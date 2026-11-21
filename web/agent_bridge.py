"""Relay one locally owned ACP process over an authenticated loopback socket."""
import json
import os
import re
import socket
import subprocess
import sys
import threading

MANUAL_PERMISSION_CONFIG = {'permissions': [{'action': '*', 'resource': '*', 'effect': 'ask'}]}
OPENCODE_CONSOLE_CONFIG = {'model': 'opencode/big-pickle',
                           'permissions': [{'action': '*', 'resource': '*', 'effect': 'allow'}]}


def automatic_permission_reply(message):
    """Resolve OpenCode consent per the user's console policy, without persistence."""
    if not isinstance(message, dict) or message.get('method') != 'session/request_permission' or 'id' not in message:
        return None
    params = message.get('params')
    options = params.get('options') if isinstance(params, dict) else None
    outcome = {'outcome': 'cancelled'}
    if isinstance(options, list) and len(options) <= 16:
        for option in options:
            if (isinstance(option, dict) and option.get('kind') == 'allow_once' and
                    isinstance(option.get('optionId'), str) and 0 < len(option['optionId']) <= 100):
                outcome = {'outcome': 'selected', 'optionId': option['optionId']}
                break
    return {'jsonrpc':'2.0','id':message['id'],'result':{'outcome':outcome}}


def agent_command(executable):
    if os.path.basename(executable).lower() == 'hermes.exe':
        python = os.path.join(os.path.dirname(executable), 'python.exe')
        wrapper = os.path.join(os.path.dirname(__file__), 'hermes_compact_acp.py')
        if os.path.isfile(python):
            return [python, '-B', wrapper]
        # Newer Hermes delegates execution to a separate gateway. The old
        # process-local safety guards cannot control that gateway.
        raise RuntimeError('hermes_gateway_unsupported')
    return [executable, 'acp']


def main():
    # Do not forward the direct-review credential to native agents.
    os.environ.pop('COORDINATION_OPENROUTER_API_KEY', None)
    port, token, executable = sys.argv[1:]
    sock = socket.create_connection(('127.0.0.1', int(port)), timeout=10)
    sock.sendall((token + '\n').encode('ascii'))
    # The parent owns the Job: the ACP child and all descendants stay inside it.
    environment = os.environ.copy()
    automatic = os.path.basename(executable).lower() == 'opencode-cli.exe'
    if automatic:
        # User-authorized direct execution, scoped to this new process. It does
        # not install an OS sandbox or modify native global permission settings.
        environment['OPENCODE_CONFIG_CONTENT'] = json.dumps(OPENCODE_CONSOLE_CONFIG)
    environment['HERMES_YOLO_MODE'] = '0'
    try:
        command = agent_command(executable)
    except RuntimeError as exc:
        if str(exc) != 'hermes_gateway_unsupported': raise
        try:
            # Consume the pending initialization before closing, so Windows
            # does not reset the connection and discard the diagnostic.
            if sock.recv(32768):
                sock.sendall((json.dumps({'jsonrpc':'2.0', 'method':'_bridge/diagnostic',
                                         'params':{'category':'hermes_gateway_unsupported'}}) + '\n').encode())
        finally:
            sock.close()
        return 1
    child = subprocess.Popen(command, stdin=subprocess.PIPE, env=environment,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             creationflags=0x08000000 if os.name == 'nt' else 0)
    sock.settimeout(None)
    sending = threading.Lock()
    child_sending = threading.Lock()
    def send(chunk):
        with sending: sock.sendall(chunk)
    def diagnostics():
        # Only publish known categories, never raw native logs, paths or tokens.
        tail = ''; seen = set()
        try:
            while True:
                chunk = os.read(child.stderr.fileno(), 2048)
                if not chunk: break
                tail = (tail + chunk.decode('utf-8', 'replace'))[-8192:]
                if 'CONSOLE_COMPACT_PROFILE_UNAVAILABLE' in tail and 'compact_profile' not in seen:
                    seen.add('compact_profile')
                    event = {'jsonrpc': '2.0', 'method': '_bridge/diagnostic',
                             'params': {'category': 'compact_profile_unavailable'}}
                    send((json.dumps(event) + '\n').encode())
                modules = re.findall(r"No module named ['\"]([A-Za-z0-9_.-]{1,80})['\"]", tail)
                for module in modules:
                    if module in seen: continue
                    seen.add(module)
                    event = {'jsonrpc': '2.0', 'method': '_bridge/diagnostic',
                             'params': {'category': 'missing_module', 'module': module}}
                    send((json.dumps(event) + '\n').encode())
        except (OSError, ValueError):
            pass
    def incoming():
        try:
            while True:
                chunk = sock.recv(8192)
                if not chunk:
                    break
                with child_sending:
                    child.stdin.write(chunk); child.stdin.flush()
        except (OSError, ValueError):
            pass
        finally:
            try:
                with child_sending: child.stdin.close()
            except OSError: pass
    thread = threading.Thread(target=incoming, daemon=True); thread.start()
    diagnostic_thread = threading.Thread(target=diagnostics, daemon=True); diagnostic_thread.start()
    try:
        while True:
            # Keep complete JSON-RPC lines atomic when stderr reports a diagnostic.
            chunk = child.stdout.readline(262145)
            if not chunk:
                break
            if automatic and len(chunk) <= 262144 and chunk.endswith(b'\n'):
                try: reply = automatic_permission_reply(json.loads(chunk))
                except ValueError: reply = None
                if reply is not None:
                    with child_sending:
                        child.stdin.write((json.dumps(reply) + '\n').encode()); child.stdin.flush()
                    continue
            send(chunk)
            if len(chunk) > 262144 or not chunk.endswith(b'\n'):
                break
    except (OSError, ValueError):
        pass
    finally:
        diagnostic_thread.join(timeout=1)
        sock.close()
    return child.wait()


if __name__ == '__main__':
    raise SystemExit(main())
