"""Finite cooperative Git handoff; local state, immutable claims, no formal acceptance."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time
from urllib.parse import urlsplit
import uuid
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from coordination_common import parse_front_matter
from worker_process_guard import JobProcess
from .parallel_policy import path_key
from .state_controller import StateError

ZERO = '0' * 40
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}')
SHA = re.compile(r'[a-f0-9]{40}')
HASH = re.compile(r'[a-f0-9]{64}')
STATES = {'RECEIVED': 0, 'RUNNING': 1, 'FINISHED': 2, 'FAILED': 2, 'UNKNOWN': 2}
CONFIG = {'schema_version', 'mode', 'project_id', 'repository', 'state_dir', 'remote_url',
          'code_ref', 'queue_ref', 'machine_id', 'owner', 'peers', 'evidence_ref_prefix',
          'evidence_revision', 'min_tests', 'runner', 'execution_enabled'}


class HandoffError(ValueError):
    """Fixed categories only; never include subprocess output or private configuration."""


def fail(category):
    raise HandoffError(category)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result: fail('INVALID_JSON')
        result[key] = value
    return result


def decoded(raw):
    try:
        return json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError, RecursionError):
        fail('INVALID_JSON')


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value): fail('INVALID_ID')


def canonical(value):
    if not isinstance(value, str): fail('INVALID_PATH')
    path = Path(value)
    if not path.is_absolute() or path != path.resolve(): fail('INVALID_PATH')
    return path


def bounded(path, limit=65536):
    if path != path.resolve() or not path.is_file(): fail('INVALID_PATH')
    with path.open('rb') as stream: raw = stream.read(limit + 1)
    if len(raw) > limit: fail('SIZE_LIMIT')
    return raw


def reference(value):
    if (not isinstance(value, str) or not re.fullmatch(r'refs/heads/[A-Za-z0-9._/-]+', value)
            or '..' in value or '//' in value or '@{' in value or value.endswith(('/', '.', '.lock'))):
        fail('INVALID_REF')


class HandoffService:
    def __init__(self, config_path, repository, project_id):
        self.config_path = canonical(str(config_path))
        raw = bounded(self.config_path)
        c = decoded(raw)
        if not isinstance(c, dict) or set(c) != CONFIG or type(c['schema_version']) is not int or c['schema_version'] != 1:
            fail('INVALID_CONFIG')
        self.root = canonical(c['repository']); self.state = canonical(c['state_dir'])
        if canonical(str(repository)) != self.root or project_id != c['project_id']: fail('BINDING_MISMATCH')
        for key in ('project_id', 'machine_id', 'owner'): identifier(c[key])
        if (self.state.is_relative_to(self.root) or self.root.is_relative_to(self.state)
                or self.config_path.is_relative_to(self.root) or not isinstance(c['mode'], str) or c['mode'] not in {'coordinator', 'worker'}
                or type(c['execution_enabled']) is not bool or type(c['min_tests']) is not int or not 1 <= c['min_tests'] <= 100000):
            fail('INVALID_CONFIG')
        reference(c['code_ref']); reference(c['queue_ref'])
        if not c['queue_ref'].startswith('refs/heads/codex/handoff-') or c['queue_ref'] == c['code_ref']: fail('INVALID_REF')
        prefix = c['evidence_ref_prefix']
        if prefix is not None:
            reference(prefix)
            if not prefix.startswith('refs/heads/docs/console-'): fail('INVALID_REF')
        if c['evidence_revision'] is not None and (not isinstance(c['evidence_revision'], str) or not SHA.fullmatch(c['evidence_revision'])): fail('INVALID_CONFIG')
        if not isinstance(c['peers'], list) or not 1 <= len(c['peers']) <= 32: fail('INVALID_PEERS')
        machines = set()
        for peer in c['peers']:
            if not isinstance(peer, dict) or set(peer) != {'machine_id', 'owner'}: fail('INVALID_PEERS')
            for value in peer.values(): identifier(value)
            if peer['machine_id'] in machines: fail('INVALID_PEERS')
            machines.add(peer['machine_id'])
        runner = c['runner']
        if runner is not None:
            if not isinstance(runner, dict) or set(runner) != {'argv', 'script', 'sha256', 'timeout_seconds'}: fail('INVALID_RUNNER')
            script = canonical(runner['script'])
            if script.is_relative_to(self.state / 'workspaces') or not isinstance(runner['argv'], list) or not 2 <= len(runner['argv']) <= 32:
                fail('INVALID_RUNNER')
            if (any(not isinstance(a, str) or not a or len(a) > 4096 or '\0' in a for a in runner['argv'])
                    or runner['script'] not in runner['argv'] or not isinstance(runner['sha256'], str) or not HASH.fullmatch(runner['sha256'])
                    or type(runner['timeout_seconds']) is not int or not 1 <= runner['timeout_seconds'] <= 900): fail('INVALID_RUNNER')
        remote = c['remote_url']
        if not isinstance(remote, str): fail('INVALID_REMOTE')
        if remote.startswith('https://'):
            url = urlsplit(remote)
            if url.netloc != 'github.com' or url.query or url.fragment or not re.fullmatch(r'/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', url.path): fail('INVALID_REMOTE')
        elif not canonical(remote).is_dir(): fail('INVALID_REMOTE')
        self.c = c; self.binding = digest(encoded(c)); self.config_hash = digest(raw)
        self.cache = self.state / 'cache.git'; self.database = self.state / 'handoff.db'
        self.deadline = None
        if self._git(['config', '--get', 'remote.origin.url'], cwd=self.root).decode().strip() != remote: fail('REMOTE_MISMATCH')

    def _git(self, args, *, cwd=None, data=None):
        timeout = 20
        if self.deadline is not None:
            timeout = min(timeout, self.deadline - time.monotonic())
            if timeout <= 0: fail('DEADLINE')
        command = ['git', '--no-optional-locks', '-c', 'core.hooksPath=' + str(self.state / 'no-hooks')]
        if cwd is None: command += ['--git-dir', str(self.cache)]
        env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='never', GIT_OPTIONAL_LOCKS='0',
            GIT_AUTHOR_NAME='Local handoff', GIT_AUTHOR_EMAIL='handoff@example.invalid',
            GIT_COMMITTER_NAME='Local handoff', GIT_COMMITTER_EMAIL='handoff@example.invalid')
        try:
            result = subprocess.run(command + args, cwd=cwd, input=data, capture_output=True, timeout=timeout, env=env)
        except (OSError, subprocess.SubprocessError): fail('TRANSPORT_FAILED')
        if result.returncode or len(result.stdout) > 2 * 1024**2: fail('TRANSPORT_FAILED')
        return result.stdout

    def _check(self):
        if digest(bounded(self.config_path)) != self.config_hash: fail('CONFIG_CHANGED')
        if self.state != self.state.resolve() or self.database != self.database.resolve() or self.cache != self.cache.resolve(): fail('INVALID_PATH')

    @contextmanager
    def _db(self, write=False):
        self._check()
        db = None
        try:
            db = sqlite3.connect(self.database.as_uri() + ('?mode=rw' if write else '?mode=ro'), uri=True, timeout=5)
            db.row_factory = sqlite3.Row
            db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if tables != {'metadata', 'snapshot', 'inbox'}: fail('BINDING_MISMATCH')
            rows = db.execute('SELECT binding FROM metadata').fetchall()
            if len(rows) != 1 or rows[0][0] != self.binding: fail('BINDING_MISMATCH')
            yield db
            if write: db.commit()
        except sqlite3.Error: fail('STATE_UNAVAILABLE')
        finally:
            if db is not None: db.close()

    def initialize(self):
        self._check()
        if self.state.exists():
            with self._db(): pass
            if self._git(['config', '--get', 'remote.origin.url']).decode().strip() != self.c['remote_url']: fail('REMOTE_MISMATCH')
            return self.summary()
        if not self.state.parent.is_dir(): fail('INVALID_PATH')
        self.state.mkdir()
        self._git(['init', '--bare', str(self.cache)], cwd=self.state)
        self._git(['remote', 'add', 'origin', self.c['remote_url']])
        with sqlite3.connect(self.database) as db:
            db.executescript('CREATE TABLE metadata(binding TEXT NOT NULL); CREATE TABLE snapshot(data TEXT NOT NULL);'
                'CREATE TABLE inbox(dispatch_id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,assignment TEXT NOT NULL,'
                'run_id TEXT NOT NULL,status TEXT NOT NULL,exit_code INTEGER,tree_stopped INTEGER NOT NULL,outbox TEXT);')
            db.execute('INSERT INTO metadata VALUES(?)', (self.binding,))
            db.execute('INSERT INTO snapshot VALUES(?)', (encoded(dict(last_sync_ms=None, last_error=None,
                code_revision=None, queue_head=ZERO, acceptance=[], dispatches=[], ready_tasks=[])).decode(),))
        return self.summary()

    def _snapshot(self, **changes):
        with self._db(write=True) as db:
            value = decoded(db.execute('SELECT data FROM snapshot').fetchone()[0]); value.update(changes)
            db.execute('UPDATE snapshot SET data=?', (encoded(value).decode(),))

    def summary(self):
        empty = dict(configured=True, initialized=False, last_sync_ms=None, last_error='STATE_UNAVAILABLE',
                     code_revision=None, queue_head=ZERO, ready_tasks=[], peers=self.c['peers'], dispatches=[], acceptance=[])
        try:
            with self._db() as db:
                value = decoded(db.execute('SELECT data FROM snapshot').fetchone()[0])
                local = {r['dispatch_id']: r for r in db.execute('SELECT dispatch_id,status,exit_code,outbox FROM inbox LIMIT 128')}
            empty.update(value, initialized=True, peers=self.c['peers'])
            for row in empty['dispatches']:
                if row['dispatch_id'] in local:
                    saved = local[row['dispatch_id']]; row.update(status=saved['status'], exit_code=saved['exit_code'])
            if any(row['outbox'] is not None for row in local.values()): empty['last_error'] = 'OUTBOX_PENDING'
            return empty
        except (HandoffError, IndexError, TypeError): return empty

    def _card(self, raw, task_id=None, owner=None):
        if len(raw) > 65536: fail('INVALID_CARD')
        try:
            header, _ = parse_front_matter(raw.decode('utf-8').replace('\r\n', '\n'))
            if not header or header.get('status') != 'READY': fail('INVALID_CARD')
            identifier(header['task_id']); identifier(header['owner'])
            if task_id is not None and header['task_id'] != task_id: fail('INVALID_CARD')
            if owner is not None and header['owner'] != owner: fail('INVALID_CARD')
            for key, minimum in [('allowed_scope', 1), ('forbidden_scope', 0)]:
                values = header[key]
                if not isinstance(values, list) or not minimum <= len(values) <= 64: fail('INVALID_CARD')
                for name in values:
                    base = name.removesuffix('/**')
                    if any(c in base for c in '*?[]{}'): fail('INVALID_CARD')
                    path_key(base)
            deps = header.get('dependencies', [])
            if not isinstance(deps, list) or len(deps) > 32: fail('INVALID_CARD')
            for item in deps: identifier(item)
            return header
        except (KeyError, TypeError, AttributeError, UnicodeError, ValueError, StateError): fail('INVALID_CARD')

    def _ready(self):
        result = []
        folder = self.root / 'coordination/task-board/ready'
        if folder != folder.resolve(): fail('INVALID_CARD')
        for count, path in enumerate(folder.glob('*.md')):
            if count >= 2048: fail('SIZE_LIMIT')
            if path.name == 'README.md': continue
            raw = bounded(path)
            try: metadata, _ = parse_front_matter(raw.decode('utf-8').replace('\r\n','\n'))
            except UnicodeError: continue
            owners = {p['owner'] for p in self.c['peers']}
            if not metadata or metadata.get('status') != 'READY' or metadata.get('owner') not in owners: continue
            header = self._card(raw)
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,149}\.md', path.name): fail('INVALID_CARD')
            if any(row['task_id'] == header['task_id'] for row in result): fail('DUPLICATE_TASK')
            result.append(dict(task_id=header['task_id'], owner=header['owner'], card_sha256=digest(raw), filename=path.name))
        return result

    def _head(self, ref):
        lines = self._git(['ls-remote', '--refs', 'origin', ref]).decode('ascii').splitlines()
        if not lines: return ZERO
        if len(lines) != 1: fail('INVALID_REMOTE')
        sha, name = lines[0].split('\t')
        if not SHA.fullmatch(sha) or name != ref: fail('INVALID_REMOTE')
        return sha

    def _fetch_queue(self):
        head = self._head(self.c['queue_ref'])
        if head != ZERO: self._git(['fetch', '--no-tags', 'origin', self.c['queue_ref']])
        return head

    def _files(self, head):
        if head == ZERO: return []
        names = self._git(['ls-tree', '-r', '--name-only', head]).decode('utf-8').splitlines()
        if len(names) > 4096: fail('SIZE_LIMIT')
        return names

    def _blob(self, head, path, limit=2 * 1024**2):
        try: path_key(path)
        except (ValueError, StateError): fail('INVALID_EVIDENCE')
        if int(self._git(['cat-file', '-s', head + ':' + path]).strip()) > limit: fail('SIZE_LIMIT')
        return self._git(['show', head + ':' + path])

    def _assignments(self, head):
        files = self._files(head); result = []
        for path in files:
            if re.fullmatch(r'dispatch/[a-f0-9]{64}/assignment.json', path):
                assignment = decoded(self._blob(head, path, 8192))
                expected = {'schema_version', 'dispatch_id', 'project_id', 'task_id', 'owner', 'machine_id', 'base_revision', 'card_sha256', 'card_filename'}
                if not isinstance(assignment, dict) or set(assignment) != expected or type(assignment['schema_version']) is not int or assignment['schema_version'] != 1: fail('INVALID_ASSIGNMENT')
                for key in ('project_id', 'task_id', 'owner', 'machine_id'): identifier(assignment[key])
                if assignment['project_id'] != self.c['project_id'] or not isinstance(assignment['base_revision'], str) or not SHA.fullmatch(assignment['base_revision']) or not isinstance(assignment['card_sha256'], str) or not HASH.fullmatch(assignment['card_sha256']): fail('INVALID_ASSIGNMENT')
                if not isinstance(assignment['card_filename'], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,149}\.md', assignment['card_filename']): fail('INVALID_ASSIGNMENT')
                original = dict(assignment); dispatch_id = original.pop('dispatch_id')
                if dispatch_id != digest(encoded(original)) or path.split('/')[1] != dispatch_id: fail('INVALID_ASSIGNMENT')
                card = self._blob(head, 'dispatch/' + dispatch_id + '/task.md', 65536)
                if digest(card) != assignment['card_sha256']: fail('INVALID_ASSIGNMENT')
                self._card(card, assignment['task_id'], assignment['owner'])
                result.append(assignment)
        if len(result) > 128: fail('SIZE_LIMIT')
        return result

    def _claim(self, head, assignment):
        path = 'receipts/' + assignment['dispatch_id'] + '/claim.json'
        if path not in self._files(head): return None
        claim = decoded(self._blob(head, path, 8192))
        required = {'schema_version', 'dispatch_id', 'project_id', 'machine_id', 'owner', 'card_sha256', 'run_id'}
        if not isinstance(claim, dict) or set(claim) != required or type(claim['schema_version']) is not int or claim['schema_version'] != 1: fail('INVALID_RECEIPT')
        for key in ('dispatch_id', 'project_id', 'machine_id', 'owner', 'card_sha256'):
            if claim[key] != assignment[key]: fail('INVALID_RECEIPT')
        if not isinstance(claim['run_id'], str) or not re.fullmatch('[a-f0-9]{32}', claim['run_id']): fail('INVALID_RECEIPT')
        return claim

    def _receipt(self, head, assignment):
        claim = self._claim(head, assignment)
        path = 'receipts/' + assignment['dispatch_id'] + '/status.json'
        if path not in self._files(head): return claim, None
        status = decoded(self._blob(head, path, 8192))
        if not claim or not isinstance(status, dict) or set(status) != set(claim) | {'status', 'exit_code', 'tree_stopped'}: fail('INVALID_RECEIPT')
        if any(status[k] != v for k, v in claim.items()) or not isinstance(status['status'], str) or status['status'] not in STATES or type(status['tree_stopped']) is not bool: fail('INVALID_RECEIPT')
        if status['exit_code'] is not None and (type(status['exit_code']) is not int or not 0 <= status['exit_code'] <= 0xffffffff): fail('INVALID_RECEIPT')
        if status['status'] == 'FINISHED' and (status['exit_code'] != 0 or not status['tree_stopped']): fail('INVALID_RECEIPT')
        return claim, status

    def _publish(self, updates, expected=None):
        previous = self.deadline
        if previous is None: self.deadline = time.monotonic() + 120
        try: return self._publish_bounded(updates, expected)
        finally: self.deadline = previous

    def _publish_bounded(self, updates, expected):
        for attempt in range(2):
            head = self._fetch_queue()
            if expected is not None and head != expected: fail('STALE_QUEUE')
            assignments = {a['dispatch_id']: a for a in self._assignments(head)}
            files = self._files(head)
            changes = {}
            for path, raw in updates.items():
                if path.endswith('/status.json'):
                    key = path.split('/')[1]
                    if key not in assignments: fail('RECEIPT_CONFLICT')
                    claim = self._claim(head, assignments[key]); new = decoded(raw)
                    if not claim or any(new.get(k) != v for k, v in claim.items()): fail('RECEIPT_CONFLICT')
                if path in files:
                    before = self._blob(head, path)
                    if before == raw: continue
                    if not path.endswith('/status.json'): fail('IMMUTABLE_CONFLICT')
                    old, new = decoded(before), decoded(raw)
                    if (any(old[k] != new[k] for k in old if k not in {'status', 'exit_code', 'tree_stopped'})
                            or STATES[new['status']] < STATES[old['status']] or STATES[old['status']] == 2): fail('RECEIPT_CONFLICT')
                changes[path] = raw
            if not changes: return head
            tree_entries = {}
            for path in files:
                tree_entries[path] = self._git(['rev-parse', head + ':' + path]).decode().strip()
            for path, raw in changes.items(): tree_entries[path] = self._git(['hash-object', '-w', '--stdin'], data=raw).decode().strip()
            def tree(prefix=''):
                entries = []; directories = set()
                for path, blob in tree_entries.items():
                    if not path.startswith(prefix): continue
                    rest = path[len(prefix):]
                    if '/' in rest: directories.add(rest.split('/')[0])
                    else: entries.append('100644 blob ' + blob + '\t' + rest + '\n')
                for directory in directories:
                    entries.append('040000 tree ' + tree(prefix + directory + '/') + '\t' + directory + '\n')
                return self._git(['mktree'], data=''.join(sorted(entries)).encode()).decode().strip()
            commit = self._git(['-c', 'user.name=Local handoff', '-c', 'user.email=handoff@example.invalid',
                'commit-tree', tree(), *(['-p', head] if head != ZERO else []), '-m', 'Bounded handoff receipt']).decode().strip()
            try:
                self._git(['push', '--porcelain', 'origin', commit + ':' + self.c['queue_ref']])
            except HandoffError:
                if expected is not None or attempt: raise
                continue
            if self._head(self.c['queue_ref']) != commit:
                # Another valid fast-forward may already include our immutable write.
                latest = self._fetch_queue()
                if any(self._blob(latest, p) != raw for p, raw in updates.items()): fail('PUBLISH_UNKNOWN')
                return latest
            return commit
        fail('PUBLISH_FAILED')

    def _evidence(self):
        prefix = self.c['evidence_ref_prefix']
        if prefix is None: return []
        lines = self._git(['ls-remote', '--refs', 'origin', prefix + '*']).decode('ascii').splitlines()
        if len(lines) > 32: fail('SIZE_LIMIT')
        reports = []
        for line in lines:
            commit, ref = line.split('\t'); reference(ref)
            if not ref.startswith(prefix) or not SHA.fullmatch(commit): fail('INVALID_EVIDENCE')
            self._git(['fetch', '--no-tags', 'origin', ref])
            manifests = [p for p in self._files(commit) if p.startswith('coordination/evidence/') and p.endswith('/publication-manifest.json')]
            if len(manifests) > 8: fail('SIZE_LIMIT')
            for path in manifests:
                row = dict(ref=ref, evidence_commit=commit, tested_commit=None, status='INVALID', test_count=0, verified_ms=int(time.time()*1000))
                try:
                    manifest = decoded(self._blob(commit, path, 65536)); tested = manifest['tested_commit']
                    row['tested_commit'] = tested if isinstance(tested, str) and SHA.fullmatch(tested) else None
                    members = manifest['files']
                    if not isinstance(members, dict) or not 2 <= len(members) <= 64: fail('INVALID_EVIDENCE')
                    contents = {}; size = 0
                    for name, pin in members.items():
                        path_key(name)
                        if not isinstance(pin, str) or not HASH.fullmatch(pin): fail('INVALID_EVIDENCE')
                        raw = self._blob(commit, str(Path(path).parent.as_posix()) + '/' + name)
                        size += len(raw)
                        if size > 16 * 1024**2 or digest(raw) != pin: fail('INVALID_EVIDENCE')
                        contents[name] = raw
                    result = decoded(contents['results.json'])
                    if result['commit'] != tested: fail('INVALID_EVIDENCE')
                    if result['status'] != 'PASS': row['status'] = 'FAIL'; reports.append(row); continue
                    if tested != self.c['evidence_revision']: row['status'] = 'STALE'; reports.append(row); continue
                    environment = result['environment']
                    if (type(environment['utf8_mode']) is not int or environment['utf8_mode'] != 0
                            or not isinstance(environment.get('preferred_encoding'), str) or not environment['preferred_encoding']
                            or environment.get('PYTHONUTF8') not in {None, '', '0'}
                            or environment.get('PYTHONIOENCODING') not in {None, ''}): fail('INVALID_EVIDENCE')
                    checks = result['checks']
                    native = {'head': 0, 'init': 0, 'init-replay': 0, 'init-conflict': 2, 'focused-tests': 0, 'git-status': 0,
                              'serve-0': 0, 'serve-1': 0}
                    for name, expected in native.items():
                        check = checks[name]
                        if type(check['exit_code']) is not int or check['exit_code'] != expected or check.get('expected', expected) != expected:
                            fail('INVALID_EVIDENCE')
                    if checks['replay-and-conflict-preserve-bytes'] is not True or checks['schema4-disabled-no-runs-unchanged-private-files'] is not True: fail('INVALID_EVIDENCE')
                    if type(checks['manifest']['passed']) is not int or checks['manifest']['passed'] < 1: fail('INVALID_EVIDENCE')
                    for name in ('serve-0', 'serve-1'):
                        check = checks[name]
                        if check['finite_exit'] is not True or check['viewer_writes'] != 403: fail('INVALID_EVIDENCE')
                        for view in ('overview','board','monitor','workspaces','reviews','events','settings'):
                            item = check['views'][view]
                            if type(item['status']) is not int or item['status'] != 200 or item['runtime_available'] is not True: fail('INVALID_EVIDENCE')
                    raw = contents['junit.xml']
                    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper(): fail('INVALID_EVIDENCE')
                    xml = ET.fromstring(raw); cases = list(xml.iter('testcase'))
                    if len(cases) < self.c['min_tests'] or any(list(t) for t in cases if any(child.tag in {'failure','error','skipped'} for child in t)): fail('INVALID_EVIDENCE')
                    suites = list(xml.iter('testsuite'))
                    if not suites: fail('INVALID_EVIDENCE')
                    for suite in suites:
                        if any(int(suite.get(k, '-1')) != 0 for k in ('failures', 'errors', 'skipped')) or int(suite.get('tests', '-1')) != len(list(suite.iter('testcase'))): fail('INVALID_EVIDENCE')
                    row.update(status='VERIFIED_PASS', test_count=len(cases))
                except (HandoffError, ValueError, KeyError, TypeError, RecursionError, ET.ParseError, StateError): pass
                reports.append(row)
        return reports

    def sync_once(self):
        with self._db(): pass
        old_deadline = self.deadline
        if old_deadline is None: self.deadline = time.monotonic() + 120
        try:
            self._git(['fetch', '--no-tags', 'origin', self.c['code_ref']])
            code = self._head(self.c['code_ref'])
            if code == ZERO: fail('CODE_UNAVAILABLE')
            queue = self._fetch_queue(); assignments = self._assignments(queue)
            dispatches = []
            for assignment in assignments:
                claim, receipt = self._receipt(queue, assignment)
                dispatches.append({k: assignment[k] for k in ('dispatch_id', 'task_id', 'machine_id', 'owner')} |
                    dict(status=receipt['status'] if receipt else 'RECEIVED' if claim else 'DISPATCHED', exit_code=receipt['exit_code'] if receipt else None))
            evidence = self._evidence(); previous = self.summary()['acceptance']
            keys = {(r['ref'], r['evidence_commit'], r['tested_commit']) for r in evidence}
            evidence += [r for r in previous if (r['ref'],r['evidence_commit'],r['tested_commit']) not in keys]
            self._snapshot(last_sync_ms=int(time.time()*1000), last_error=None, code_revision=code,
                queue_head=queue, dispatches=dispatches, acceptance=evidence[:64], ready_tasks=[{k:v for k,v in row.items() if k != 'filename'} for row in self._ready()])
        except HandoffError as error:
            self._snapshot(last_error=str(error)); raise
        finally: self.deadline = old_deadline
        return self.summary()

    def dispatch(self, task_id, machine_id, expected_card_sha256, expected_revision, expected_queue_head, execute=False):
        if self.c['mode'] != 'coordinator': fail('ROLE_REFUSED')
        identifier(task_id); identifier(machine_id)
        if not isinstance(expected_card_sha256, str) or not HASH.fullmatch(expected_card_sha256) or not isinstance(expected_revision, str) or not SHA.fullmatch(expected_revision) or not isinstance(expected_queue_head, str) or not SHA.fullmatch(expected_queue_head): fail('INVALID_EXPECTATION')
        snapshot = self.summary()
        if not snapshot['initialized'] or snapshot['last_error'] or snapshot['code_revision'] != expected_revision or snapshot['queue_head'] != expected_queue_head: fail('STALE_PREVIEW')
        tasks = [r for r in self._ready() if r['task_id'] == task_id]
        peers = [p for p in self.c['peers'] if p['machine_id'] == machine_id]
        if len(tasks) != 1 or len(peers) != 1 or tasks[0]['owner'] != peers[0]['owner'] or tasks[0]['card_sha256'] != expected_card_sha256: fail('ASSIGNMENT_REFUSED')
        row = tasks[0]
        raw = bounded(self.root / 'coordination/task-board/ready' / row['filename'])
        if digest(raw) != expected_card_sha256: fail('STALE_CARD')
        card = self._card(raw, task_id, row['owner'])
        assignment = dict(schema_version=1, project_id=self.c['project_id'], task_id=task_id, owner=row['owner'], machine_id=machine_id,
                          base_revision=expected_revision, card_sha256=expected_card_sha256, card_filename=row['filename'])
        dispatch_id = digest(encoded(assignment)); assignment['dispatch_id'] = dispatch_id
        preview = dict(task_id=task_id, machine_id=machine_id, expected_card_sha256=expected_card_sha256,
            expected_revision=expected_revision, expected_queue_head=expected_queue_head, dispatch_id=dispatch_id, owner=row['owner'], status='PREVIEW',
            allowed_scope=list(card['allowed_scope']), forbidden_scope=list(card['forbidden_scope']))
        if execute:
            if self._head(self.c['code_ref']) != expected_revision: fail('STALE_REVISION')
            raw = bounded(self.root / 'coordination/task-board/ready' / row['filename'])
            if digest(raw) != expected_card_sha256: fail('STALE_CARD')
            head = self._publish({'dispatch/' + dispatch_id + '/assignment.json': encoded(assignment), 'dispatch/' + dispatch_id + '/task.md': raw}, expected_queue_head)
            self._snapshot(queue_head=head)
            self.sync_once(); preview['status'] = 'DISPATCHED'
        return preview

    @contextmanager
    def _lock(self):
        path = self.state / 'worker.lock'
        if path != path.resolve(): fail('INVALID_PATH')
        stream = path.open('a+b')
        if not stream.tell(): stream.write(b'0'); stream.flush()
        stream.seek(0)
        try:
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError: fail('WORKER_BUSY')
            yield
        finally: stream.close()

    def _immutable(self, path, raw):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path != path.resolve(): fail('INVALID_PATH')
        try:
            with path.open('xb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        except FileExistsError:
            if bounded(path) != raw: fail('INBOX_CONFLICT')

    def _outbox(self):
        with self._db() as db: rows = [dict(r) for r in db.execute('SELECT dispatch_id,outbox FROM inbox WHERE outbox IS NOT NULL LIMIT 128')]
        for row in rows:
            try:
                self._publish({'receipts/' + row['dispatch_id'] + '/status.json': row['outbox'].encode()})
            except HandoffError:
                self._snapshot(last_error='OUTBOX_PENDING'); return
            with self._db(write=True) as db: db.execute('UPDATE inbox SET outbox=NULL WHERE dispatch_id=? AND outbox=?', (row['dispatch_id'], row['outbox']))

    def _record(self, assignment, run_id, status, exit_code=None, stopped=False):
        claim = {k: assignment[k] for k in ('schema_version','dispatch_id','project_id','machine_id','owner','card_sha256')} | dict(run_id=run_id)
        receipt = claim | dict(status=status, exit_code=exit_code, tree_stopped=stopped)
        with self._db(write=True) as db:
            db.execute('UPDATE inbox SET status=?,exit_code=?,tree_stopped=?,outbox=? WHERE dispatch_id=?',
                       (status, exit_code, int(stopped), encoded(receipt).decode(), assignment['dispatch_id']))

    def _workspace(self, assignment):
        workspace = self.state / 'workspaces' / assignment['dispatch_id']
        if workspace != workspace.resolve(): fail('INVALID_PATH')
        if not workspace.exists():
            workspace.parent.mkdir(exist_ok=True)
            self._git(['clone', '--no-checkout', str(self.cache), str(workspace)], cwd=self.state)
            self._git(['checkout', '--detach', assignment['base_revision']], cwd=workspace)
        if self._git(['rev-parse', 'HEAD'], cwd=workspace).decode().strip() != assignment['base_revision']: fail('WORKSPACE_CONFLICT')
        target = workspace / 'coordination/task-board/ready' / assignment['card_filename']
        changes = self._git(['status', '--porcelain', '--untracked-files=all'], cwd=workspace).decode().splitlines()
        relative = target.relative_to(workspace).as_posix()
        if any(line[3:] != relative for line in changes): fail('DIRTY_WORKSPACE')
        raw = bounded(self.state / 'inbox' / assignment['dispatch_id'] / 'task.md')
        if changes and (not target.exists() or bounded(target) != raw): fail('DIRTY_WORKSPACE')
        target.parent.mkdir(parents=True, exist_ok=True)
        if target != target.resolve(): fail('INVALID_PATH')
        target.write_bytes(raw)
        return workspace

    def _run(self, assignment, run_id):
        runner = self.c['runner']
        if runner is None or not self.c['execution_enabled']: fail('EXECUTION_DISABLED')
        if digest(bounded(canonical(runner['script']), 1024**2)) != runner['sha256']: fail('RUNNER_CHANGED')
        workspace = self._workspace(assignment)
        payload = self.state / 'inbox' / assignment['dispatch_id'] / 'payload.json'
        self._immutable(payload, encoded(dict(schema_version=1, assignment=assignment, run_id=run_id,
            task_file=str(payload.parent / 'task.md'), workspace=str(workspace))))
        def remaining_budget():
            timeout = runner['timeout_seconds']
            if self.deadline is not None:
                timeout = min(timeout, self.deadline - time.monotonic() - 5)
                if timeout <= 0: fail('DEADLINE')
            return timeout
        remaining_budget()
        self._record(assignment, run_id, 'RUNNING')
        self._outbox()
        process = None; code = None; stopped = False; status = 'UNKNOWN'
        try:
            if digest(bounded(canonical(runner['script']), 1024**2)) != runner['sha256']: fail('RUNNER_CHANGED')
            remaining_budget()  # RUNNING/outbox work cannot authorize a later launch.
            process = JobProcess([*runner['argv'], str(payload)], cwd=workspace, capture_output=False)
            remaining_budget()  # Constructor returned an owned suspended process.
            process.resume()
            try:
                code = process.wait(remaining_budget())
                stopped = process.wait_empty(2)
                status = 'FINISHED' if code == 0 and stopped else 'FAILED' if stopped else 'UNKNOWN'
                if not stopped:
                    process.stop(); stopped = process.wait_empty(2); status = 'FAILED' if stopped else 'UNKNOWN'
            except subprocess.TimeoutExpired:
                process.stop(); code = process.wait(0); stopped = process.wait_empty(2)
                status = 'FAILED' if stopped else 'UNKNOWN'
        except (OSError, RuntimeError, ValueError):
            if process is not None:
                try: process.stop(); code = process.wait(0); stopped = process.wait_empty(2)
                except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired): pass
        finally:
            if process is not None: process.close()
            self._record(assignment, run_id, status, code, stopped)
        self._outbox()

    def receive_once(self, execute=False):
        if self.c['mode'] != 'worker': fail('ROLE_REFUSED')
        self.sync_once()
        with self._lock():
            with self._db() as db: interrupted = [dict(r) for r in db.execute("SELECT * FROM inbox WHERE status='RUNNING'")]
            for row in interrupted: self._record(decoded(row['assignment']), row['run_id'], 'UNKNOWN')
            self._outbox()
            head = self.summary()['queue_head']
            for assignment in self._assignments(head):
                if (assignment['owner'], assignment['machine_id']) != (self.c['owner'], self.c['machine_id']): continue
                if assignment['base_revision'] != self.summary()['code_revision']: fail('STALE_REVISION')
                key = assignment['dispatch_id']; fingerprint = digest(encoded(assignment))
                with self._db() as db: saved = db.execute('SELECT * FROM inbox WHERE dispatch_id=?', (key,)).fetchone()
                claim, receipt = self._receipt(head, assignment)
                if saved is None:
                    if claim is not None: continue
                    run_id = uuid.uuid4().hex
                    self._immutable(self.state / 'inbox' / key / 'assignment.json', encoded(assignment))
                    self._immutable(self.state / 'inbox' / key / 'task.md', self._blob(head, 'dispatch/' + key + '/task.md', 65536))
                    with self._db(write=True) as db:
                        db.execute('INSERT INTO inbox VALUES(?,?,?,?,?,?,?,?)',
                            (key, fingerprint, encoded(assignment).decode(), run_id, 'RECEIVED', None, 0, None))
                else:
                    if saved['fingerprint'] != fingerprint: fail('INBOX_CONFLICT')
                    if saved['status'] != 'RECEIVED': continue
                    run_id = saved['run_id']
                claim_value = {k: assignment[k] for k in ('schema_version','dispatch_id','project_id','machine_id','owner','card_sha256')} | dict(run_id=run_id)
                try:
                    published = self._publish({'receipts/' + key + '/claim.json': encoded(claim_value)})
                    verified = self._claim(published, assignment)
                    if verified != claim_value: fail('CLAIM_CONFLICT')
                except HandoffError as error:
                    if str(error) in {'IMMUTABLE_CONFLICT','CLAIM_CONFLICT'}: self._record(assignment, run_id, 'UNKNOWN')
                    raise
                self._record(assignment, run_id, 'RECEIVED'); self._outbox()
                if execute: self._run(assignment, run_id)
                break
        self.sync_once()
        return self.summary()
