"""Bounded, private projections; never create or write the runtime database."""
from collections import Counter
import hashlib
import json
import os
import re
import time

from coordination_runtime.board_projection import STATES
from coordination_runtime.resource_guard import latch, MIN_DISK, MIN_MEMORY, MAX_LOAD
from coordination_runtime.state_controller import StateError, _id


def text(value):
    if not isinstance(value, str) or len(value) > 256:
        raise StateError('Metadata field exceeds bound.')
    return value


class ReadModel:
    def __init__(self, parallel):
        self.p = parallel
        self.cached_at = 0
        self.cached = None

    def board(self):
        if self.cached is not None and time.monotonic() - self.cached_at < 10:
            return self.cached
        rows = []; seen = set(); size = 0; scanned = 0
        for state in STATES:
            directory = self.p.board._path('coordination/task-board/' + state)
            with os.scandir(directory) as entries:
                for entry in entries:
                    scanned += 1
                    if scanned > 4096:
                        raise StateError('Board directory enumeration exceeds bound.')
                    if not entry.name.lower().endswith('.md') or entry.name == 'README.md':
                        continue
                    if len(rows) >= 2048:
                        raise StateError('Board scan exceeds bound.')
                    rows.append(self._card(directory / entry.name, state, seen))
                    size += rows[-1].pop('_bytes')
                    if size > 8 * 1024**2:
                        raise StateError('Board bytes exceed bound.')
        rows.sort(key=lambda row: (row['status'], row['task_id']))
        self.cached, self.cached_at = rows, time.monotonic()
        return rows

    def _card(self, path, state, seen):
        data = self.p.board._read(path)
        if data is None:
            raise StateError('Board changed during read.')
        fields = self.p.board._header(data)
        task = fields.get('task_id'); _id(task)
        if task in seen or fields.get('status') != state.upper():
            raise StateError('Board identity or status conflicts.')
        seen.add(task)
        deps = fields.get('dependencies', [])
        if not isinstance(deps, list) or len(deps) > 32:
            raise StateError('Dependency metadata exceeds bound.')
        for dep in deps:
            _id(dep)
        return dict(task_id=task, status=state.upper(), owner=text(fields.get('owner', '')),
                    phase=text(fields.get('phase', '')), priority=text(fields.get('priority', '')),
                    dependencies=deps, _bytes=len(data))

    def binding(self, db):
        row = db.execute('SELECT root_digest FROM project_bindings WHERE project_id=?',
                         (self.p.project_id,)).fetchone()
        if not row or row[0] != self.p.board.root_digest:
            raise StateError('Console project binding refused.')
        settings = self.p._settings(db)
        if not settings:
            raise StateError('Console configuration missing.')
        if settings['mode'] == 'parallel':
            self.p._active(db)
        elif settings['mode'] != 'disabled' or self.p.marker.exists() or self.p.marker.is_symlink():
            raise StateError('Console mode binding refused.')
        return dict(settings)

    def _rows(self, db, table, fields, offset):
        # Table/column names are exclusively internal constants.
        project = self.p.project_id
        total = db.execute('SELECT count(*) FROM ' + table + ' WHERE project_id=?', (project,)).fetchone()[0]
        rows = [dict(r) for r in db.execute('SELECT ' + fields + ' FROM ' + table +
                ' WHERE project_id=? ORDER BY 1 LIMIT 100 OFFSET ?', (project, offset))]
        for row in rows:
            for value in row.values():
                if isinstance(value, str):
                    text(value)
        return dict(rows=rows, total=total, more=offset + len(rows) < total, offset=offset)

    def view(self, name, offset=0, after=0, limit=50):
        result = dict(view=name, project_id=self.p.project_id,
                      sampled_ms=time.time_ns() // 1_000_000,
                      runtime_available=self.p.controller.path.is_file())
        if name in {'overview', 'board', 'reviews'}:
            cards = self.board()
            if name == 'overview':
                result['board_counts'] = dict(Counter(r['status'] for r in cards))
                result['board_total'] = len(cards)
            elif name == 'board':
                result.update(rows=cards[offset:offset + 100], total=len(cards),
                              offset=offset, more=offset + 100 < len(cards))
            else:
                reviews = []
                for card in cards[offset:offset + 100]:
                    path = self.p.board._path('coordination/reviews/review-' + card['task_id'] + '.md')
                    data = self.p.board._read(path)
                    if data is None:
                        continue
                    prefix = data.decode('utf-8').replace('\r\n', '\n').partition('\n## ')[0]
                    tasks = re.findall(r'^- Task ID: (.+)$', prefix, re.M)
                    decisions = re.findall(r'^- Decision: (.+)$', prefix, re.M)
                    if tasks != [card['task_id']] or len(decisions) != 1:
                        raise StateError('Canonical review header conflicts.')
                    reviews.append(dict(task_id=card['task_id'], decision=text(decisions[0]),
                                        sha256=hashlib.sha256(data).hexdigest()))
                result.update(reviews=reviews, offset=offset, total=len(cards),
                              more=offset + 100 < len(cards))
        if not result['runtime_available']:
            result['notice'] = 'Runtime database unavailable; repository metadata only.'
            return result
        with self.p.controller._db() as db:
            settings = self.binding(db)
            if name == 'overview':
                result['active_runs'] = db.execute('SELECT count(*) FROM runtime_tasks WHERE project_id=? '
                        'AND active_run_id IS NOT NULL', (self.p.project_id,)).fetchone()[0]
                result['breaker'] = latch(db, self.p.project_id)
                result['mode'] = settings['mode']
            elif name == 'monitor':
                result.update(self._rows(db, 'runs', 'run_id,task_id,owner,fence,phase,lease_until_ms,heartbeat_ms', offset))
                for row in result['rows']:
                    proof = db.execute('SELECT process_json,status FROM parallel_runs WHERE project_id=? AND run_id=?',
                                       (self.p.project_id, row['run_id'])).fetchone()
                    row['receipt'] = None
                    if proof:
                        if len(proof[0]) > 65536:
                            raise StateError('Process receipt exceeds bound.')
                        parsed = json.loads(proof[0])
                        if not isinstance(parsed, dict):
                            raise StateError('Process receipt invalid.')
                        row['receipt'] = {key: parsed.get(key) for key in ('pid', 'creation_time', 'exit_code', 'tree_stopped')}
                        for key, value in row['receipt'].items():
                            if value is not None and (type(value) is not (bool if key == 'tree_stopped' else int)):
                                raise StateError('Process receipt invalid.')
            elif name == 'workspaces':
                result.update(self._rows(db, 'parallel_runs', 'run_id,task_id,owner,base_sha,path_digest,status', offset))
            elif name == 'reviews':
                result['evidence'] = self._rows(db, 'evidence_candidates',
                        'evidence_id,run_id,status,candidate_sha,tested_sha,reviewed_sha', offset)
                result['publications'] = self._rows(db, 'publication_queue',
                        'sequence,evidence_id,status,candidate_sha,integrated_sha', offset)
            elif name == 'events':
                rows = [dict(r) for r in db.execute('SELECT sequence,event_type,task_id,run_id,agent_id,timestamp_ms '
                        'FROM events WHERE project_id=? AND sequence>? ORDER BY sequence LIMIT ?',
                        (self.p.project_id, after, limit + 1))]
                result.update(rows=rows[:limit], more=len(rows) > limit,
                              cursor=rows[min(len(rows), limit) - 1]['sequence'] if rows else after)
                for row in result['rows']:
                    for value in row.values():
                        if isinstance(value, str):
                            text(value)
            elif name == 'settings':
                result.update(mode=settings['mode'], capacity=settings['capacity'], schema_version=4,
                              breaker=latch(db, self.p.project_id),
                              minimum_disk_bytes=MIN_DISK, minimum_memory_bytes=MIN_MEMORY,
                              maximum_memory_load=MAX_LOAD, visible_poll_seconds=5, hidden_poll_seconds=60)
        return result
