"""Explicit local console initialization and finite foreground serving (Python 3.12+)."""
import argparse
import csv
import ctypes
import hashlib
import json
import os
import re
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from coordination_runtime.parallel_runtime import ParallelController
from coordination_runtime.state_controller import StateController, StateError, _id
from coordination_runtime.workspace import path_digest
from web.api import Console, Server, ROLES, TOKEN

FILES = {'config.json', 'auth.json', 'runtime.db', 'login.txt'}


def current_sid():
    result = subprocess.run(['whoami', '/user', '/fo', 'csv', '/nh'],
                            capture_output=True, text=True, check=True, timeout=10)
    sid = next(csv.reader([result.stdout.strip()]))[1]
    if not re.fullmatch(r'S-1-[0-9-]+', sid):
        raise StateError('Windows user identity unavailable.')
    return sid


def require_private(path, inherited=False):
    if os.name != 'nt':
        if path.stat().st_mode & 0o077:
            raise StateError('Private directory permissions required.')
        return
    # Read the protected DACL without changing existing permissions on replay.
    from ctypes import wintypes as w
    api = ctypes.WinDLL('advapi32', use_last_error=True)
    get = api.GetFileSecurityW
    get.argtypes = [w.LPCWSTR, w.DWORD, ctypes.c_void_p, w.DWORD, ctypes.POINTER(w.DWORD)]
    get.restype = w.BOOL
    size = w.DWORD()
    get(str(path), 4, None, 0, ctypes.byref(size))
    if not size.value:
        raise StateError('Windows private permissions unavailable.')
    data = ctypes.create_string_buffer(size.value)
    if not get(str(path), 4, data, size.value, ctypes.byref(size)):
        raise StateError('Windows private permissions unavailable.')
    convert = api.ConvertSecurityDescriptorToStringSecurityDescriptorW
    convert.argtypes = [ctypes.c_void_p, w.DWORD, w.DWORD, ctypes.POINTER(w.LPWSTR), ctypes.POINTER(w.DWORD)]
    convert.restype = w.BOOL
    output = w.LPWSTR()
    if not convert(data, 1, 4, ctypes.byref(output), None):
        raise StateError('Windows private permissions unavailable.')
    try:
        sddl = output.value
    finally:
        free = ctypes.WinDLL('kernel32').LocalFree
        free.argtypes = [ctypes.c_void_p]; free.restype = ctypes.c_void_p
        free(ctypes.cast(output, ctypes.c_void_p))
    protection = 'P?' if inherited else 'P'
    if not re.fullmatch(r'D:' + protection + r'(?:AI|AR)*\(A;[A-Z]*;FA;;;' + re.escape(current_sid()) + r'\)', sddl):
        raise StateError('Current-user-only protected directory permissions required.')


def canonical(value):
    path = Path(value)
    if not path.is_absolute() or path != path.resolve():
        raise StateError('Use an absolute canonical path without aliases.')
    return path


def settings(repo, workspaces, project_id, state_dir, username='viewer', role='viewer'):
    repo, workspaces, state_dir = map(canonical, (repo, workspaces, state_dir))
    _id(project_id); _id(username)
    if role not in ROLES:
        raise StateError('Choose an explicit supported role.')
    if not (repo / '.git').exists() or not (repo / 'coordination/task-board').is_dir():
        raise StateError('Repository must contain Git metadata and the task board.')
    roots = [repo, workspaces, state_dir]
    if any(a.is_relative_to(b) or b.is_relative_to(a) for i, a in enumerate(roots) for b in roots[i + 1:]):
        raise StateError('Repository, workspace and private state roots must be separate.')
    if not state_dir.parent.is_dir():
        raise StateError('Create the private state parent directory first.')
    if workspaces.exists() and not workspaces.is_dir():
        raise StateError('Workspace root must be a directory.')
    marker = repo / 'coordination/monitor/runtime/coordination-v2/parallel-mode.json'
    if marker.exists() or marker.is_symlink():
        raise StateError('An active or unknown mode marker requires separate recovery.')
    return dict(schema_version=1, repo=str(repo), workspaces=str(workspaces),
                project_id=project_id, state_dir=str(state_dir), username=username, role=role)


def private_directory(path):
    """Restrict a newly created directory before any credentials are written."""
    if os.name == 'nt':
        sid = current_sid()
        # Python's private mkdtemp may add explicit system/admin ACEs. On this
        # new empty staging directory only, reset then remove inherited ACEs.
        subprocess.run(['icacls', str(path), '/reset'], capture_output=True, check=True, timeout=10)
        subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r', '*' + sid + ':(OI)(CI)F'],
                       capture_output=True, check=True, timeout=10)
    else:
        path.chmod(0o700)
    require_private(path)


def write_new(path, value):
    raw = (json.dumps(value, sort_keys=True) + '\n').encode() if isinstance(value, dict) else value.encode()
    with path.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    if os.name != 'nt':
        path.chmod(0o600)


def read_json(path):
    with path.open('rb') as stream:
        raw = stream.read(16385)
    if len(raw) > 16384:
        raise StateError('Configuration exceeds bound.')
    return json.loads(raw)


def load(state_dir, expected=None):
    root = canonical(state_dir)
    if not root.is_dir() or {p.name for p in root.iterdir()} != FILES:
        raise StateError('Incomplete initialization; preserve it and choose a new private state directory.')
    require_private(root)
    for name in FILES:
        path = root / name
        if path != path.resolve() or not path.is_file():
            raise StateError('Private state file alias refused.')
        require_private(path, inherited=True)
    config = read_json(root / 'config.json')
    if not isinstance(config, dict) or set(config) != {'schema_version', 'repo', 'workspaces', 'project_id', 'state_dir', 'username', 'role'}:
        raise StateError('Configuration shape invalid.')
    rebuilt = settings(**{k: config[k] for k in config if k != 'schema_version'})
    if type(config['schema_version']) is not int or config != rebuilt or (expected is not None and config != expected):
        raise StateError('Existing configuration differs; no files were changed.')
    p = ParallelController(StateController(root / 'runtime.db'), config['repo'], config['workspaces'], config['project_id'])
    with p.controller._db() as db:
        bindings = [tuple(row) for row in db.execute('SELECT project_id,root_digest FROM project_bindings')]
        parallel = [tuple(row) for row in db.execute('SELECT project_id,root_digest,workspace_root_digest,mode,capacity FROM parallel_projects')]
        if bindings != [(p.project_id, p.board.root_digest)] or parallel != [(
                p.project_id, p.board.root_digest, path_digest(p.workspace.root), 'disabled', 2)]:
            raise StateError('Database binding or mode differs; no files were changed.')
    app = Console(p, root / 'auth.json')
    if len(app.users) != 1 or config['username'] not in app.users or app.users[config['username']]['role'] != config['role']:
        raise StateError('Existing account differs; no files were changed.')
    with (root / 'login.txt').open('rb') as stream:
        raw = stream.read(513)
    if len(raw) > 512:
        raise StateError('Private login file exceeds bound.')
    login = raw.decode('utf-8')
    prefix = 'Username: ' + config['username'] + '\nToken: '
    token = login.removeprefix(prefix).removesuffix('\n')
    if not login.startswith(prefix) or not TOKEN.fullmatch(token) or hashlib.sha256(token.encode()).hexdigest() != app.users[config['username']]['token_sha256']:
        raise StateError('Private login file conflicts with account; no files were changed.')
    return app


def initialize(config):
    root = Path(config['state_dir'])
    # A complete existing setup is checked read-only: no DB initialization on replay.
    if root.exists():
        load(root, config)
        return False
    staging = Path(tempfile.mkdtemp(prefix=root.name + '.pending-', dir=root.parent))
    private_directory(staging)
    controller = StateController(staging / 'runtime.db')
    controller.initialize()
    p = ParallelController(controller, config['repo'], config['workspaces'], config['project_id'])
    with controller._db(write=True) as db:
        db.execute('INSERT INTO project_bindings VALUES(?,?)', (p.project_id, p.board.root_digest))
        db.execute('INSERT INTO parallel_projects VALUES(?,?,?,?,?)',
                   (p.project_id, p.board.root_digest, path_digest(p.workspace.root), 'disabled', 2))
    token = secrets.token_urlsafe(32)
    write_new(staging / 'auth.json', dict(schema_version=1, users=[dict(username=config['username'],
              role=config['role'], token_sha256=hashlib.sha256(token.encode()).hexdigest())]))
    write_new(staging / 'login.txt', 'Username: ' + config['username'] + '\nToken: ' + token + '\n')
    write_new(staging / 'config.json', config)
    if os.name != 'nt':
        (staging / 'runtime.db').chmod(0o600)
    for name in FILES:
        require_private(staging / name, inherited=True)
    # Never replace an existing setup. Failed/interrupted private staging remains for inspection.
    if root.exists():
        raise StateError('Initialization target appeared concurrently; private staging preserved.')
    staging.rename(root)
    return True


def serve(state_dir, port=8766, duration=300):
    if type(port) is not int or not 1024 <= port <= 65535 or type(duration) is not int or not 10 <= duration <= 1800:
        raise StateError('Port must be1024..65535 and duration10..1800 seconds.')
    app = load(state_dir)
    try:
        server = Server(app, port)
    except OSError:
        raise StateError('Port unavailable; choose another port or stop its owner explicitly.') from None
    timer = threading.Timer(duration, server.shutdown); timer.daemon = True
    try:
        timer.start()
        print(json.dumps(dict(origin=server.origin, pid=os.getpid(), duration=duration,
                              stop='Ctrl+C in this terminal, or wait for expiry')), flush=True)
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        timer.cancel(); server.server_close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    for name in ('repo', 'workspaces', 'project-id', 'state-dir'):
        init.add_argument('--' + name, required=True)
    init.add_argument('--username', default='viewer')
    init.add_argument('--role', choices=sorted(ROLES), default='viewer')
    run = sub.add_parser('serve')
    run.add_argument('--state-dir', required=True)
    run.add_argument('--port', type=int, default=8766)
    run.add_argument('--duration', type=int, default=300)
    args = vars(parser.parse_args(argv)); command = args.pop('command')
    try:
        if command == 'init':
            config = settings(**args)
            created = initialize(config)
            print(json.dumps(dict(created=created, login_file=str(Path(config['state_dir']) / 'login.txt'),
                                  mode='disabled', role=config['role'])), flush=True)
        else:
            serve(**args)
        return 0
    except StateError as error:
        print('Console setup refused: ' + str(error), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print('Console setup refused: check canonical paths, private permissions, configuration/schema/binding, or occupied port. Existing files preserved.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
