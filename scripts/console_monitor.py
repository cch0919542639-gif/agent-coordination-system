"""Manual foreground read-only console: start, status, stop (Windows/Python3.12+)."""
import argparse
from contextlib import contextmanager
import hashlib
import hmac
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from console_setup import canonical, load, private_directory, read_json, require_private
from coordination_runtime.state_controller import StateError
from web.api import handoff_service
from worker_process_guard import GuardError, JobProcess

ROOT = Path(__file__).resolve().parents[1]


def checked_file(root, name):
    path = root / name
    if path != path.resolve() or (path.exists() and not path.is_file()):
        raise StateError('Session file alias refused.')
    return path


def session_root(state_dir, create=False):
    state = canonical(state_dir)
    root = state.with_name(state.name + '.monitor')
    if root != root.resolve():
        raise StateError('Session directory alias refused.')
    if create and not root.exists():
        root.mkdir()
        private_directory(root)
    require_private(root)
    return root


@contextmanager
def owner_lock(root):
    # ponytail: one Windows file lock per console setup; no persistent service registry.
    import msvcrt
    with checked_file(root, 'owner.lock').open('a+b') as stream:
        if not stream.tell():
            stream.write(b'0'); stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise StateError('Monitor already running for this console.') from None
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def write(root, name, data):
    target = checked_file(root, name)
    temporary = root / (name + '.' + secrets.token_hex(8) + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            if os.name != 'nt':
                temporary.chmod(0o600)
            json.dump(data, stream, sort_keys=True)
        # Windows readers briefly deny delete-sharing. Preserve atomic visibility
        # and retry for under one second; permanent permission errors still fail.
        for attempt in range(20):
            try:
                temporary.replace(target)
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(.05)
    finally:
        temporary.unlink(missing_ok=True)


def status(root):
    value = read_json(checked_file(root, 'session.json'))
    try:
        with owner_lock(root):
            value['running'] = False
            if value['phase'] not in ('stopped', 'failed', 'cleanup_unconfirmed'):
                value['phase'] = 'interrupted'
    except StateError:
        value['running'] = True
    return value


def request_stop(root):
    value = status(root)
    if value['running']:
        write(root, 'stop.json', dict(run_id=value['run_id']))
    # This is acknowledgement of a request, never proof of process cleanup.
    return dict(stop_requested=value['running'], run_id=value['run_id'])


def launch(arguments):
    child = JobProcess([sys.executable, '-B', *arguments], cwd=ROOT)
    try:
        child.resume()
        return child
    except BaseException:
        child.close()
        raise


def release(child):
    if child is not None:
        try:
            child.stop()
        finally:
            child.close()


def exited(child):
    try:
        return child.wait(0)
    except subprocess.TimeoutExpired:
        return None


def healthy(port, pid, secret):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=1)
    try:
        nonce = secrets.token_hex(16)
        connection.request('GET', '/api/monitor-health?nonce=' + nonce)
        response = connection.getresponse()
        raw = response.read(1025)
        if response.status != 200 or len(raw) > 1024:
            return False
        result = json.loads(raw)
        expected = hmac.new(bytes.fromhex(secret), (nonce + ':' + str(pid)).encode('ascii'), hashlib.sha256).hexdigest()
        return (isinstance(result, dict) and type(result.get('pid')) is int and result['pid'] == pid
                and result.get('read_only') is True and isinstance(result.get('proof'), str)
                and hmac.compare_digest(result['proof'], expected))
    except (OSError, http.client.HTTPException, ValueError, TypeError, UnicodeError):
        return False
    finally:
        connection.close()


def supervise(root, server_args, sync_args, port, interval=60, sync_timeout=150):
    """Restart owned children only. No dispatch/receive/runner path exists here."""
    server = sync = None
    run_id = secrets.token_hex(16)
    value = dict(run_id=run_id, running=True, phase='starting', read_only=True,
                 origin='http://127.0.0.1:' + str(port), server_pid=None,
                 server_restarts=0, sync_attempts=0, last_sync_exit=None,
                 last_sync_ms=None, sync_error=None, failure=None)
    secret = secrets.token_hex(32)
    next_server = next_sync = next_health = 0
    sync_started = 0
    failures = 0
    delay = 5
    try:
        try:
            write(root, 'health.json', {'secret': secret})
        except OSError:
            value['failure'] = 'HEALTH_SETUP_FAILED'
            raise
        while True:
            stop = checked_file(root, 'stop.json')
            if stop.exists() and read_json(stop).get('run_id') == run_id:
                break
            now = time.monotonic()
            if server is not None:
                code = exited(server)
                if now >= next_health:
                    failures = 0 if healthy(port, server.pid, secret) else failures + 1
                    if failures == 0:
                        value['phase'] = 'running'
                        delay = 5
                    next_health = now + 10
                if code is not None or failures >= 3:
                    release(server); server = None
                    value.update(phase='retrying', server_pid=None)
                    value['server_restarts'] += 1
                    next_server = now + delay
                    delay = min(delay * 2, 60)
            if server is None and now >= next_server:
                try:
                    server = launch(server_args)
                except (OSError, GuardError):
                    value['failure'] = 'SERVER_LAUNCH_FAILED'
                    raise
                value.update(phase='starting', server_pid=server.pid)
                failures = 0
                next_health = now + 2
            if sync is not None:
                code = exited(sync)
                if code is not None or now - sync_started >= sync_timeout:
                    release(sync); sync = None
                    value.update(last_sync_exit=code, sync_error=None if code == 0 else
                                 'SYNC_TIMEOUT' if code is None else 'SYNC_FAILED')
                    if code == 0:
                        value['last_sync_ms'] = time.time_ns() // 1_000_000
                    next_sync = time.monotonic() + interval
            if sync is None and now >= next_sync:
                try:
                    sync = launch(sync_args)
                except (OSError, GuardError):
                    value['failure'] = 'SYNC_LAUNCH_FAILED'
                    raise
                sync_started = now
                value['sync_attempts'] += 1
            value['sampled_ms'] = time.time_ns() // 1_000_000
            write(root, 'session.json', value)
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    except BaseException:
        value['failure'] = value['failure'] or 'SUPERVISOR_FAILED'
        raise
    finally:
        value['phase'] = 'stopping'
        cleanup_error = None
        for child in (sync, server):
            try:
                release(child)
            except GuardError as error:
                cleanup_error = error
        value.update(running=False, phase='cleanup_unconfirmed' if cleanup_error else
                     'failed' if value['failure'] else 'stopped', server_pid=None)
        write(root, 'session.json', value)
        if cleanup_error:
            raise cleanup_error
    return value


def start(state_dir, handoff_config, port=8766, interval=60):
    if not 1024 <= port <= 65535 or not 60 <= interval <= 3600:
        raise StateError('Port1024..65535 and sync interval60..3600 required.')
    app = load(state_dir)
    service = handoff_service(handoff_config, app.p)
    if service is None or not service.summary()['initialized']:
        raise StateError('An explicitly initialized handoff store is required.')
    root = session_root(state_dir, create=True)
    with owner_lock(root):
        # Refuse to take over any existing listener, including another console.
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', port))
        server = [str(ROOT / 'scripts/console_setup.py'), 'serve', '--state-dir', str(canonical(state_dir)),
                  '--handoff-config', str(canonical(handoff_config)), '--port', str(port),
                  '--read-only', '--duration', '0', '--monitor-health-file', str(root / 'health.json')]
        sync = [str(ROOT / 'scripts/github_handoff.py'), '--config', str(canonical(handoff_config)), 'sync']
        print(json.dumps(dict(origin='http://127.0.0.1:' + str(port), read_only=True,
                              stop='Ctrl+C or console_monitor.py stop --state-dir SAME_PATH')), flush=True)
        return supervise(root, server, sync, port, interval)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('start', 'status', 'stop'):
        command = commands.add_parser(name)
        command.add_argument('--state-dir', required=True)
        if name == 'start':
            command.add_argument('--handoff-config', required=True)
            command.add_argument('--port', type=int, default=8766)
            command.add_argument('--interval', type=int, default=60)
    args = vars(parser.parse_args(argv)); command = args.pop('command')
    try:
        if os.name != 'nt':
            raise StateError('Windows owned-process support required.')
        if command == 'start':
            result = start(**args)
        else:
            root = session_root(args['state_dir'])
            result = request_stop(root) if command == 'stop' else status(root)
        print(json.dumps(result, sort_keys=True), flush=True)
        return 0
    except (StateError, GuardError, OSError, ValueError, KeyError, TypeError):
        print('Monitor refused; check private setup, handoff binding, session status and port.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
