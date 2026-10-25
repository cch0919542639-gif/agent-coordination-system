"""Real loopback HTTP, controller state and access-boundary verification."""
import hashlib
import http.client
import json
from pathlib import Path
import secrets
import shutil
import socket
import sys
import threading
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts'), str(ROOT / 'tests/scripts')]
from test_parallel_runtime import system, prepare
from coordination_runtime.state_controller import StateController, StateError
from coordination_runtime.parallel_runtime import ParallelController
from coordination_runtime.resource_guard import ResourceController
from web.api import Console, Server


@pytest.fixture
def console(system, tmp_path):
    p, db, clock = system
    tokens = {role: secrets.token_urlsafe(32) for role in ('viewer', 'operator', 'administrator')}
    auth = tmp_path / 'auth.json'
    auth.write_text(json.dumps(dict(schema_version=1, users=[dict(username=role, role=role,
        token_sha256=hashlib.sha256(token.encode()).hexdigest()) for role, token in tokens.items()])))
    app = Console(p, auth); server = Server(app)
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    thread.start()
    yield dict(p=p, db=db, clock=clock, app=app, server=server, tokens=tokens, auth=auth)
    server.shutdown(); server.server_close(); thread.join(3)
    assert not thread.is_alive()


def request(c, path, body=None, session=None, headers=None, raw=None):
    s = c['server']; h = {'Origin': s.origin}
    if body is not None or raw is not None:
        h['Content-Type'] = 'application/json'
    if session:
        h['Cookie'] = s.cookie + '=' + session['sid']; h['X-CSRF-Token'] = session['csrf']
    h.update(headers or {})
    connection = http.client.HTTPConnection('127.0.0.1', s.server_port, timeout=3)
    connection.request('POST' if body is not None or raw is not None else 'GET', path,
                       raw if raw is not None else json.dumps(body) if body is not None else None, h)
    response = connection.getresponse(); data = response.read(); status = response.status
    response_headers = dict(response.getheaders()); connection.close()
    return status, json.loads(data) if 'application/json' in response_headers.get('Content-Type', '') else data, response_headers


def login(c, role='viewer'):
    status, data, headers = request(c, '/api/login', dict(username=role, token=c['tokens'][role]))
    assert status == 200
    assert 'HttpOnly' in headers['Set-Cookie'] and 'SameSite=Strict' in headers['Set-Cookie']
    return dict(data, sid=headers['Set-Cookie'].partition('=')[2].partition(';')[0])


def test_real_board_schema4_views_and_private_receipts(console):
    c = console; prepare((c['p'], c['db'], c['clock']))
    viewer = login(c)
    for name in ('overview', 'board', 'monitor', 'workspaces', 'reviews', 'events', 'settings'):
        status, data, headers = request(c, '/api/view?name=' + name, session=viewer)
        assert status == 200 and data['runtime_available'] and data['project_id'] == 'project'
        assert 'no-store' in headers['Cache-Control'] and "frame-ancestors 'none'" in headers['Content-Security-Policy']
        raw = json.dumps(data)
        assert str(c['p'].root) not in raw and 'process_json' not in raw and 'artifact_ref' not in raw
    _, data, _ = request(c, '/api/view?name=board', session=viewer)
    assert data['total'] == 3 and {r['task_id'] for r in data['rows']} == {'task-a', 'task-b', 'task-c'}
    _, data, _ = request(c, '/api/view?name=monitor', session=viewer)
    assert data['rows'][0]['run_id'] == 'run-task-a' and data['rows'][0]['fence'] == 1


@pytest.mark.parametrize('route', ['/api/view', '/api/session', '/api/inspect', '/api/preview', '/api/execute'])
def test_auth_required(console, route):
    status, _, _ = request(console, route, {} if route in {'/api/inspect', '/api/preview', '/api/execute'} else None)
    assert status == 401


@pytest.mark.parametrize('role', ['viewer', 'operator', 'administrator'])
def test_server_side_role_enforcement_and_one_use_confirmation(console, role):
    session = login(console, role); before = console['db'].path.read_bytes()
    status, preview, _ = request(console, '/api/preview', dict(action='parallel.disable', args={}), session)
    assert status == (403 if role == 'viewer' else 200)
    assert console['db'].path.read_bytes() == before and console['p'].marker.exists()
    status, _, _ = request(console, '/api/execute', dict(plan=preview.get('plan', 'forged')), session)
    assert status == (200 if role == 'administrator' else 403)
    if role == 'administrator':
        assert not console['p'].marker.exists()
        assert request(console, '/api/execute', dict(plan=preview['plan']), session)[0] == 409


def test_plan_session_expiry_arguments_and_stale_resource_guard(console):
    admin = login(console, 'administrator'); other = login(console, 'administrator')
    body = dict(action='resource.reset', args=dict(expected_sequence=0))
    status, preview, _ = request(console, '/api/preview', body, admin); assert status == 200
    assert request(console, '/api/execute', dict(plan=preview['plan']), other)[0] == 409
    assert request(console, '/api/execute', dict(plan=preview['plan'], args={}), admin)[0] == 400
    console['app'].sessions[admin['sid']]['plans'][preview['plan']]['expires'] = 0
    assert request(console, '/api/execute', dict(plan=preview['plan']), admin)[0] == 409
    _, preview, _ = request(console, '/api/preview', body, admin)
    # A real controller event changes the expected latch sequence after preview.
    with console['db']._db(write=True) as db:
        ResourceController(console['p'])._append(db, True, {}, 'fixture')
    before = console['db'].path.read_bytes()
    assert request(console, '/api/execute', dict(plan=preview['plan']), admin)[0] == 409
    assert console['db'].path.read_bytes() == before


def test_recovery_inspect_preview_and_version_recheck(console):
    c = console; prepare((c['p'], c['db'], c['clock'])); c['clock'][0] = 200000
    admin = login(c, 'administrator'); before = c['db'].path.read_bytes()
    status, state, _ = request(c, '/api/inspect', dict(run_id='run-task-a'), admin)
    assert status == 200 and state['never_launched'] and not state['lease_valid']
    body = dict(action='recovery.reconcile', args=dict(run_id='run-task-a', request_id='recover-a',
                expected_version=state['expected_version'], expected_fence=1, reason='expired'))
    status, preview, _ = request(c, '/api/preview', body, admin); assert status == 200
    assert c['db'].path.read_bytes() == before
    # Same real Controller authority revocation wins outside the web preview.
    from coordination_runtime.recovery_manager import RecoveryManager
    RecoveryManager(c['p']).reconcile(**dict(body['args'], request_id='other-recovery'), execute=True)
    before = c['db'].path.read_bytes()
    assert request(c, '/api/execute', dict(plan=preview['plan']), admin)[0] == 409
    assert c['db'].path.read_bytes() == before


@pytest.mark.parametrize('headers', [{'Origin': 'http://evil.invalid'}, {'Origin':'null'},
    {'Host':'evil.invalid'}, {'X-CSRF-Token':'wrong'}, {'Content-Type':'text/plain'}])
def test_origin_host_csrf_and_content_type_refuse_without_writes(console, headers):
    session = login(console, 'administrator'); before = console['db'].path.read_bytes()
    if any(key in headers for key in ('Host', 'Origin', 'Content-Type')):
        s = console['server']
        sent = {'Host': s.origin.removeprefix('http://'), 'Origin': s.origin,
                'Content-Type': 'application/json', 'Content-Length': '0'} | headers
        with socket.create_connection(('127.0.0.1', s.server_port), timeout=3) as conn:
            conn.sendall(('POST /api/preview HTTP/1.1\r\n' + ''.join(
                key + ': ' + value + '\r\n' for key, value in sent.items()) + '\r\n').encode())
            assert (b' 415 ' if 'Content-Type' in headers else b' 403 ') in conn.recv(4096)
    else:
        assert request(console, '/api/preview', dict(action='parallel.disable', args={}), session, headers)[0] == 403
    assert console['db'].path.read_bytes() == before


@pytest.mark.parametrize('path', ['/api/view?name=board&name=events', '/api/view?limit=101',
    '/api/view?offset=-1', '/api/view?after=9223372036854775808', '/api/view?name=unknown',
    '/api/view?secret=x', '/api/view?limit=true'])
def test_query_bounds(console, path):
    assert request(console, path, session=login(console))[0] in {400,409}


@pytest.mark.parametrize('raw', ['{"action":"parallel.disable","action":"resource.probe","args":{}}',
    '{"action":"parallel.disable","args":{},"execute":true}', '{"action":"sql","args":{}}',
    '{"action":"resource.reset","args":{"expected_sequence":true}}',
    '{"action":"resource.reset","args":{"expected_sequence":NaN}}', 'x' * 16385],
    ids=['duplicate', 'extra-field', 'unknown-op', 'boolean-int', 'nonfinite', 'oversize'])
def test_json_and_operation_allowlist(console, raw):
    before = console['db'].path.read_bytes(); session = login(console, 'administrator')
    if len(raw) > 16384:
        # Refuse from length before reading; avoid Windows unread-body TCP reset
        # racing the HTTP client's upload/response in this transport-boundary test.
        s = console['server']
        with socket.create_connection(('127.0.0.1', s.server_port), timeout=3) as conn:
            conn.sendall(('POST /api/preview HTTP/1.1\r\nHost: 127.0.0.1:' + str(s.server_port) +
                          '\r\nOrigin: ' + s.origin + '\r\nContent-Type: application/json\r\nContent-Length: 16385\r\n\r\n').encode())
            assert b' 413 ' in conn.recv(4096)
    else:
        assert request(console, '/api/preview', session=session, raw=raw)[0] in {400,409}
    assert console['db'].path.read_bytes() == before


def test_duplicates_chunking_and_static_path_traversal(console):
    s = console['server']
    for extra in ['Host: evil.invalid\r\n', 'Transfer-Encoding: chunked\r\n']:
        with socket.create_connection(('127.0.0.1', s.server_port), timeout=3) as conn:
            conn.sendall(('GET / HTTP/1.1\r\nHost: 127.0.0.1:' + str(s.server_port) + '\r\n' + extra + '\r\n').encode())
            assert b' 400 ' in conn.recv(4096)
    viewer = login(console)
    for path in ('/../PLAN.md', '/%2e%2e/PLAN.md', '/auth.json'):
        assert request(console, path, session=viewer)[0] == 404
    for path in ('/', '/app.css', '/app.js'):
        assert request(console, path)[0] == 200


def test_missing_database_and_foreign_binding_never_create_or_migrate(console, tmp_path):
    c = console; original = c['p'].controller
    missing = tmp_path / 'missing.db'; c['p'].controller = StateController(missing)
    viewer = login(c)
    status, data, _ = request(c, '/api/view?name=overview', session=viewer)
    assert status == 200 and not data['runtime_available'] and 'active_runs' not in data and not missing.exists()
    c['p'].controller = original
    with original._db(write=True) as db:
        db.execute("UPDATE project_bindings SET root_digest=?", ('0' * 64,))
    before = original.path.read_bytes()
    assert request(c, '/api/view?name=settings', session=viewer)[0] == 409
    assert original.path.read_bytes() == before


def test_event_cursor_project_filter_and_no_opaque_artifacts(console):
    c = console
    with c['db']._db(write=True) as db:
        for n in range(105):
            db.execute('INSERT INTO events(schema_version,event_id,project_id,task_id,run_id,agent_id,event_type,timestamp_ms,causation_id,artifact_ref) VALUES(?,?,?,?,?,?,?,?,?,?)',
                       (1, 'event-' + str(n), 'other' if n == 3 else 'project', 'task-a', 'run-a', 'worker', 'fixture.event', 10000, 'fixture', 'PRIVATE-TRANSCRIPT'))
    viewer = login(c); cursor = 0; sequences = []
    while True:
        status, data, _ = request(c, '/api/view?name=events&after=' + str(cursor) + '&limit=50', session=viewer)
        assert status == 200 and len(data['rows']) <= 50 and 'PRIVATE-TRANSCRIPT' not in json.dumps(data)
        sequences.extend(row['sequence'] for row in data['rows']); cursor = data['cursor']
        if not data['more']: break
    assert len(sequences) == 105 and len(sequences) == len(set(sequences))  # initial mode event +104


def test_logout_session_expiry_and_login_throttle(console):
    viewer = login(console)
    assert request(console, '/api/logout', {}, viewer)[0] == 200
    assert request(console, '/api/session', session=viewer)[0] == 401
    viewer = login(console); console['app'].sessions[viewer['sid']]['expires'] = 0
    assert request(console, '/api/session', session=viewer)[0] == 401
    for _ in range(5):
        assert request(console, '/api/login', dict(username='viewer', token='bad'))[0] == 401
    assert request(console, '/api/login', dict(username='viewer', token=console['tokens']['viewer']))[0] == 429


def test_auth_file_is_mandatory_external_and_never_plaintext(console):
    p = console['p']
    with pytest.raises(StateError): Console(p, p.root / 'auth.json')
    assert not any(value in console['auth'].read_text() for value in console['tokens'].values())
    console['auth'].write_text('{"schema_version":1,"users":[]}')
    with pytest.raises(StateError): Console(p, console['auth'])


def test_conflicting_board_is_explicit_error_and_never_raw_body(console):
    c = console; viewer = login(c)
    card = c['p'].root / 'coordination/task-board/ready/task-a.md'
    raw = card.read_bytes() + b'PRIVATE-TRANSCRIPT'
    card.write_bytes(raw)
    assert 'PRIVATE-TRANSCRIPT' not in json.dumps(request(c, '/api/view?name=board', session=viewer)[1])
    (card.parent / 'duplicate.md').write_bytes(raw); c['app'].model.cached_at = 0
    status, data, _ = request(c, '/api/view?name=board', session=viewer)
    assert status == 409 and 'PRIVATE' not in json.dumps(data)


@pytest.mark.parametrize('action', ['board.reconcile', 'board.cancel'])
def test_known_board_intent_preview_and_execution(console, action):
    c = console; prepare((c['p'], c['db'], c['clock']))
    admin = login(c, 'administrator'); before = c['db'].path.read_bytes()
    status, preview, _ = request(c, '/api/preview', dict(action=action, args=dict(request_id='claim-task-a')), admin)
    assert status == 200 and preview['preview']['dry_run']
    assert c['db'].path.read_bytes() == before
    status, data, _ = request(c, '/api/execute', dict(plan=preview['plan']), admin)
    assert status == 200 and data['result']['status'] == ('applied' if action.endswith('reconcile') else 'cancelled')


def test_board_pagination_and_card_bounds(console):
    from test_parallel_runtime import card
    c = console; directory = c['p'].root / 'coordination/task-board/ready'
    for n in range(101): (directory / ('extra-' + str(n) + '.md')).write_bytes(card('extra-' + str(n)))
    viewer = login(c)
    status, first, _ = request(c, '/api/view?name=board', session=viewer)
    status2, last, _ = request(c, '/api/view?name=board&offset=100', session=viewer)
    assert status == status2 == 200 and len(first['rows']) == 100 and len(last['rows']) == 4
    assert first['more'] and not last['more']
    assert not {r['task_id'] for r in first['rows']} & {r['task_id'] for r in last['rows']}
    (directory / 'task-a.md').write_bytes(b'x' * 65537); c['app'].model.cached_at = 0
    assert request(c, '/api/view?name=board', session=viewer)[0] == 409


def test_frontend_pending_pager_and_navigation_discard_stale_response(tmp_path):
    """Execute the real production script with deterministic delayed fetches."""
    binary = shutil.which('node')
    if not binary:
        pytest.skip('Installed Node required for frontend race regression.')
    from worker_process_guard import JobProcess
    script = tmp_path / 'paging.cjs'
    script.write_text(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Element {
 constructor(){this.children=[];this.listeners={};this.value='resource.probe';this.hidden=false;this.disabled=false;this.dataset={};this.textContent='';}
 append(...xs){this.children.push(...xs);} replaceChildren(...xs){this.children=xs;}
 addEventListener(n,f){this.listeners[n]=f;} setAttribute(){} removeAttribute(){} focus(){}
}
const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
const requests=[],context={AbortController,Date,Set,Number,JSON,Error,
 document:{hidden:false,getElementById:get,createElement:()=>new Element(),querySelectorAll:()=>[],addEventListener(){}},
 clearTimeout(){},setTimeout(){return 1;},fetch(path,opts){return new Promise(resolve=>requests.push({path,opts,resolve}));}};
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),context);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function respond(req,offset){req.resolve({ok:true,status:200,json:async()=>({project_id:'fixture',runtime_available:true,sampled_ms:0,rows:[{task_id:'row-'+offset,status:'READY'}],offset,total:300,more:offset<200})});}
(async()=>{
 requests.shift().resolve({ok:false,status:401,json:async()=>({})});await tick();
 vm.runInContext("session={role:'viewer',csrf:'fixture'}; navigate('board')",context);respond(requests.shift(),0);await tick();
 get('next').listeners.click();assert(get('next').disabled && get('previous').disabled);
 get('next').listeners.click();get('previous').listeners.click();assert.equal(requests.length,1);
 assert(requests[0].path.includes('offset=100'));respond(requests.shift(),100);await tick();
 assert.equal(vm.runInContext('offset',context),100);assert(get('page-info').textContent.includes('2'));
 assert(!get('next').disabled && !get('previous').disabled);
 get('previous').listeners.click();assert(requests[0].path.includes('offset=0'));
 const stale=requests.shift();vm.runInContext("navigate('events')",context);
 const latest=requests.shift();respond(stale,0);await tick();
 assert.equal(vm.runInContext('view',context),'events');respond(latest,0);await tick();
 assert(get('page-info').textContent.includes('游標'));
 for(const status of [200,401]) {
  requests.length=0;
  const fresh={...context};vm.createContext(fresh);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),fresh);
  const oldRestore=requests.shift();get('username').value='administrator';get('token').value='fixture';
  const submitted=get('login-form').listeners.submit({preventDefault(){},submitter:get('submit')});
  requests.shift().resolve({ok:true,status:200,json:async()=>({username:'administrator',role:'administrator',csrf:'new'})});
  await submitted;assert.equal(vm.runInContext('session.role',fresh),'administrator');
  oldRestore.resolve({ok:status===200,status,json:async()=>({username:'viewer',role:'viewer',csrf:'old'})});
  await tick();assert.equal(vm.runInContext('session.role',fresh),'administrator');assert(get('login').hidden);
 }
 console.log('pager and stale navigation passed; old session restore discarded');
})().catch(error=>{console.error(error);process.exitCode=1;});
''', encoding='utf-8')
    job = JobProcess([binary, str(script), str(ROOT / 'web/static/app.js')], cwd=tmp_path, capture_output=True)
    try:
        job.resume()
        assert job.wait(10) == 0 and job.wait_empty(3)
        assert b'pager and stale navigation passed' in job.stdout.read()
    finally:
        job.close()


def test_board_enumerates_lazily_and_bounds_ignored_entries(console, monkeypatch):
    import os
    from types import SimpleNamespace
    real = os.scandir; count = [0]; first_read = []
    class Entries:
        def __init__(self, source): self.source = source
        def __enter__(self): return self
        def __exit__(self, *args):
            if hasattr(self.source, 'close'): self.source.close()
        def __iter__(self):
            for entry in self.source:
                count[0] += 1
                yield entry
    monkeypatch.setattr('web.read_model.os.scandir', lambda path: Entries(real(path)))
    original_read = console['p'].board._read
    def observed(path):
        first_read.append(count[0])
        return original_read(path)
    monkeypatch.setattr(console['p'].board, '_read', observed)
    assert len(console['app'].model.board()) == 3
    assert first_read[0] == 1
    count[0] = 0; console['app'].model.cached_at = 0
    monkeypatch.setattr('web.read_model.os.scandir', lambda path: Entries(
        SimpleNamespace(name='ignored.txt') for _ in range(10000)))
    with pytest.raises(StateError, match='enumeration exceeds'):
        console['app'].model.board()
    assert count[0] == 4097
