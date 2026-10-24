"""New private setup only: replay/refusal and real finite foreground HTTP."""
import http.client
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import console_setup as setup
from coordination_runtime.state_controller import StateError


@pytest.mark.parametrize('payload,default_encoding', [
    ('"example\\測試使用者","S-1-5-21-100-200-300-1001"\r\n'.encode('utf-8'), 'cp950'),
    ('"example\\測試使用者","S-1-5-21-100-200-300-1001"\r\n'.encode('cp950'), 'utf-8'),
    (b'"example\\\xff","S-1-5-21-100-200-300-1001"\r\n', 'ascii'),
    ('"example\\測試, ""user""","S-1-5-21-100-200-300-1001"\r\n'.encode('utf-8'), 'cp950'),
], ids=['utf8-under-cp950', 'cp950-under-utf8', 'raw-nontext', 'quoted-comma'])
def test_current_sid_never_decodes_non_ascii_account_output(monkeypatch, payload, default_encoding):
    def run(command, **kwargs):
        assert command == ['whoami', '/user', '/fo', 'csv', '/nh']
        assert kwargs['capture_output'] and kwargs['check'] and kwargs['timeout'] == 10
        raw = payload.decode(default_encoding) if kwargs.get('text') else payload
        return SimpleNamespace(stdout=raw, returncode=0)
    monkeypatch.setattr(setup.subprocess, 'run', run)
    assert setup.current_sid() == 'S-1-5-21-100-200-300-1001'


@pytest.mark.parametrize('payload', [None, b'', b'"user"\r\n',
    b'"user","S-1-5-"\r\n', b'"user","S-1-5-21"\r\n"other","S-1-5-22"\r\n',
    b'"user","S-1-5-21"junk', b'"user","S-1-5-21\xff"\r\n', b'x' * 16385],
    ids=['none', 'empty', 'missing-sid', 'invalid-sid', 'multiple-records', 'suffix', 'nonascii-sid', 'oversized'])
def test_current_sid_refuses_missing_or_malformed_output(monkeypatch, payload):
    def run(command, **kwargs):
        output = payload.decode('ascii') if isinstance(payload, bytes) and kwargs.get('text') else payload
        return SimpleNamespace(stdout=output, returncode=0)
    monkeypatch.setattr(setup.subprocess, 'run', run)
    with pytest.raises(StateError, match='identity unavailable'):
        setup.current_sid()


@pytest.mark.parametrize('failure', [subprocess.CalledProcessError(1, ['whoami']),
                                    subprocess.TimeoutExpired(['whoami'], 10), OSError('synthetic refusal')])
def test_current_sid_command_failure_is_fail_closed(monkeypatch, failure):
    def run(*args, **kwargs):
        raise failure
    monkeypatch.setattr(setup.subprocess, 'run', run)
    with pytest.raises(StateError, match='identity unavailable'):
        setup.current_sid()


def test_current_sid_isolated_child_ignores_utf8_environment(tmp_path):
    code = '''import sys
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1])
import console_setup as setup
payload='"example\\\\測試使用者","S-1-5-21-100-200-300-1001"\\r\\n'.encode('utf-8')
def run(*args,**kwargs):
    if kwargs.get('text'):
        try: return SimpleNamespace(stdout=payload.decode('cp950'))
        except UnicodeDecodeError: return SimpleNamespace(stdout=None)
    return SimpleNamespace(stdout=payload)
setup.subprocess.run=run
assert sys.flags.isolated and sys.flags.utf8_mode==0
assert setup.current_sid()=='S-1-5-21-100-200-300-1001'
print('isolated SID extraction passed')
'''
    result = subprocess.run([sys.executable, '-I', '-X', 'utf8=0', '-B', '-c', code, str(ROOT / 'scripts')],
                            cwd=tmp_path, capture_output=True, text=True, timeout=20,
                            env=dict(os.environ, PYTHONUTF8='1'))
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'isolated SID extraction passed'


@pytest.fixture
def config(tmp_path):
    repo = tmp_path / 'repo'; (repo / '.git').mkdir(parents=True)
    for state in ('ready', 'in_progress', 'review', 'blocked', 'done', 'cancelled'):
        (repo / 'coordination/task-board' / state).mkdir(parents=True)
    return setup.settings(str(repo), str(tmp_path / 'workspaces'), 'test-project', str(tmp_path / 'private'))


def snapshot(root):
    # Do not expose private login contents in pytest assertion diagnostics.
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(root).iterdir()}


def test_initialization_replay_preserves_every_byte_and_disabled_binding(config):
    assert setup.initialize(config)
    root = Path(config['state_dir']); before = snapshot(root)
    assert not setup.initialize(config)
    assert snapshot(root) == before
    app = setup.load(root)
    with app.p.controller._db() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 4
        assert db.execute('SELECT mode FROM parallel_projects').fetchone()[0] == 'disabled'
        assert db.execute('SELECT count(*) FROM runs').fetchone()[0] == 0
    assert not app.p.marker.exists()
    setup.require_private(root)
    assert app.users['viewer']['role'] == 'viewer'


@pytest.mark.parametrize('field,value', [('project_id', 'another-project'), ('username', 'another-user'), ('role', 'administrator')])
def test_replay_configuration_mismatch_refuses_before_mutation(config, field, value):
    setup.initialize(config); before = snapshot(config['state_dir'])
    with pytest.raises(StateError):
        setup.initialize(config | {field: value})
    assert snapshot(config['state_dir']) == before


def test_copied_private_root_refuses_stored_path_mismatch(config):
    setup.initialize(config)
    root = Path(config['state_dir']); moved = root.with_name('copied-private')
    moved.mkdir(); setup.private_directory(moved)
    for path in root.iterdir():
        shutil.copyfile(path, moved / path.name)
        if os.name != 'nt': (moved / path.name).chmod(0o600)
    before = snapshot(moved)
    with pytest.raises(StateError, match='configuration differs'):
        setup.load(moved)
    assert snapshot(moved) == snapshot(root) == before
    setup.load(root)


@pytest.mark.parametrize('kind', ['foreign', 'schema', 'root', 'workspace', 'mode', 'auth', 'login'])
def test_conflicting_schema_binding_or_login_refuses_without_writes(config, kind):
    setup.initialize(config); root = Path(config['state_dir'])
    if kind in {'foreign', 'schema', 'root', 'workspace', 'mode'}:
        if kind == 'foreign':
            (root / 'runtime.db').unlink()
        with sqlite3.connect(root / 'runtime.db') as db:
            if kind == 'foreign': db.execute('CREATE TABLE foreign_data(value)')
            elif kind == 'schema': db.execute('PRAGMA user_version=1')
            elif kind == 'root': db.execute("UPDATE project_bindings SET root_digest='wrong'")
            elif kind == 'workspace': db.execute("UPDATE parallel_projects SET workspace_root_digest='wrong'")
            else: db.execute("UPDATE parallel_projects SET mode='parallel'")
    elif kind == 'auth':
        (root / 'auth.json').write_text('{}')
    else:
        (root / 'login.txt').write_text('conflicting login')
    before = snapshot(root)
    with pytest.raises((StateError, ValueError)):
        setup.load(root)
    assert snapshot(root) == before


@pytest.mark.parametrize('target', ['inside_repo', 'inside_workspaces', 'ancestor', 'relative', 'dotdot'])
def test_path_refusal_is_side_effect_free(config, target):
    repo = Path(config['repo']); private = Path(config['state_dir'])
    paths = dict(inside_repo=repo / 'private', inside_workspaces=Path(config['workspaces']) / 'private',
                 ancestor=repo.parent, relative=Path('relative-state'), dotdot=private / '..' / 'another-state')
    with pytest.raises(StateError):
        setup.settings(config['repo'], config['workspaces'], config['project_id'], str(paths[target]))
    assert not private.exists()


def test_missing_incomplete_and_interrupted_setup_never_auto_repairs(config, monkeypatch):
    root = Path(config['state_dir'])
    with pytest.raises(StateError): setup.load(root)
    assert not root.exists()
    root.mkdir(); (root / 'runtime.db').write_bytes(b'foreign')
    before = snapshot(root)
    with pytest.raises(StateError): setup.initialize(config)
    assert snapshot(root) == before
    root = root.with_name('new-private'); config = config | dict(state_dir=str(root))
    monkeypatch.setattr(setup, 'write_new', lambda *args: (_ for _ in ()).throw(OSError('synthetic interruption')))
    with pytest.raises(OSError): setup.initialize(config)
    assert not root.exists()
    staging = list(root.parent.glob('new-private.pending-*'))
    assert len(staging) == 1
    setup.require_private(staging[0])


def test_permission_failure_stops_before_credentials(config, monkeypatch):
    monkeypatch.setattr(setup, 'private_directory', lambda *args: (_ for _ in ()).throw(StateError('synthetic ACL failure')))
    with pytest.raises(StateError): setup.initialize(config)
    assert not Path(config['state_dir']).exists()
    assert not list(Path(config['state_dir']).parent.glob('*.pending-*/login.txt'))


def test_broadened_login_file_permissions_refuse_without_mutation(config):
    setup.initialize(config); path = Path(config['state_dir']) / 'login.txt'
    if os.name == 'nt':
        result = subprocess.run(['icacls', str(path), '/grant', '*S-1-1-0:R'], capture_output=True, timeout=10)
        assert result.returncode == 0
    else:
        path.chmod(0o644)
    before = snapshot(config['state_dir'])
    with pytest.raises(StateError, match='permissions'):
        setup.load(config['state_dir'])
    assert snapshot(config['state_dir']) == before


def test_no_query_or_invalid_serve_creates_a_database(config):
    with pytest.raises(StateError): setup.serve(config['state_dir'], duration=9)
    with pytest.raises(StateError): setup.serve(config['state_dir'], duration=1801)
    with pytest.raises(StateError): setup.serve(config['state_dir'], port=0)
    assert not Path(config['state_dir']).exists()


def test_busy_port_refuses_and_preserves_private_files(config):
    setup.initialize(config); before = snapshot(config['state_dir'])
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0)); listener.listen()
        with pytest.raises(StateError, match='Port unavailable'):
            setup.serve(config['state_dir'], port=listener.getsockname()[1], duration=10)
    assert snapshot(config['state_dir']) == before


def request(port, path, body=None, session=None):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    headers = {'Origin': 'http://127.0.0.1:' + str(port)}
    if body is not None: headers['Content-Type'] = 'application/json'
    if session: headers.update(Cookie=session[0], **{'X-CSRF-Token': session[1]})
    connection.request('POST' if body is not None else 'GET', path,
                       json.dumps(body) if body is not None else None, headers)
    response = connection.getresponse(); raw = response.read()
    result = response.status, json.loads(raw), response.getheader('Set-Cookie')
    connection.close()
    return result


def test_cli_new_directory_login_seven_views_viewer_refusal_and_finite_exit(config, tmp_path):
    command = [sys.executable, '-I', '-B', str(ROOT / 'scripts/console_setup.py')]
    result = subprocess.run(command + ['init', '--repo', config['repo'], '--workspaces', config['workspaces'],
        '--project-id', config['project_id'], '--state-dir', config['state_dir']],
        cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    root = Path(config['state_dir']); before = snapshot(root)
    token = (root / 'login.txt').read_text().split('Token: ')[1].strip()
    assert token not in result.stdout + result.stderr
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
    process = subprocess.Popen(command + ['serve', '--state-dir', str(root), '--port', str(port), '--duration', '10'],
                               cwd=tmp_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        # Bounded process lifetime also bounds a startup failure; no secret output is expected.
        startup = process.stdout.readline()
        metadata = json.loads(startup)
        assert metadata['pid'] == process.pid and metadata['duration'] == 10
        status, data, cookie = request(port, '/api/login', dict(username='viewer', token=token))
        assert status == 200
        session = (cookie.split(';')[0], data['csrf'])
        for view in ('overview', 'board', 'monitor', 'workspaces', 'reviews', 'events', 'settings'):
            status, data, _ = request(port, '/api/view?name=' + view, session=session)
            assert status == 200 and data['runtime_available']
        assert request(port, '/api/preview', dict(action='parallel.disable', args={}), session)[0] == 403
        stdout, stderr = process.communicate(timeout=20)
        assert process.returncode == 0 and token not in startup + stdout + stderr
    finally:
        if process.poll() is None:
            process.terminate(); process.communicate(timeout=5)
    assert snapshot(root) == before
