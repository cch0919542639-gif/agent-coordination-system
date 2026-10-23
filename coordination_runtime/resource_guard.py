"""Finite native resource samples and an explicit project latch in ordered events."""
import ctypes as C
import json
import os
from pathlib import Path
import shutil
import uuid

from .state_controller import StateError, _integer

MIN_DISK = 512 * 1024**2
MIN_MEMORY = 256 * 1024**2
MAX_LOAD = 95
OPEN = 'resource.breaker.open'
CLOSED = 'resource.breaker.closed'


def sample(paths):
    """No process enumeration, subprocess, persistent sampler or private output."""
    if os.name != 'nt':
        raise StateError('Native resource sampling unavailable.')
    class Memory(C.Structure):
        _fields_ = [('length', C.c_uint32), ('load', C.c_uint32)] + [
            (name, C.c_uint64) for name in ('total', 'available', 'page_total',
                                          'page_available', 'virtual_total',
                                          'virtual_available', 'extended')]
    value = Memory();value.length = C.sizeof(value)
    api = C.WinDLL('kernel32', use_last_error=True).GlobalMemoryStatusEx
    api.argtypes = [C.POINTER(Memory)];api.restype = C.c_int
    if not api(C.byref(value)):
        raise StateError('Native resource sampling unavailable.')
    free = []
    for name in paths:
        path = Path(name)
        while not path.exists() and path != path.parent:
            path = path.parent
        free.append(shutil.disk_usage(path).free)
    return dict(disk_free_bytes=min(free), available_memory_bytes=value.available,
                memory_load_percent=value.load)


def measured(paths):
    try:
        result = sample(paths)
        if not isinstance(result, dict) or set(result) != {
                'disk_free_bytes', 'available_memory_bytes', 'memory_load_percent'}:
            raise ValueError
        for key, value in result.items():
            _integer(value, maximum=100 if key == 'memory_load_percent' else 2**63-1)
        reason = ('disk_pressure' if result['disk_free_bytes'] < MIN_DISK else
                  'memory_pressure' if result['available_memory_bytes'] < MIN_MEMORY
                  or result['memory_load_percent'] >= MAX_LOAD else '')
        return result, reason
    except (OSError, ValueError, TypeError, RuntimeError, StateError):
        return {}, 'sample_unknown'


def latch(db, project):
    row = db.execute('SELECT sequence,event_type,artifact_ref FROM events WHERE '
                     'project_id=? AND event_type IN (?,?) ORDER BY sequence DESC LIMIT 1',
                     (project, OPEN, CLOSED)).fetchone()
    return dict(sequence=row['sequence'], state='open' if row['event_type'] == OPEN else 'closed') if row else dict(sequence=0, state='closed')


def admission_gate(db, project):
    if latch(db, project)['state'] == 'open':
        raise StateError('Resource breaker is open; explicit healthy reset required.')


def require_resources(p, db, extra=()):
    admission_gate(db, p.project_id)
    _, reason = measured((p.root, p.controller.path.parent, p.workspace.root, *extra))
    if reason:
        raise StateError('Resource sample refuses new work.')


class ResourceController:
    def __init__(self, parallel, extra=()):
        self.p = parallel
        self.paths = (parallel.root, parallel.controller.path.parent, parallel.workspace.root, *extra)

    def _binding(self, db):
        settings = self.p._settings(db)
        if not settings:
            raise StateError('Resource project binding is missing.')
        if settings['mode'] == 'parallel':
            self.p._active(db)
        elif settings['mode'] != 'disabled' or self.p.marker.exists() or self.p.marker.is_symlink():
            raise StateError('Resource mode marker conflicts.')

    def _append(self, db, opened, metrics, reason):
        now = self.p._now(db)
        row = db.execute('INSERT INTO events(schema_version,event_id,project_id,task_id,run_id,agent_id,event_type,timestamp_ms,causation_id,artifact_ref) '
                         'VALUES(?,?,?,?,?,?,?,?,?,?)',
                         (1, uuid.uuid4().hex, self.p.project_id, 'controller', 'controller',
                          'resource-controller', OPEN if opened else CLOSED, now, 'resources',
                          json.dumps(dict(sample=metrics, reason=reason), sort_keys=True)))
        db.execute('UPDATE metadata SET last_clock_ms=? WHERE id=1', (now,))
        return dict(sequence=row.lastrowid, state='open' if opened else 'closed')

    def probe(self, *, execute=False):
        with self.p.controller._db(write=execute) as db:
            self._binding(db);current = latch(db, self.p.project_id)
            metrics, reason = measured(self.paths)
            if execute and reason and current['state'] != 'open':
                current = self._append(db, True, metrics, reason)
            return dict(current, sample=metrics, healthy=not reason, reason=reason,
                        dry_run=not execute)

    def reset(self, expected_sequence, *, execute=False):
        _integer(expected_sequence)
        with self.p.controller._db(write=execute) as db:
            self._binding(db);current = latch(db, self.p.project_id)
            if current['sequence'] != expected_sequence:
                raise StateError('Resource latch sequence changed.')
            self.p._quiescent(db)
            for row in db.execute('SELECT status,process_json FROM evidence_candidates WHERE project_id=?', (self.p.project_id,)):
                proof = json.loads(row['process_json'])
                if not isinstance(proof, dict):
                    raise StateError('Unknown checker receipt prevents resource reset.')
                if row['status'] == 'checking' or (row['status'] == 'recovery_required' and proof.get('tree_stopped') is not True):
                    raise StateError('Unknown checker tree prevents resource reset.')
            metrics, reason = measured(self.paths)
            if reason:
                raise StateError('Healthy resource sample required for reset.')
            if not execute:
                return dict(current, dry_run=True, would_reset=current['state'] == 'open')
            if current['state'] == 'closed':
                return dict(current, historical=True)
            return self._append(db, False, metrics, '')


def preflight(p, *, execute=False, extra=()):
    result = ResourceController(p, extra).probe(execute=execute)
    if not result['healthy'] or result['state'] == 'open':
        raise StateError('Resource breaker refuses new work; inspect resources.')
