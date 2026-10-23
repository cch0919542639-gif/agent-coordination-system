"""Explicit, finite, authenticated loopback server; no initialization or providers."""
import argparse
from collections import deque
import hashlib
import hmac
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import threading
import time
from urllib.parse import parse_qs, urlsplit

from coordination_runtime.parallel_runtime import ParallelController
from coordination_runtime.recovery_manager import RecoveryManager
from coordination_runtime.resource_guard import ResourceController
from coordination_runtime.state_controller import StateController, StateError, _id, _integer
from .read_model import ReadModel

VIEWS = {'overview', 'board', 'monitor', 'workspaces', 'reviews', 'events', 'settings'}
ROLES = {'viewer': 0, 'operator': 1, 'administrator': 2}
TOKEN = re.compile(r'[A-Za-z0-9_-]{43}')
STATIC = {'/': ('index.html', 'text/html'), '/app.css': ('app.css', 'text/css'),
          '/app.js': ('app.js', 'text/javascript')}


class Refused(Exception):
    def __init__(self, status=400):
        self.status = status


def shape(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise Refused()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Refused()
        result[key] = value
    return result


class Console:
    def __init__(self, parallel, auth_file):
        self.p = parallel
        path = Path(auth_file).absolute()
        if (path.resolve() != path or path.is_relative_to(parallel.root)
                or path.is_relative_to(parallel.workspace.root)):
            raise StateError('External authentication file required.')
        with path.open('rb') as stream:
            raw = stream.read(16385)
        if len(raw) > 16384:
            raise StateError('Authentication configuration exceeds bound.')
        try:
            data = json.loads(raw, object_pairs_hook=unique)
            shape(data, {'schema_version', 'users'})
            if type(data['schema_version']) is not int or data['schema_version'] != 1:
                raise Refused()
            users = data['users']
            if not isinstance(users, list) or not 1 <= len(users) <= 8:
                raise Refused()
            self.users = {}
            for user in users:
                shape(user, {'username', 'role', 'token_sha256'})
                _id(user['username'])
                if (user['username'] in self.users or user['role'] not in ROLES
                        or not isinstance(user['token_sha256'], str)
                        or not re.fullmatch('[a-f0-9]{64}', user['token_sha256'])):
                    raise Refused()
                self.users[user['username']] = user
        except (Refused, ValueError, TypeError, KeyError):
            raise StateError('Authentication configuration invalid.') from None
        self.model = ReadModel(parallel)
        self.sessions = {}
        self.failures = deque(maxlen=5)
        # ponytail: four HTTP handlers share one bounded local-controller lock;
        # per-session locks only if measured operator throughput requires them.
        self.lock = threading.RLock()

    def login(self, body):
        shape(body, {'username', 'token'})
        now = time.monotonic()
        while self.failures and now - self.failures[0] >= 60:
            self.failures.popleft()
        if len(self.failures) >= 5:
            raise Refused(429)
        user = self.users.get(body['username']) if isinstance(body['username'], str) else None
        token = body['token']
        digest = hashlib.sha256(token.encode()).hexdigest() if isinstance(token, str) and TOKEN.fullmatch(token) else ''
        if not hmac.compare_digest(digest, user['token_sha256'] if user else '0' * 64):
            self.failures.append(now)
            raise Refused(401)
        self.sessions = {k: v for k, v in self.sessions.items() if now < v['expires']}
        if len(self.sessions) >= 8:
            raise Refused(429)
        sid = secrets.token_urlsafe(32)
        session = dict(username=user['username'], role=user['role'], csrf=secrets.token_urlsafe(32),
                       expires=now + 900, plans={})
        self.sessions[sid] = session
        return sid, session

    def action(self, action, args, execute=False):
        fields = {'recovery.reconcile': {'run_id', 'request_id', 'expected_version', 'expected_fence', 'reason'},
                  'resource.probe': set(), 'resource.reset': {'expected_sequence'},
                  'board.reconcile': {'request_id'}, 'board.cancel': {'request_id'},
                  'parallel.disable': set()}
        if not isinstance(action, str) or action not in fields:
            raise Refused()
        shape(args, fields[action])
        for key, value in args.items():
            if key.startswith('expected_'):
                _integer(value, 1 if key == 'expected_fence' else 0)
            else:
                _id(value)
        if action == 'recovery.reconcile':
            return RecoveryManager(self.p).reconcile(**args, execute=execute)
        if action == 'resource.probe':
            return ResourceController(self.p).probe(execute=execute)
        if action == 'resource.reset':
            return ResourceController(self.p).reset(**args, execute=execute)
        if action == 'board.reconcile':
            return self.p.board.reconcile(args['request_id'], execute=execute)
        if action == 'board.cancel':
            return self.p.board.cancel(args['request_id'], execute=execute)
        return self.p.disable(execute=execute)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, console, port=0):
        self.app = console
        self.slots = threading.BoundedSemaphore(4)
        super().__init__(('127.0.0.1', port), Handler)
        self.origin = 'http://127.0.0.1:' + str(self.server_port)
        self.cookie = 'coordination_' + str(self.server_port)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(2)
        return connection, address

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()

    def handle_error(self, request, client_address):
        pass  # Never emit paths, request bodies, cookies or tracebacks.


class Handler(BaseHTTPRequestHandler):
    server_version = 'CoordinationConsole'
    sys_version = ''

    def log_message(self, *args):
        pass

    def send_error(self, code, message=None, explain=None):
        self.reply(code, dict(error='Request refused.'))

    def reply(self, code, payload, content_type='application/json', cookie=None):
        raw = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode()
        if len(raw) > 262144:
            code, raw, content_type = 409, b'{"error":"Response exceeds bound."}', 'application/json'
        self.send_response(code)
        for key, value in {'Content-Type': content_type + '; charset=utf-8', 'Content-Length': str(len(raw)),
                'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY',
                'Referrer-Policy': 'no-referrer', 'Content-Security-Policy': "default-src 'self'; script-src 'self'; "
                "style-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; "
                "frame-ancestors 'none'; form-action 'self'", 'Connection': 'close'}.items():
            self.send_header(key, value)
        if cookie is not None:
            self.send_header('Set-Cookie', self.server.cookie + '=' + cookie + '; Path=/; HttpOnly; SameSite=Strict; Max-Age=' + ('900' if cookie else '0'))
        self.end_headers()
        self.wfile.write(raw)
        self.close_connection = True

    def session(self):
        raw = self.headers.get('Cookie', '')
        if len(raw) > 4096:
            raise Refused(401)
        if sum(part.strip().startswith(self.server.cookie + '=') for part in raw.split(';')) != 1:
            raise Refused(401)
        jar = SimpleCookie(); jar.load(raw)
        morsel = jar.get(self.server.cookie)
        sid = morsel.value if morsel else ''
        session = self.server.app.sessions.get(sid)
        if not session or time.monotonic() >= session['expires']:
            self.server.app.sessions.pop(sid, None)
            raise Refused(401)
        if self.command == 'POST' and not hmac.compare_digest(self.headers.get('X-CSRF-Token', ''), session['csrf']):
            raise Refused(403)
        return sid, session

    def dispatch(self):
        if self.client_address[0] != '127.0.0.1':
            raise Refused(403)
        if sum(len(k) + len(v) for k, v in self.headers.items()) > 16384:
            raise Refused(431)
        for key in self.headers:
            if len(self.headers.get_all(key)) != 1:
                raise Refused()
        if self.headers.get('Host') != self.server.origin.removeprefix('http://'):
            raise Refused(403)
        origin = self.headers.get('Origin')
        if origin is not None and origin != self.server.origin:
            raise Refused(403)
        if self.headers.get('Transfer-Encoding') is not None:
            raise Refused()
        parsed = urlsplit(self.path)
        if parsed.scheme or parsed.netloc or parsed.fragment or len(self.path) > 2048:
            raise Refused()
        route = parsed.path
        if self.command == 'GET' and route in STATIC and not parsed.query:
            if self.headers.get('Content-Length') not in (None, '0'):
                raise Refused()
            name, mime = STATIC[route]
            return self.reply(200, (Path(__file__).parent / 'static' / name).read_bytes(), mime)
        body = None
        if self.command == 'POST':
            if origin != self.server.origin or parsed.query:
                raise Refused(403)
            if self.headers.get('Content-Type') != 'application/json':
                raise Refused(415)
            length = self.headers.get('Content-Length', '')
            if not re.fullmatch(r'[0-9]{1,5}', length) or not 0 < int(length) <= 16384:
                raise Refused(413)
            raw = self.rfile.read(int(length))
            if len(raw) != int(length):
                raise Refused()
            body = json.loads(raw, object_pairs_hook=unique,
                              parse_constant=lambda _: (_ for _ in ()).throw(Refused()))
        elif self.headers.get('Content-Length') not in (None, '0'):
            raise Refused()
        app = self.server.app
        with app.lock:
            if route == '/api/login' and self.command == 'POST':
                sid, session = app.login(body)
                return self.reply(200, {k: session[k] for k in ('username', 'role', 'csrf')}, cookie=sid)
            sid, session = self.session()
            if route == '/api/session' and self.command == 'GET' and not parsed.query:
                return self.reply(200, {k: session[k] for k in ('username', 'role', 'csrf')})
            if route == '/api/logout' and self.command == 'POST':
                shape(body, set()); del app.sessions[sid]
                return self.reply(200, dict(logged_out=True), cookie='')
            if route == '/api/view' and self.command == 'GET':
                query = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=4, strict_parsing=True)
                if not set(query) <= {'name', 'offset', 'after', 'limit'} or any(len(v) != 1 for v in query.values()):
                    raise Refused()
                name = query.get('name', ['overview'])[0]
                if name not in VIEWS:
                    raise Refused()
                numbers = {}
                for key, default, low, high in [('offset', 0, 0, 1000000), ('after', 0, 0, 2**63-1), ('limit', 50, 1, 100)]:
                    value = query.get(key, [str(default)])[0]
                    if not re.fullmatch(r'[0-9]{1,19}', value):
                        raise Refused()
                    numbers[key] = int(value); _integer(numbers[key], low, high)
                return self.reply(200, app.model.view(name, **numbers))
            if self.command == 'POST' and route in {'/api/inspect', '/api/preview', '/api/execute'}:
                if ROLES[session['role']] < (2 if route == '/api/execute' else 1):
                    raise Refused(403)
                # Verify bound database even before planning a controller action.
                with app.p.controller._db() as db:
                    app.model.binding(db)
                if route == '/api/inspect':
                    shape(body, {'run_id'}); _id(body['run_id'])
                    return self.reply(200, RecoveryManager(app.p).inspect(body['run_id']))
                if route == '/api/preview':
                    shape(body, {'action', 'args'})
                    result = app.action(body['action'], body['args'])
                    now = time.monotonic()
                    session['plans'] = {k: v for k, v in session['plans'].items() if now < v['expires']}
                    if len(session['plans']) >= 8:
                        raise Refused(429)
                    plan = secrets.token_urlsafe(32)
                    session['plans'][plan] = dict(action=body['action'], args=body['args'], expires=now + 60)
                    return self.reply(200, dict(plan=plan, action=body['action'], args=body['args'], preview=result, expires_in=60))
                shape(body, {'plan'})
                if not isinstance(body['plan'], str):
                    raise Refused()
                plan = session['plans'].pop(body['plan'], None)
                if not plan or time.monotonic() >= plan['expires']:
                    raise Refused(409)
                result = app.action(plan['action'], plan['args'], execute=True)
                app.model.cached_at = 0
                return self.reply(200, dict(action=plan['action'], result=result))
            raise Refused(404)

    def handle_request(self):
        try:
            self.dispatch()
        except Refused as error:
            self.reply(error.status, dict(error='Request refused.'))
        except StateError:
            self.reply(409, dict(error='Controller refused; refresh state and preview again.'))
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
            self.reply(400, dict(error='Invalid request or metadata.'))
        except OSError:
            self.reply(503, dict(error='Local service unavailable.'))

    do_GET = handle_request
    do_POST = handle_request


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'db', 'workspaces', 'project-id', 'auth-file'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--duration', type=int, default=300)
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535 or not 10 <= args.duration <= 1800:
        parser.error('Port or finite lifetime outside allowed range.')
    server = None
    try:
        p = ParallelController(StateController(args.db), args.repo, args.workspaces, args.project_id)
        server = Server(Console(p, args.auth_file), args.port)
        timer = threading.Timer(args.duration, server.shutdown); timer.daemon = True; timer.start()
        print(json.dumps(dict(origin=server.origin, duration=args.duration)), flush=True)
        server.serve_forever(poll_interval=0.25)
        timer.cancel()
        return 0
    except (OSError, ValueError, StateError):
        print('Local console configuration unavailable.', flush=True)
        return 2
    finally:
        if server is not None:
            server.server_close()


if __name__ == '__main__':
    raise SystemExit(main())
