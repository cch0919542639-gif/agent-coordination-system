"""Explicit fenced restart reconciliation; never kill a reopened PID or delete work."""
import argparse
import json
from pathlib import Path

from .state_controller import StateController, StateError, _id, _integer
from .parallel_runtime import ParallelController
from .workspace import digest, read_small
from .board_projection import _sha
from .resource_guard import ResourceController, latch


def observe(proof):
    if not isinstance(proof, dict):
        return 'unknown'
    from worker_process_guard import identity_state
    try:
        return identity_state(proof.get('pid'), proof.get('creation_time'))
    except (OSError, RuntimeError):
        return 'unknown'


def stopped(proof, observed):
    return (proof.get('tree_stopped') is True and observed != 'running'
            and type(proof.get('pid')) is int and 0 < proof['pid'] <= 0xffffffff
            and type(proof.get('creation_time')) is int and proof['creation_time'] > 0
            and type(proof.get('exit_code')) is int and 0 <= proof['exit_code'] <= 0xffffffff)


class RecoveryManager:
    def __init__(self, parallel, *, _checkpoint=None):
        self.p = parallel
        self.checkpoint = _checkpoint or (lambda stage: None)

    def _binding(self, db):
        settings = self.p._settings(db)
        if not settings:
            raise StateError('Recovery project binding missing.')
        if settings['mode'] == 'parallel':
            self.p._active(db)
        elif settings['mode'] != 'disabled' or self.p.marker.exists() or self.p.marker.is_symlink():
            raise StateError('Recovery mode marker conflicts.')

    def _health(self, db, row):
        state = self.p.controller._snapshot(db, self.p.project_id, row['task_id'])
        old = db.execute('SELECT * FROM runs WHERE project_id=? AND run_id=?',
                         (self.p.project_id, row['run_id'])).fetchone()
        if not old or any(old[k] != row[k] for k in ('task_id', 'owner', 'fence', 'base_sha')):
            raise StateError('Recovery run binding mismatched.')
        now = self.p.controller._now()
        clock_ok = now >= db.execute('SELECT last_clock_ms FROM metadata WHERE id=1').fetchone()[0]
        proof = json.loads(row['process_json'])
        if not isinstance(proof, dict):
            raise StateError('Recovery process receipt invalid.')
        launched = db.execute("SELECT 1 FROM events WHERE project_id=? AND run_id=? AND event_type IN ('mock.launching','provider.launching') LIMIT 1",
                              (self.p.project_id, row['run_id'])).fetchone()
        prior_never = db.execute("SELECT 1 FROM events WHERE project_id=? AND run_id=? AND event_type='recovery.never_launched' LIMIT 1",
                                 (self.p.project_id, row['run_id'])).fetchone()
        never = (not proof and not launched and (old['phase'] == 'claimed' or prior_never)
                 and row['status'] in {'reserved', 'ready', 'recovery_required'})
        root = 'not_launched' if never else observe(proof)
        lease = bool(clock_ok and state['active_run_id'] == row['run_id']
                     and state['fence'] == row['fence'] and now < old['lease_until_ms']
                     and old['phase'] not in {'completed', 'failed', 'lost', 'recovery_required'})
        workspace = 'invalid';changed = None
        try:
            path = self.p.workspace.path(row['run_id'])
            provisioned = db.execute("SELECT 1 FROM events WHERE project_id=? AND run_id=? AND event_type='workspace.ready' LIMIT 1",
                                     (self.p.project_id, row['run_id'])).fetchone()
            if not path.exists() and never and not provisioned:
                workspace = 'absent_before_provision'
            else:
                checked = self.p.workspace.validate(row)
                workspace = 'bound';changed = len(checked['changed'])
        except (OSError, StateError, ValueError):
            pass
        intents = []
        for intent in db.execute('SELECT request_id,status FROM board_intents WHERE project_id=? AND run_id=? ORDER BY sequence LIMIT 101',
                                  (self.p.project_id, row['run_id'])):
            if len(intents) >= 100:
                raise StateError('Recovery intent inventory exceeds bound.')
            try:
                preview = self.p.board.reconcile(intent['request_id'])
                stage = preview.get('observed', preview['status'])
            except (OSError, StateError, ValueError):
                stage = 'unknown'
            intents.append(dict(request_id=intent['request_id'], status=intent['status'], observed=stage))
        board = 'ambiguous'
        board_bound = False
        try:
            cards = self.p.board._cards(row['task_id'])
            if len(cards) == 1:
                card = next(iter(cards));raw = self.p.board._read(card)
                header = self.p.board._header(raw)
                if (header.get('task_id') == row['task_id']
                        and header.get('status') == card.parent.name.upper()):
                    board = card.parent.name
                    latest = db.execute('SELECT * FROM board_intents WHERE project_id=? AND run_id=? ORDER BY sequence DESC LIMIT 1',
                                        (self.p.project_id, row['run_id'])).fetchone()
                    if latest:
                        cancelled = latest['status'] == 'cancelled'
                        board_bound = (board == latest['source_state' if cancelled else 'target_state']
                                       and _sha(raw) == latest['before_sha' if cancelled else 'after_sha'])
        except (OSError, StateError, ValueError, TypeError):
            pass
        delivery = 'none'
        if row['delivery_sha']:
            try:
                path = self.p.board._path(Path('coordination/delivery') / (row['task_id'] + '-delivery-report.md'))
                delivery = 'bound' if _sha(read_small(path)) == row['delivery_sha'] else 'changed'
            except (OSError, StateError):
                delivery = 'unknown'
        checks = []
        for check in db.execute('SELECT evidence_id,status,process_json,candidate_sha,tested_sha,reviewed_sha FROM evidence_candidates WHERE project_id=? AND run_id=? LIMIT 101',
                                 (self.p.project_id, row['run_id'])):
            if len(checks) >= 100:
                raise StateError('Recovery checker inventory exceeds bound.')
            receipt = json.loads(check['process_json'])
            checks.append(dict(evidence_id=check['evidence_id'], status=check['status'],
                               root_state=observe(receipt) if receipt else 'unknown',
                               candidate_sha=check['candidate_sha'], tested_sha=check['tested_sha'],
                               reviewed_sha=check['reviewed_sha']))
        publications = [dict(r) for r in db.execute('SELECT q.request_id,q.status,q.expected_sha,q.candidate_sha,q.integrated_sha '
                                                   'FROM publication_queue q JOIN evidence_candidates e ON q.project_id=e.project_id AND q.evidence_id=e.evidence_id '
                                                   'WHERE e.project_id=? AND e.run_id=? ORDER BY q.sequence LIMIT 101',
                                                   (self.p.project_id, row['run_id']))]
        if len(publications) > 100:
            raise StateError('Recovery publication inventory exceeds bound.')
        pending = any(i['status'] in {'pending', 'recovery_required'} for i in intents)
        safe = ((never or stopped(proof, root)) and workspace in {'bound', 'absent_before_provision'}
                and not pending and board_bound and delivery in {'none', 'bound'})
        return dict(run_id=row['run_id'], task_id=row['task_id'], status=row['status'],
                    expected_version=state['version'], fence=row['fence'], current_fence=state['fence'],
                    active_run_id=state['active_run_id'], phase=old['phase'], lease_valid=lease,
                    lease_until_ms=old['lease_until_ms'], clock_valid=clock_ok,
                    heartbeat_age_ms=max(0, now-old['heartbeat_ms']) if clock_ok else None,
                    pid=proof.get('pid') if type(proof.get('pid')) is int else None,
                    creation_time=proof.get('creation_time') if type(proof.get('creation_time')) is int else None,
                    root_state=root, tree_stop_proven=stopped(proof, root), never_launched=never,
                    workspace=workspace, changed_count=changed, board=board, board_bound=board_bound, intents=intents,
                    delivery=delivery, checks=checks, publications=publications, safe_to_release=safe)

    def inspect(self, run_id):
        with self.p.controller._db() as db:
            self._binding(db)
            return self._health(db, self.p._row(db, run_id))

    def scan(self, *, after_run_id='', limit=100):
        if after_run_id:
            _id(after_run_id)
        _integer(limit, 1, 100)
        with self.p.controller._db() as db:
            self._binding(db)
            rows = db.execute('SELECT * FROM parallel_runs WHERE project_id=? AND run_id>? ORDER BY run_id LIMIT ?',
                              (self.p.project_id, after_run_id, limit)).fetchall()
            return dict(runs=[self._health(db, dict(r)) for r in rows],
                        next_after=rows[-1]['run_id'] if len(rows) == limit else '',
                        breaker=latch(db, self.p.project_id))

    def reconcile(self, run_id, request_id, expected_version, expected_fence, reason, *, execute=False):
        _id(run_id);_id(request_id);_integer(expected_version);_integer(expected_fence, 1)
        if reason not in {'expired', 'interrupted'}:
            raise StateError('Recovery reason invalid.')
        spec = dict(recovery_run=run_id, request_id=request_id, expected_version=expected_version,
                    expected_fence=expected_fence, reason=reason)
        key = digest(spec)
        with self.p.controller._db(write=execute) as db:
            self._binding(db)
            prior = db.execute('SELECT digest,result_json FROM requests WHERE project_id=? AND request_id=?',
                               (self.p.project_id, request_id)).fetchone()
            if prior:
                if prior['digest'] != key:
                    raise StateError('Recovery request key conflicts.')
                return dict(json.loads(prior['result_json']), historical=True)
            row = self.p._row(db, run_id);health = self._health(db, row);now = self.p._now(db)
            if health['expected_version'] != expected_version or row['fence'] != expected_fence:
                raise StateError('Recovery version or fence changed.')
            active = health['active_run_id'] == run_id and health['current_fence'] == expected_fence
            retired = health['active_run_id'] is None and health['current_fence'] == expected_fence+1
            if not active and not retired:
                raise StateError('Recovery generation is stale.')
            if active and reason == 'expired' and now < health['lease_until_ms']:
                raise StateError('Recovery lease has not expired.')
            if active and reason == 'interrupted' and health['lease_valid'] and health['root_state'] == 'running':
                raise StateError('Healthy running authority cannot be recovered.')
            result = dict(run_id=run_id, status='released' if health['safe_to_release'] else 'recovery_required',
                          authority_revoked=True, candidate_preserved=True, tree_stop_proven=health['tree_stop_proven'])
            if row['status'] == 'released':
                return dict(result, status='released', historical=True)
            if not execute:
                return dict(result, dry_run=True)
            if active:
                if health['never_launched']:
                    self.p._audit(db, 'recovery.never_launched', row)
                command = dict(op='revoke', project_id=self.p.project_id, task_id=row['task_id'],
                               run_id=run_id, actor='recovery-controller', reason=reason,
                               fence=expected_fence, expected_version=expected_version,
                               request_id=digest(['phase4.revoke', request_id]))
                self.p.controller.apply(command, _parallel=True, _connection=db)
            self.checkpoint('recovery.revoked')
            self.p._update(db, row, 'recovery.' + result['status'], status=result['status'])
            db.execute('INSERT INTO requests VALUES(?,?,?,?)',
                       (self.p.project_id, request_id, key, json.dumps(result, sort_keys=True)))
        return result


class PrivateParser(argparse.ArgumentParser):
    def error(self, message):
        raise StateError('Invalid recovery arguments.')


def main(argv=None):
    parser = PrivateParser(description=__doc__)
    for flag in ('db', 'repo', 'workspaces'):
        parser.add_argument('--'+flag, type=Path, required=True)
    parser.add_argument('--project-id', required=True)
    subs = parser.add_subparsers(dest='action', required=True)
    inspect = subs.add_parser('inspect');inspect.add_argument('--run-id', required=True)
    scan = subs.add_parser('scan');scan.add_argument('--after-run-id', default='');scan.add_argument('--limit', type=int, default=100)
    subs.add_parser('resources')
    probe = subs.add_parser('probe');probe.add_argument('--execute', action='store_true')
    reset = subs.add_parser('reset');reset.add_argument('--expected-sequence', type=int, required=True);reset.add_argument('--execute', action='store_true')
    rec = subs.add_parser('reconcile')
    for flag in ('run-id', 'request-id', 'reason'):
        rec.add_argument('--'+flag, required=True)
    for flag in ('expected-version', 'expected-fence'):
        rec.add_argument('--'+flag, type=int, required=True)
    rec.add_argument('--execute', action='store_true')
    try:
        args = parser.parse_args(argv)
        p = ParallelController(StateController(args.db), args.repo, args.workspaces, args.project_id)
        recovery = RecoveryManager(p);resources = ResourceController(p)
        if args.action == 'inspect':result = recovery.inspect(args.run_id)
        elif args.action == 'scan':result = recovery.scan(after_run_id=args.after_run_id, limit=args.limit)
        elif args.action in {'resources', 'probe'}:result = resources.probe(execute=args.action == 'probe' and args.execute)
        elif args.action == 'reset':result = resources.reset(args.expected_sequence, execute=args.execute)
        else:result = recovery.reconcile(args.run_id, args.request_id, args.expected_version, args.expected_fence, args.reason, execute=args.execute)
        text = json.dumps(result, sort_keys=True)
        if len(text.encode()) > 65536:
            raise StateError('Recovery output exceeds bound.')
        print(text)
        return 1 if result.get('status') == 'recovery_required' or result.get('state') == 'open' else 0
    except (StateError, OSError, ValueError, RecursionError, TypeError):
        print(json.dumps(dict(error='recovery_refused', reason='input_state_or_io_refused')))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
