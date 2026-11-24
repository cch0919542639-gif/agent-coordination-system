"""Read-only HTTP and real Windows supervisor failure/stop boundaries."""
import hashlib
import http.server
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts'), str(ROOT / 'tests/scripts')]
import console_monitor as monitor
import console_setup as setup
from test_parallel_runtime import system
from test_web_console import console, request, login
from test_github_handoff import pilot, git
from test_console_setup import request as setup_request, snapshot
from web.api import Refused
from worker_process_guard import GuardError, JobProcess, identity_state


def test_monitor_downgrades_admin_and_denies_all_controller_routes(console):
    app = console['app']; app.read_only = True
    before = hashlib.sha256(console['db'].path.read_bytes()).hexdigest()
    admin = login(console, 'administrator')
    assert admin['role'] == 'viewer'
    for view in ('overview', 'board', 'monitor', 'workspaces', 'reviews', 'events', 'settings', 'handoff'):
        assert request(console, '/api/view?name=' + view, session=admin)[0] == 200
    for route in ('inspect', 'preview', 'execute'):
        assert request(console, '/api/' + route, {}, admin)[0] == 403
    # Integration: the newer Agent and direct-model routes remain unavailable
    # even when the user authenticated with an Administrator account.
    assert request(console, '/api/direct/models', session=admin)[0] == 403
    assert request(console, '/api/agent/start', {'agent': 'opencode'}, admin)[0] == 403
    assert request(console, '/api/agent/start', {'agent': 'direct', 'api_key': 'fixture', 'model': 'vendor/model'}, admin)[0] == 403
    assert request(console, '/api/agent/report', {}, admin)[0] == 403
    assert not console['app'].agent_sessions
    with pytest.raises(Refused) as error:
        app.action('handoff.dispatch', {}, execute=True)
    assert error.value.status == 403
    assert hashlib.sha256(console['db'].path.read_bytes()).hexdigest() == before
    assert request(console, '/api/logout', {}, admin)[0] == 200


def test_monitor_health_requires_read_only(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(setup, 'load', lambda *args: SimpleNamespace())
    with pytest.raises(setup.StateError):
        setup.serve('unused', duration=0, monitor_health_file='unused')


def test_health_requires_owned_read_only_proof(console):
    port = console['server'].server_port
    secret = 'a' * 64
    assert not monitor.healthy(port, os.getpid(), secret)
    console['app'].read_only = True
    console['app'].monitor_health_secret = secret
    assert monitor.healthy(port, os.getpid(), secret)
    assert not monitor.healthy(port, os.getpid() + 1, secret)
    assert not monitor.healthy(port, os.getpid(), 'b' * 64)
    console['app'].read_only = False
    assert not monitor.healthy(port, os.getpid(), secret)


@pytest.mark.skipif(os.name != 'nt', reason='Windows owned Jobs')
def test_health_requires_valid_proof_and_live_job_member(console):
    secret = 'a' * 64
    console['app'].read_only = True
    console['app'].monitor_health_secret = secret
    port = console['server'].server_port
    child = JobProcess([sys.executable, '-c', 'import time; time.sleep(30)'], cwd=ROOT)
    try:
        child.resume()
        assert child.owns_pid(child.pid)
        assert not child.owns_pid(os.getpid())
        assert not child.owns_pid(True)
        assert monitor.health_pid(port, secret, child.owns_pid) is None
        assert monitor.health_pid(port, 'b' * 64, lambda pid: True) is None
        assert monitor.health_pid(port, secret, lambda pid: True) == os.getpid()
        assert monitor.health_pid(port, secret, lambda pid: (_ for _ in ()).throw(GuardError('failed'))) is None
    finally:
        child.stop()
        child.close()
    assert not child.owns_pid(child.pid)


def test_status_retries_sharing_denial_and_fails_closed(tmp_path, monkeypatch):
    import contextlib
    attempts = []
    def read(path):
        attempts.append(path)
        if len(attempts) < 3:
            raise PermissionError('sharing denial')
        return {'phase': 'stopped'}
    monkeypatch.setattr(monitor, 'read_json', read)
    monkeypatch.setattr(monitor, 'owner_lock', lambda root: contextlib.nullcontext())
    monkeypatch.setattr(monitor.time, 'sleep', lambda delay: None)
    assert monitor.status(tmp_path)['phase'] == 'stopped'
    assert len(attempts) == 3
    def denied(path):
        attempts.append(path)
        raise PermissionError('persistent denial')
    attempts.clear()
    monkeypatch.setattr(monitor, 'read_json', denied)
    with pytest.raises(PermissionError):
        monitor.status(tmp_path)
    assert len(attempts) == 20


def test_job_membership_api_failures_are_rejected():
    from types import SimpleNamespace
    child = JobProcess.__new__(JobProcess)
    child.job = 1
    closed = []
    child.api = SimpleNamespace(OpenProcess=lambda *args: 0)
    assert not child.owns_pid(123)
    child.api = SimpleNamespace(OpenProcess=lambda *args: 2,
                                WaitForSingleObject=lambda *args: 258,
                                IsProcessInJob=lambda *args: 0,
                                CloseHandle=closed.append)
    assert not child.owns_pid(123)
    assert closed == [2]


def test_foreign_http_200_cannot_report_monitor_healthy():
    class Foreign(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b'unrelated service')
        def log_message(self, *args): pass
    server = http.server.HTTPServer(('127.0.0.1', 0), Foreign)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        assert not monitor.healthy(server.server_port, os.getpid(), 'a' * 64)
    finally:
        server.shutdown(); server.server_close(); thread.join(3)


def test_health_secret_is_not_written_before_private_mode(tmp_path, monkeypatch):
    from types import SimpleNamespace
    seen = []
    chmod = Path.chmod
    def checked(path, mode):
        seen.append((mode, path.stat().st_size))
        chmod(path, mode)
    monkeypatch.setattr(monitor, 'os', SimpleNamespace(name='posix'))
    monkeypatch.setattr(Path, 'chmod', checked)
    monitor.write(tmp_path, 'health.json', {'secret': 'a' * 64})
    assert seen == [(0o600, 0)]


def test_supervisor_never_marks_foreign_service_running(tmp_path, monkeypatch):
    from types import SimpleNamespace
    class Foreign(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b'unrelated service')
        def log_message(self, *args): pass
    class Child:
        pid = 123
        def owns_pid(self, pid): return False
        def wait(self, timeout): raise subprocess.TimeoutExpired('fixture', timeout)
        def stop(self): pass
        def close(self): pass
    server = http.server.HTTPServer(('127.0.0.1', 0), Foreign)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    clock = [0]; snapshots = []
    def sleep(seconds):
        clock[0] += seconds
        if clock[0] > 40: raise KeyboardInterrupt()
    real_write = monitor.write
    def capture(root, name, value):
        if name == 'session.json': snapshots.append(value.copy())
        real_write(root, name, value)
    monkeypatch.setattr(monitor, 'time', SimpleNamespace(monotonic=lambda: clock[0], sleep=sleep, time_ns=lambda: 0))
    monkeypatch.setattr(monitor, 'launch', lambda args: Child())
    monkeypatch.setattr(monitor, 'write', capture)
    try:
        monitor.supervise(tmp_path, ['server'], ['sync'], server.server_port)
        assert snapshots and all(x['phase'] != 'running' for x in snapshots)
        assert max(x['server_restarts'] for x in snapshots) >= 1
    finally:
        server.shutdown(); server.server_close(); thread.join(3)


@pytest.mark.parametrize('failed', ['server', 'sync'])
@pytest.mark.parametrize('failure', [OSError, GuardError])
def test_launch_failure_is_terminal_failure_not_normal_stop(tmp_path, monkeypatch, failed, failure):
    closed = []
    class Child:
        pid = 1
        def stop(self): closed.append('stop')
        def close(self): closed.append('close')
    def launch(args):
        if args == [failed]: raise failure('synthetic launch failure')
        return Child()
    monkeypatch.setattr(monitor, 'launch', launch)
    with pytest.raises(failure):
        monitor.supervise(tmp_path, ['server'], ['sync'], 8766)
    state = setup.read_json(tmp_path / 'session.json')
    assert state['phase'] == 'failed' and not state['running']
    assert state['failure'] == failed.upper() + '_LAUNCH_FAILED'
    assert closed == (['stop', 'close'] if failed == 'sync' else [])
    if os.name == 'nt':
        assert monitor.status(tmp_path)['phase'] == 'failed'


@pytest.mark.skipif(os.name != 'nt', reason='Windows file sharing semantics')
def test_health_file_replacement_failure_records_failed_start(tmp_path, monkeypatch):
    monitor.write(tmp_path, 'health.json', {'secret': 'a' * 64})
    monkeypatch.setattr(monitor, 'launch', lambda args: pytest.fail('child must not launch'))
    with (tmp_path / 'health.json').open('rb'):
        with pytest.raises(PermissionError):
            monitor.supervise(tmp_path, ['server'], ['sync'], 8766)
    state = setup.read_json(tmp_path / 'session.json')
    assert state['phase'] == 'failed' and state['failure'] == 'HEALTH_SETUP_FAILED'
    assert setup.read_json(tmp_path / 'health.json')['secret'] == 'a' * 64


def test_unconfirmed_cleanup_is_never_reported_as_stopped(tmp_path, monkeypatch):
    class Child:
        pid = 1
        def stop(self):
            raise GuardError('synthetic_cleanup_unconfirmed')
        def close(self):
            pass
    monkeypatch.setattr(monitor, 'launch', lambda args: Child())
    def interrupt(seconds):
        raise KeyboardInterrupt()
    monkeypatch.setattr(monitor.time, 'sleep', interrupt)
    with pytest.raises(GuardError):
        monitor.supervise(tmp_path, [], [], 8766)
    assert json.loads((tmp_path / 'session.json').read_text())['phase'] == 'cleanup_unconfirmed'


@pytest.mark.skipif(os.name != 'nt', reason='Windows file sharing semantics')
def test_status_reader_sharing_retries_and_permanent_denial_preserves_state(tmp_path, monkeypatch):
    monitor.write(tmp_path, 'session.json', dict(phase='old'))
    failed_replace = threading.Event()
    replace = Path.replace
    errors = []
    def observed_replace(source, target):
        try:
            return replace(source, target)
        except PermissionError:
            failed_replace.set()
            raise
    monkeypatch.setattr(Path, 'replace', observed_replace)
    def writer():
        try:
            monitor.write(tmp_path, 'session.json', dict(phase='new'))
        except Exception as error:
            errors.append(type(error).__name__)
    with (tmp_path / 'session.json').open('rb') as reader:
        thread = threading.Thread(target=writer)
        thread.start()
        assert failed_replace.wait(3), 'real Windows reader did not deny replace'
        assert json.loads(reader.read())['phase'] == 'old'
    thread.join(3)
    assert not thread.is_alive() and not errors
    assert setup.read_json(tmp_path / 'session.json')['phase'] == 'new'
    attempts = []
    def always_denied(source, target):
        attempts.append(1)
        raise PermissionError('synthetic permanent sharing denial')
    monkeypatch.setattr(Path, 'replace', always_denied)
    monkeypatch.setattr(monitor.time, 'sleep', lambda seconds: None)
    with pytest.raises(PermissionError):
        monitor.write(tmp_path, 'session.json', dict(phase='must-not-appear'))
    assert len(attempts) == 20
    assert setup.read_json(tmp_path / 'session.json')['phase'] == 'new'
    assert not list(tmp_path.glob('*.tmp'))


@pytest.mark.skipif(os.name != 'nt', reason='Windows owned Jobs')
def test_keyboard_interrupt_cleans_real_owned_children(tmp_path, monkeypatch):
    children = []
    launch = monitor.launch
    sleep = time.sleep
    interrupted = False
    def observed_launch(arguments):
        child = launch(arguments)
        children.append((child.pid, child.creation_time))
        return child
    def interrupt_once(seconds):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise KeyboardInterrupt()
        sleep(seconds)
    monkeypatch.setattr(monitor, 'launch', observed_launch)
    monkeypatch.setattr(monitor.time, 'sleep', interrupt_once)
    arguments = ['-c', 'import time; time.sleep(60)']
    value = monitor.supervise(tmp_path, arguments, arguments, 8766)
    assert interrupted and len(children) == 2 and value['phase'] == 'stopped'
    assert all(identity_state(pid, created) in ('missing', 'exited') for pid, created in children)


@pytest.mark.skipif(os.name != 'nt', reason='Windows owned Jobs and file locks')
def test_real_supervisor_restart_timeout_duplicate_stop_and_owned_tree(tmp_path):
    state = tmp_path / 'private'
    root = monitor.session_root(str(state), create=True)
    monitor.write(root, 'stop.json', dict(run_id='previous-session'))
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
    server = tmp_path / 'server.py'
    server.write_text('''import hashlib,hmac,http.server,json,os,pathlib,sys,urllib.parse
marker=pathlib.Path(sys.argv[1])
if not marker.exists():
    marker.write_text('first failure')
    sys.exit(7)
secret=json.loads(pathlib.Path(sys.argv[3]).read_text())['secret']
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        nonce=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)['nonce'][0]
        proof=hmac.new(bytes.fromhex(secret),(nonce+':'+str(os.getpid())).encode(),hashlib.sha256).hexdigest()
        self.send_response(200);self.end_headers();self.wfile.write(json.dumps(dict(pid=os.getpid(),read_only=True,proof=proof)).encode())
    def log_message(self,*args):pass
http.server.HTTPServer(('127.0.0.1',int(sys.argv[2])),Handler).serve_forever()
''')
    sync = tmp_path / 'sync.py'
    sync.write_text('''import json, pathlib, subprocess, sys, time
sys.path.insert(0,sys.argv[2])
from worker_process_guard import creation_time
import ctypes
marker=pathlib.Path(sys.argv[1]); n=int(marker.read_text())+1 if marker.exists() else 1
marker.write_text(str(n))
if n==1: sys.exit(2)
if n==2:
    child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])
    pathlib.Path(sys.argv[3]).write_text(json.dumps(dict(pid=child.pid,created=creation_time(int(child._handle)))))
    time.sleep(60)
''')
    server_args = [str(server), str(tmp_path / 'server-starts'), str(port), str(root / 'health.json')]
    sync_args = [str(sync), str(tmp_path / 'sync-starts'), str(ROOT / 'scripts'), str(tmp_path / 'descendant.json')]
    code = '''import sys
sys.path.insert(0,sys.argv[1])
import console_monitor as m
from pathlib import Path
with m.owner_lock(Path(sys.argv[2])):
    m.supervise(Path(sys.argv[2]), %r, %r, %r, interval=1, sync_timeout=2)
''' % (server_args, sync_args, port)
    with JobProcess([sys.executable, '-B', '-c', code, str(ROOT / 'scripts'), str(root)], cwd=ROOT) as child:
        child.resume()
        try:
            deadline = time.monotonic() + 30
            snapshots = []
            while time.monotonic() < deadline:
                if (root / 'session.json').exists():
                    value = monitor.status(root); snapshots.append(value)
                    if value['phase'] == 'running' and value['last_sync_exit'] == 0:
                        break
                time.sleep(.2)
            else:
                pytest.fail('supervisor did not recover within30seconds')
            assert value['running'] and value['server_restarts'] == 1
            assert any(v['sync_error'] == 'SYNC_FAILED' for v in snapshots)
            assert any(v['sync_error'] == 'SYNC_TIMEOUT' for v in snapshots)
            assert value['sync_attempts'] >= 3
            with pytest.raises(setup.StateError, match='already running'):
                with monitor.owner_lock(root):
                    pytest.fail('duplicate owner acquired lock')
            descendant = json.loads((tmp_path / 'descendant.json').read_text())
            assert identity_state(descendant['pid'], descendant['created']) in ('missing', 'exited')
            assert monitor.request_stop(root)['stop_requested']
            assert child.wait(10) == 0 and child.wait_empty(3)
            assert monitor.status(root)['phase'] == 'stopped'
            assert not monitor.status(root)['running']
            assert not monitor.healthy(port, 1, 'a' * 64)
            assert not monitor.request_stop(root)['stop_requested']
        finally:
            child.stop()


@pytest.mark.skipif(os.name != 'nt', reason='Windows manual monitor entry')
def test_full_start_real_http_local_git_sync_and_cli_stop(pilot, tmp_path):
    service = pilot['service']('monitor', runner=None, execution_enabled=False)
    service.initialize()
    state = tmp_path / 'console-private'
    config = setup.settings(str(pilot['source']), str(tmp_path / 'workspaces'),
                            'project', str(state), username='admin', role='administrator')
    setup.initialize(config)
    before = snapshot(state)
    refs = git(pilot['remote'], 'show-ref')
    index = (pilot['source'] / '.git/index').read_bytes()
    token = (state / 'login.txt').read_text().split('Token: ')[1].strip()
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
    command = [sys.executable, '-B', str(ROOT / 'scripts/console_monitor.py')]
    with JobProcess(command + ['start', '--state-dir', str(state), '--handoff-config',
                               str(service.config_path), '--port', str(port)], cwd=ROOT) as child:
        child.resume()
        try:
            root = state.with_name(state.name + '.monitor')
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if (root / 'session.json').exists():
                    value = monitor.status(root)
                    if value['phase'] == 'running' and value['last_sync_exit'] == 0:
                        break
                time.sleep(.2)
            else:
                pytest.fail('real monitor failed to start/sync')
            health_secret = setup.read_json(root / 'health.json')['secret']
            assert len(health_secret) == 64 and health_secret not in json.dumps(value)
            first_run = value['run_id']
            status, body, cookie = setup_request(port, '/api/login', dict(username='admin', token=token))
            assert status == 200 and body['role'] == 'viewer'
            session = (cookie.split(';')[0], body['csrf'])
            status, body, _ = setup_request(port, '/api/view?name=handoff', session=session)
            assert status == 200 and body['handoff']['last_sync_ms'] is not None
            assert body['handoff']['last_error'] is None
            assert setup_request(port, '/api/preview', dict(action='handoff.dispatch', args={}), session)[0] == 403
            assert setup_request(port, '/api/direct/models', session=session)[0] == 403
            assert setup_request(port, '/api/agent/start', dict(agent='direct', api_key='fixture', model='vendor/model'), session)[0] == 403
            stopped = subprocess.run(command + ['stop', '--state-dir', str(state)],
                                     capture_output=True, timeout=10)
            assert stopped.returncode == 0 and json.loads(stopped.stdout)['stop_requested']
            assert child.wait(10) == 0 and child.wait_empty(3)
            assert monitor.status(root)['phase'] == 'stopped'
        finally:
            child.stop()
    # A stale file with invalid contents and ACL must be replaced by the new start.
    (root / 'health.json').write_text('{}', encoding='utf-8')
    subprocess.run(['icacls', str(root / 'health.json'), '/grant:r', '*S-1-5-18:F'],
                   capture_output=True, check=True, timeout=10)
    with pytest.raises(setup.StateError):
        setup.require_private(root / 'health.json', inherited=True)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); second_port = probe.getsockname()[1]
    with JobProcess(command + ['start', '--state-dir', str(state), '--handoff-config',
                               str(service.config_path), '--port', str(second_port)], cwd=ROOT) as child:
        child.resume()
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                value = monitor.status(root)
                if value['run_id'] != first_run and value['phase'] == 'running':
                    break
                time.sleep(.2)
            else:
                pytest.fail('monitor did not restart with existing health file')
            new_secret = setup.read_json(root / 'health.json')['secret']
            assert new_secret != health_secret
            setup.require_private(root / 'health.json', inherited=True)
            assert monitor.healthy(second_port, value['server_pid'], new_secret)
            stopped = subprocess.run(command + ['stop', '--state-dir', str(state)], capture_output=True, timeout=10)
            assert stopped.returncode == 0 and json.loads(stopped.stdout)['stop_requested']
            assert child.wait(10) == 0 and child.wait_empty(3)
        finally:
            child.stop()
    assert snapshot(state) == before
    assert git(pilot['remote'], 'show-ref') == refs
    assert (pilot['source'] / '.git/index').read_bytes() == index
    assert not pilot['marker'].exists()
