"""Local bare Git only, finite synthetic runner and adversarial cooperative receipts."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from coordination_runtime.github_handoff import HandoffService, HandoffError, ZERO, encoded, digest
from coordination_runtime import github_handoff as implementation


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.DEVNULL).decode().strip()


@pytest.fixture
def pilot(tmp_path):
    remote = tmp_path / 'remote.git'; source = tmp_path / 'source'
    subprocess.run(['git', 'init', '--bare', '-q', str(remote)], check=True, capture_output=True)
    source.mkdir(); git(source, 'init', '-q'); git(source, 'config', 'user.name', 'Fixture'); git(source, 'config', 'user.email', 'fixture@example.invalid')
    folder = source / 'coordination/task-board/ready'; folder.mkdir(parents=True)
    card = folder / 'task-one.md'
    card.write_text('---\ntask_id: task-one\nstatus: READY\nowner: worker\nallowed_scope:\n  - src/**\nforbidden_scope:\n  - secrets/**\ndependencies: []\n---\nSynthetic task\n')
    (source / 'src').mkdir(); (source / 'src/value.txt').write_text('base')
    git(source, 'add', '.'); git(source, 'commit', '-qm', 'fixture'); revision = git(source, 'rev-parse', 'HEAD')
    git(source, 'remote', 'add', 'origin', str(remote)); git(source, 'push', '-q', 'origin', 'HEAD:refs/heads/code')
    runner = tmp_path / 'trusted.py'; marker = tmp_path / 'marker.txt'
    runner.write_text('import json,pathlib,sys\npayload=json.loads(pathlib.Path(sys.argv[2]).read_text())\nwith pathlib.Path(sys.argv[1]).open("a") as f:f.write(payload["run_id"]+"\\n")\n')
    base = dict(schema_version=1, mode='coordinator', project_id='project', repository=str(source), state_dir='',
        remote_url=str(remote), code_ref='refs/heads/code', queue_ref='refs/heads/codex/handoff-fixture', machine_id='A', owner='boss',
        peers=[dict(machine_id='B', owner='worker')], evidence_ref_prefix=None, evidence_revision=revision,
        min_tests=2, runner=dict(argv=[sys.executable, '-B', str(runner), str(marker)], script=str(runner), sha256=digest(runner.read_bytes()), timeout_seconds=5), execution_enabled=True)
    def service(name, worker=False, **changes):
        repo = source
        if worker:
            repo = tmp_path / (name + '-repo')
            subprocess.run(['git', 'clone', '-q', '--branch', 'code', str(remote), str(repo)], check=True, capture_output=True)
        config = base | dict(mode='worker' if worker else 'coordinator', repository=str(repo), state_dir=str(tmp_path / (name + '-state')),
            machine_id='B' if worker else 'A', owner='worker' if worker else 'boss') | changes
        path = tmp_path / (name + '.json'); path.write_bytes(encoded(config))
        return HandoffService(path, repo, config['project_id'])
    return dict(remote=remote, source=source, card=card, revision=revision, runner=runner, marker=marker, service=service)


def dispatched(pilot):
    sender = pilot['service']('sender'); sender.initialize(); summary = sender.sync_once()
    args = dict(task_id='task-one', machine_id='B', expected_card_sha256=digest(pilot['card'].read_bytes()),
        expected_revision=pilot['revision'], expected_queue_head=summary['queue_head'])
    preview = sender.dispatch(**args)
    assert preview['status'] == 'PREVIEW' and summary['queue_head'] == ZERO
    result = sender.dispatch(**args, execute=True)
    return sender, result['dispatch_id'], args


def test_summary_is_readonly_and_foreign_binding_refused(pilot, monkeypatch):
    service = pilot['service']('empty')
    monkeypatch.setattr(service, '_git', lambda *a, **k: (_ for _ in ()).throw(AssertionError('network')))
    assert not service.summary()['initialized'] and not service.state.exists()
    other = pilot['service']('configured'); other.initialize()
    before = other.database.read_bytes(); other.initialize(); assert other.database.read_bytes() == before
    with sqlite3.connect(other.database) as db: db.execute("UPDATE metadata SET binding='foreign'")
    before = other.database.read_bytes()
    with pytest.raises(HandoffError): other.initialize()
    assert other.database.read_bytes() == before


@pytest.mark.parametrize('pending', [False, True])
def test_local_bare_end_to_end_unique_claim_job_and_outbox_replay(pilot, monkeypatch, pending):
    before = git(pilot['source'], 'status', '--porcelain'); index = (pilot['source'] / '.git/index').read_bytes()
    sender, key, args = dispatched(pilot)
    worker = pilot['service']('worker', worker=True); worker.initialize(); worker.receive_once()
    twin = pilot['service']('twin', worker=True); twin.initialize(); twin.receive_once(execute=True)
    assert not pilot['marker'].exists()
    publish = worker._publish
    job = implementation.JobProcess
    def claimed_job(command, **kwargs):
        payload = json.loads(Path(command[-1]).read_bytes())
        claim = worker._claim(worker._fetch_queue(), payload['assignment'])
        assert claim['run_id'] == payload['run_id']
        assert kwargs['capture_output'] is False
        return job(command, **kwargs)
    monkeypatch.setattr(implementation, 'JobProcess', claimed_job)
    if pending:
        def fail_finish(updates, *a, **k):
            if any(b'"status":"FINISHED"' in raw for raw in updates.values()): raise HandoffError('SYNTHETIC_OFFLINE')
            return publish(updates, *a, **k)
        monkeypatch.setattr(worker, '_publish', fail_finish)
    result = worker.receive_once(execute=True)
    assert result['dispatches'][0]['status'] == 'FINISHED' and result['dispatches'][0]['exit_code'] == 0
    assert len(pilot['marker'].read_text().splitlines()) == 1
    if pending: assert result['last_error'] == 'OUTBOX_PENDING'
    monkeypatch.setattr(worker, '_publish', publish)
    worker.receive_once(execute=True); twin.receive_once(execute=True)
    result = sender.sync_once()
    assert result['dispatches'][0]['status'] == 'FINISHED'
    assert len(pilot['marker'].read_text().splitlines()) == 1
    assert git(pilot['source'], 'status', '--porcelain') == before and (pilot['source'] / '.git/index').read_bytes() == index
    assert str(worker.state) not in json.dumps(result) and 'argv' not in json.dumps(result)


def test_stale_card_revision_and_queue_refuse(pilot):
    sender, key, args = dispatched(pilot)
    with pytest.raises(HandoffError): sender.dispatch(**args, execute=True)
    args['expected_queue_head'] = sender.summary()['queue_head']
    assert sender.dispatch(**args, execute=True)['dispatch_id'] == key
    pilot['card'].write_text(pilot['card'].read_text() + 'changed')
    with pytest.raises(HandoffError, match='ASSIGNMENT_REFUSED'): sender.dispatch(**args)
    pilot['card'].write_text(pilot['card'].read_text().removesuffix('changed'))
    (pilot['source'] / 'src/value.txt').write_text('new code'); git(pilot['source'], 'add', '.'); git(pilot['source'], 'commit', '-qm', 'new code')
    git(pilot['source'], 'push', '-q', 'origin', 'HEAD:refs/heads/code')
    with pytest.raises(HandoffError, match='STALE_REVISION'): sender.dispatch(**args, execute=True)


def test_runner_hash_and_interrupted_running_never_launch(pilot):
    sender, key, args = dispatched(pilot)
    worker = pilot['service']('worker', worker=True); worker.initialize(); worker.receive_once()
    pilot['runner'].write_text(pilot['runner'].read_text() + '# drift\n')
    with pytest.raises(HandoffError, match='RUNNER_CHANGED'): worker.receive_once(execute=True)
    with sqlite3.connect(worker.database) as db: db.execute("UPDATE inbox SET status='RUNNING'")
    result = worker.receive_once(execute=True)
    assert result['dispatches'][0]['status'] == 'UNKNOWN' and not pilot['marker'].exists()
    assert sender.sync_once()['dispatches'][0]['status'] == 'UNKNOWN'


def test_wrong_identity_and_project_do_not_receive(pilot):
    dispatched(pilot)
    wrong = pilot['service']('wrong', worker=True, owner='another')
    wrong.initialize(); wrong.receive_once(execute=True)
    with wrong._db() as db: assert db.execute('SELECT count(*) FROM inbox').fetchone()[0] == 0
    foreign = pilot['service']('foreign', worker=True, project_id='other')
    foreign.initialize()
    with pytest.raises(HandoffError, match='INVALID_ASSIGNMENT'): foreign.receive_once(execute=True)
    assert not pilot['marker'].exists()


def publish_evidence(pilot, kind):
    folder = pilot['source'] / 'coordination/evidence/fixture'; folder.mkdir(parents=True, exist_ok=True)
    checks = {name: dict(exit_code=2 if name == 'init-conflict' else 0, expected=2 if name == 'init-conflict' else 0)
        for name in ('head','init','init-replay','init-conflict','focused-tests','git-status')}
    checks.update({'manifest': dict(passed=47), 'replay-and-conflict-preserve-bytes': True,
        'schema4-disabled-no-runs-unchanged-private-files': True})
    for name in ('serve-0','serve-1'):
        checks[name] = dict(exit_code=0, finite_exit=True, viewer_writes=403, views={view:dict(status=200,runtime_available=True)
            for view in ('overview','board','monitor','workspaces','reviews','events','settings')})
    result = dict(commit=pilot['revision'], status='PASS', checks=checks,
        environment=dict(preferred_encoding='cp950', utf8_mode=0, PYTHONUTF8=None, PYTHONIOENCODING=None))
    if kind == 'exit': checks['focused-tests'].update(exit_code=1, expected=1)
    if kind == 'missing': del checks['init']
    if kind == 'stale': result['commit'] = 'a' * 40
    if kind == 'override': result['environment']['PYTHONUTF8'] = '1'
    if kind == 'fail': result['status'] = 'FAIL'
    junit = b'<testsuites><testsuite tests="2" failures="0" errors="0" skipped="0"><testcase name="one"/><testcase name="two"/></testsuite></testsuites>'
    if kind == 'junit': junit = junit.replace(b'failures="0"', b'failures="1"')
    (folder / 'results.json').write_bytes(encoded(result)); (folder / 'junit.xml').write_bytes(junit)
    manifest = dict(tested_commit=result['commit'], files={n:digest((folder/n).read_bytes()) for n in ('results.json','junit.xml')})
    if kind == 'hash': manifest['files']['junit.xml'] = '0' * 64
    (folder / 'publication-manifest.json').write_bytes(encoded(manifest))
    git(pilot['source'], 'add', '.'); git(pilot['source'], 'commit', '-qm', 'evidence ' + kind)
    git(pilot['source'], 'push', '-q', 'origin', 'HEAD:refs/heads/docs/console-fixture')


def test_discovery_hash_native_junit_revision_and_offline_status(pilot, monkeypatch):
    (pilot['card'].parent / 'legacy.md').write_text('---\ntask_id: legacy\nstatus: READY\nowner: UNASSIGNED\nallowed_scope:\n  - tests/** if needed\n---\nLegacy unrelated card\n')
    service = pilot['service']('evidence', evidence_ref_prefix='refs/heads/docs/console-')
    service.initialize()
    for kind, expected in [('good','VERIFIED_PASS'), ('hash','INVALID'), ('exit','INVALID'), ('missing','INVALID'),
                           ('junit','INVALID'), ('override','INVALID'), ('stale','STALE'), ('fail','FAIL')]:
        publish_evidence(pilot, kind)
        summary = service.sync_once()
        assert summary['acceptance'][0]['status'] == expected
        assert [row['task_id'] for row in summary['ready_tasks']] == ['task-one']
    before = service.summary()['last_sync_ms']
    monkeypatch.setattr(service, '_git', lambda *a, **k: (_ for _ in ()).throw(HandoffError('TRANSPORT_FAILED')))
    with pytest.raises(HandoffError): service.sync_once()
    summary = service.summary()
    assert summary['last_sync_ms'] == before and summary['last_error'] == 'TRANSPORT_FAILED'


def test_timeout_is_failed_stopped_and_not_retried(pilot):
    pilot['runner'].write_text('import time\ntime.sleep(30)\n')
    sender, key, args = dispatched(pilot)
    service = pilot['service']('timeout', worker=True, runner=dict(
        argv=[sys.executable, '-B', str(pilot['runner']), str(pilot['marker'])],
        script=str(pilot['runner']), sha256=digest(pilot['runner'].read_bytes()), timeout_seconds=1))
    service.initialize()
    result = service.receive_once(execute=True)
    assert result['dispatches'][0]['status'] == 'FAILED'
    with service._db() as db: assert db.execute('SELECT tree_stopped FROM inbox').fetchone()[0] == 1
    service.receive_once(execute=True)


def test_cli_summary_and_watch_budget(pilot):
    service = pilot['service']('cli')
    command = [sys.executable, '-I', '-B', str(ROOT / 'scripts/github_handoff.py'), '--config', str(service.config_path)]
    result = subprocess.run(command + ['summary'], capture_output=True, timeout=20)
    assert result.returncode == 0 and not json.loads(result.stdout)['initialized']
    result = subprocess.run(command + ['watch','--cycles','121'], capture_output=True, timeout=20)
    assert result.returncode == 2 and not service.state.exists()
