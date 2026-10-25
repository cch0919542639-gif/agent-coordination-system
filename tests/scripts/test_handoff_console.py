"""Optional handoff HTTP boundary; fixtures never contact Git or launch a runner."""
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts'), str(ROOT/'tests/scripts')]
from test_web_console import console, system, request, login
from web.api import handoff_service, StateError


class Handoff:
    def __init__(self):
        self.syncs = 0
        self.dispatches = []
        self.data = dict(configured=True, initialized=True, last_sync_ms=1,
            last_error=None, code_revision='a'*40, queue_head='0'*40,
            ready_tasks=[dict(task_id='task-a', owner='worker', card_sha256='b'*64)],
            peers=[dict(machine_id='peer', owner='worker')], dispatches=[], acceptance=[])

    def summary(self):
        return copy.deepcopy(self.data)

    def sync_once(self):
        self.syncs += 1
        return {'private_path': 'never-return-this'}

    def dispatch(self, task_id, machine_id, expected_card_sha256, expected_revision,
                 expected_queue_head, execute=False):
        if (task_id, machine_id, expected_card_sha256, expected_revision, expected_queue_head) != (
                'task-a', 'peer', self.data['ready_tasks'][0]['card_sha256'],
                self.data['code_revision'], self.data['queue_head']):
            raise ValueError('private failure details are not for HTTP')
        self.dispatches.append(execute)
        return dict(dispatch_id='dispatch-a', task_id=task_id, machine_id=machine_id,
                    owner='worker', status='RECEIVED' if execute else 'PREVIEW', raw_task='never-return-this')


def attach(c):
    c['app'].handoff = Handoff()
    return c['app'].handoff


def args():
    return dict(task_id='task-a', machine_id='peer', expected_card_sha256='b'*64,
                expected_revision='a'*40, expected_queue_head='0'*40)


def test_unconfigured_summary_and_actions(console):
    viewer = login(console)
    status, body, _ = request(console, '/api/view?name=handoff', session=viewer)
    assert status == 200 and body['handoff']['configured'] is False
    assert body['handoff']['last_sync_ms'] is None
    admin = login(console, 'administrator')
    assert request(console, '/api/preview', dict(action='handoff.sync', args={}), admin)[0] == 409


@pytest.mark.parametrize('role', ['viewer','operator','administrator'])
def test_sync_role_preview_confirmation_is_explicit_one_use(console, role):
    h = attach(console); session = login(console, role)
    for _ in range(3):
        assert request(console, '/api/view?name=handoff', session=session)[0] == 200
    assert h.syncs == 0 and not h.dispatches
    status, preview, _ = request(console, '/api/preview', dict(action='handoff.sync', args={}), session)
    assert status == (403 if role == 'viewer' else 200)
    assert h.syncs == 0
    status, result, _ = request(console, '/api/execute', dict(plan=preview.get('plan','forged')), session)
    assert status == (200 if role == 'administrator' else 403)
    assert h.syncs == (1 if role == 'administrator' else 0)
    assert 'never-return-this' not in json.dumps(result)
    if role == 'administrator':
        assert request(console, '/api/execute', dict(plan=preview['plan']), session)[0] == 409
        assert h.syncs == 1


def test_dispatch_sha_strings_preserved_rechecked_and_redacted(console):
    h = attach(console); admin = login(console, 'administrator')
    status, preview, _ = request(console, '/api/preview', dict(action='handoff.dispatch', args=args()), admin)
    assert status == 200 and preview['args'] == args()
    assert h.dispatches == [False] and 'raw_task' not in preview['preview']
    status, result, _ = request(console, '/api/execute', dict(plan=preview['plan']), admin)
    assert status == 200 and result['result']['status'] == 'RECEIVED'
    assert h.dispatches == [False, True]


@pytest.mark.parametrize('field', ['expected_card_sha256','expected_revision','expected_queue_head'])
def test_stale_dispatch_plan_refuses_and_is_consumed(console, field):
    h=attach(console); admin=login(console,'administrator')
    _, preview, _ = request(console,'/api/preview',dict(action='handoff.dispatch',args=args()),admin)
    if field == 'expected_card_sha256': h.data['ready_tasks'][0]['card_sha256']='c'*64
    else: h.data[{'expected_revision':'code_revision','expected_queue_head':'queue_head'}[field]]='c'*40
    status, result, _ = request(console,'/api/execute',dict(plan=preview['plan']),admin)
    assert status==409 and h.dispatches==[False]
    assert 'private' not in json.dumps(result)
    assert request(console,'/api/execute',dict(plan=preview['plan']),admin)[0]==409


def test_handoff_csrf_own_session_expiry_and_extra_fields(console):
    h=attach(console); admin=login(console,'administrator'); other=login(console,'administrator')
    body=dict(action='handoff.dispatch',args=args())
    assert request(console,'/api/preview',body,admin,headers={'X-CSRF-Token':'wrong'})[0]==403
    _, preview, _=request(console,'/api/preview',body,admin)
    assert request(console,'/api/execute',dict(plan=preview['plan']),other)[0]==409
    console['app'].sessions[admin['sid']]['plans'][preview['plan']]['expires']=0
    assert request(console,'/api/execute',dict(plan=preview['plan']),admin)[0]==409
    body['args']['expected_revision']=12
    assert request(console,'/api/preview',body,admin)[0]==400
    body['args']=dict(args(),execute=True)
    assert request(console,'/api/preview',body,admin)[0]==400
    assert h.dispatches==[False]


def test_summary_allowlist_and_generic_errors(console):
    h=attach(console); viewer=login(console)
    h.data.update(private_path='never-return-this',last_error='private/path')
    h.data['ready_tasks'][0]['body']='never-return-this'
    status,data,_=request(console,'/api/view?name=handoff',session=viewer)
    assert status==200 and data['handoff']['last_error']=='handoff_error'
    assert 'never-return-this' not in json.dumps(data)
    h.data['ready_tasks'][0]['task_id']='private/path'
    assert request(console,'/api/view?name=handoff',session=viewer)[0]==409


def test_optional_service_is_lazy_and_receives_binding(monkeypatch):
    assert handoff_service(None,None) is None
    calls=[]
    factory=lambda *a: calls.append(a) or 'adapter'
    monkeypatch.setitem(sys.modules,'coordination_runtime.github_handoff',SimpleNamespace(HandoffService=factory))
    p=SimpleNamespace(root=Path('repo'),project_id='project')
    assert handoff_service('external.json',p)=='adapter'
    assert calls==[('external.json',p.root,'project')]


def test_setup_serve_option_is_ephemeral(monkeypatch):
    import console_setup
    calls=[]
    monkeypatch.setattr(console_setup,'serve',lambda **kw:calls.append(kw))
    assert console_setup.main(['serve','--state-dir','private','--handoff-config','handoff.json'])==0
    assert calls[0]['handoff_config']=='handoff.json'
    assert console_setup.main(['serve','--state-dir','private'])==0
    assert calls[1]['handoff_config'] is None


def test_real_frontend_handoff_cached_view_and_string_bindings(tmp_path):
    import shutil
    binary = shutil.which('node')
    if not binary:
        pytest.skip('Installed Node required for frontend execution.')
    from worker_process_guard import JobProcess
    script = tmp_path/'handoff.cjs'
    script.write_text(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Element {
 constructor(){this.children=[];this.listeners={};this._value='resource.probe';this.hidden=false;this.disabled=false;this.dataset={};this.textContent='';}
 get value(){return this._value;} set value(x){this._value=x;}
 get options(){return this.children;} append(...xs){this.children.push(...xs);if(this.children.length===xs.length&&xs.length)this._value=xs[0].value;}
 replaceChildren(...xs){this.children=xs;this._value='';}
 addEventListener(n,f){this.listeners[n]=f;} setAttribute(){} removeAttribute(){} focus(){}
}
const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
const requests=[],context={AbortController,Date,Set,Number,JSON,Error,
 document:{hidden:false,getElementById:get,createElement:()=>new Element(),querySelectorAll:()=>[],addEventListener(){}},
 clearTimeout(){},setTimeout(){return 1;},fetch(path,opts){return new Promise(resolve=>requests.push({path,opts,resolve}));}};
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),context);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const summary={configured:true,initialized:true,last_sync_ms:1,last_error:null,code_revision:'a'.repeat(40),queue_head:'0'.repeat(40),
 ready_tasks:[{task_id:'task-a',owner:'worker',card_sha256:'b'.repeat(64)}],
 peers:[{machine_id:'peer',owner:'worker'},{machine_id:'wrong',owner:'other'}],acceptance:[],dispatches:[]};
function respond(req,data){req.resolve({ok:true,status:200,json:async()=>data});}
(async()=>{
 requests.shift().resolve({ok:false,status:401,json:async()=>({})});await tick();
 vm.runInContext("session={role:'administrator',csrf:'fixture'};navigate('handoff')",context);
 assert(requests[0].path.startsWith('/api/view?name=handoff'));
 respond(requests.shift(),{project_id:'project',sampled_ms:1,handoff:summary});await tick();
 assert.equal(get('handoff-peer').options.length,1);assert.equal(get('handoff-peer').value,'peer');
 assert(!get('handoff-preview').disabled);assert(get('handoff-binding').textContent.includes('expected_revision'));
 assert.equal(requests.length,0); // navigation/render does not trigger sync or dispatch
 get('handoff-form').listeners.submit({preventDefault(){}});
 let req=requests.shift(),body=JSON.parse(req.opts.body);
 assert.equal(req.path,'/api/preview');assert.equal(body.action,'handoff.dispatch');
 assert.equal(typeof body.args.expected_revision,'string');assert.equal(body.args.expected_queue_head,'0'.repeat(40));
 respond(req,{plan:'once',expires_in:60});await tick();assert(!get('confirm').hidden);
 vm.runInContext('refresh()',context);assert(requests[0].path.startsWith('/api/view?name=handoff'));
 respond(requests.shift(),{project_id:'project',sampled_ms:2,handoff:{...summary,queue_head:'c'.repeat(40)}});await tick();
 assert(get('confirm').hidden);assert.equal(vm.runInContext('plan',context),null);
 vm.runInContext("session.role='viewer';renderHandoff(handoffSnapshot)",context);assert(get('handoff-controls').hidden);
 console.log('handoff cache, peer matching, SHA strings, stale plan and Viewer passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
''',encoding='utf-8')
    job=JobProcess([binary,str(script),str(ROOT/'web/static/app.js')],cwd=tmp_path,capture_output=True)
    try:
        job.resume()
        assert job.wait(10)==0 and job.wait_empty(3)
        assert b'Viewer passed' in job.stdout.read()
    finally:
        job.close()
