"""Text-only direct model routing and real console session boundaries."""
import json
import os
from pathlib import Path
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts'), str(ROOT / 'tests/scripts')]
from test_parallel_runtime import system
from test_web_console import console, login, request
from web import agent_control, direct_model_bridge as direct
from worker_process_guard import identity_state


def test_provider_request_requires_private_routing_and_has_no_tools():
    captured = {}
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size):
            return json.dumps({'choices': [{'message': {'content': 'review'}, 'finish_reason': 'stop'}]}).encode()
    def opener(req, timeout):
        captured.update(url=req.full_url, body=json.loads(req.data), timeout=timeout)
        assert req.get_header('Authorization') == 'Bearer fixture-key'
        return Response()
    assert direct.complete('fixture-key', 'vendor/model:free', [{'role': 'user', 'content': 'hello'}], opener) == ('review', 'stop')
    assert captured['url'] == direct.ENDPOINT and captured['timeout'] == 90
    assert captured['body']['provider'] == {'zdr': True, 'data_collection': 'deny'}
    assert 'tools' not in captured['body']
    assert direct.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://elsewhere.invalid') is None


def test_direct_inventory_requires_key_and_valid_models(monkeypatch):
    monkeypatch.delenv('COORDINATION_OPENROUTER_API_KEY', raising=False)
    monkeypatch.setenv('COORDINATION_DIRECT_MODELS', 'vendor/a:free, bad model, vendor/a:free')
    assert direct.model_ids() == ['vendor/a:free']
    assert not next(x for x in agent_control.inventory() if x['id'] == 'direct')['configured']
    monkeypatch.setenv('COORDINATION_OPENROUTER_API_KEY', 'fixture-key')
    assert next(x for x in agent_control.inventory() if x['id'] == 'direct')['configured']
    monkeypatch.setenv('COORDINATION_DIRECT_MODELS', 'bad model')
    assert not next(x for x in agent_control.inventory() if x['id'] == 'direct')['configured']


def test_model_catalog_is_bounded_and_deduplicated(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size):
            return json.dumps({'data': [{'model_id': 'provider/a:free'}, {'model_id': 'provider/a:free'},
                                        {'model_id': 'provider/b'}, {'model_id': 'invalid space'}]}).encode()
    assert direct.catalog(lambda url, timeout: Response()) == [
        {'id': 'provider/a:free', 'free': True}, {'id': 'provider/b', 'free': False}]


def test_catalog_requires_administrator(console, monkeypatch):
    monkeypatch.setattr('web.api.catalog', lambda: [{'id': 'vendor/a:free', 'free': True}])
    admin, viewer = login(console, 'administrator'), login(console, 'viewer')
    assert request(console, '/api/direct/models', session=viewer)[0] == 403
    assert request(console, '/api/direct/models', session=admin)[1]['models'][0]['id'] == 'vendor/a:free'


@pytest.mark.skipif(os.name != 'nt', reason='Windows owned Job')
def test_direct_frontend_key_and_model_controls(tmp_path):
    import shutil
    from worker_process_guard import JobProcess
    binary = shutil.which('node')
    if not binary: pytest.skip('Node required')
    script = tmp_path / 'direct-ui.cjs'
    script.write_text(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class E{constructor(){this.children=[];this.listeners={};this.value='';this.hidden=false;this.disabled=false;this.dataset={};this.textContent='';}
append(...a){this.children.push(...a)}replaceChildren(...a){this.children=a}addEventListener(n,f){this.listeners[n]=f}setAttribute(){}removeAttribute(){}focus(){}}
const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new E());return nodes.get(id)},requests=[];
const ctx={AbortController,Date,Set,Number,JSON,Error,document:{hidden:false,getElementById:get,createElement:()=>new E(),querySelectorAll:()=>[],addEventListener(){}},
clearTimeout(){},setTimeout(){return 1},fetch(path,opts){return new Promise(resolve=>requests.push({path,opts,resolve}))}};
get('action').value='resource.probe';vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),ctx);
const tick=()=>new Promise(r=>setImmediate(r));function reply(req,status,body){req.resolve({ok:status===200,status,json:async()=>body})}
(async()=>{
 reply(requests.shift(),401,{});await tick();get('agent-kind').value='direct';
 vm.runInContext("session={role:'administrator',csrf:'fixture'};navigate('agents')",ctx);
 reply(requests.shift(),200,{agents:[{id:'direct',name:'direct',installed:true,configured:false}],sessions:{}});await tick();
 assert(!get('direct-config').hidden && get('agent-start').disabled);
 get('direct-key').value='fixture-key';get('direct-model').value='vendor/model:free';get('direct-model').listeners.input();
 assert(!get('agent-start').disabled);
 const running=get('agent-start').listeners.click();const post=requests.shift();
 assert.equal(post.path,'/api/agent/start');assert.equal(get('direct-key').value,'');
 assert.deepEqual(JSON.parse(post.opts.body),{agent:'direct',api_key:'fixture-key',model:'vendor/model:free'});
 reply(post,200,{phase:'starting',models:[],response:''});await running;
 reply(requests.shift(),200,{agents:[{id:'direct',name:'direct',installed:true}],sessions:{direct:{phase:'starting',models:[]}}});await tick();
 const loading=get('direct-model-load').listeners.click();const catalog=requests.shift();assert.equal(catalog.path,'/api/direct/models');
 reply(catalog,200,{models:[{id:'vendor/model:free',free:true}]});await loading;
 assert.equal(get('direct-model-options').children[0].value,'vendor/model:free');console.log('direct UI passed');
})().catch(e=>{console.error(e);process.exitCode=1});
''', encoding='utf-8')
    job = JobProcess([binary, str(script), str(ROOT / 'web/static/app.js')], cwd=tmp_path, capture_output=True)
    try:
        job.resume()
        assert job.wait(10) == 0 and job.wait_empty(3)
        assert b'direct UI passed' in job.stdout.read()
    finally:
        job.close()


@pytest.mark.skipif(os.name != 'nt', reason='Windows owned Job')
def test_direct_console_roundtrip_auth_model_history_and_owned_stop(console, tmp_path, monkeypatch):
    monkeypatch.delenv('COORDINATION_OPENROUTER_API_KEY', raising=False)
    monkeypatch.delenv('COORDINATION_DIRECT_MODELS', raising=False)
    bridge = tmp_path / 'web' / 'direct_model_bridge.py'
    bridge.parent.mkdir()
    bridge.write_text('''import sys,time,urllib.error
sys.path.insert(0,sys.argv.pop(1))
from web import direct_model_bridge as bridge
def complete(key,model,messages):
    if messages[-1]['content']=='wait': time.sleep(60)
    if messages[-1]['content']=='fail': raise urllib.error.HTTPError('https://example.invalid',429,'private',None,None)
    return model+':'+str(len(messages)), 'stop'
bridge.complete=complete
bridge.main()
''', encoding='utf-8')
    # Keep the production bridge in the command while using a synthetic provider.
    original = agent_control.JobProcess
    def launch(args, **kwargs):
        if args[2].endswith('direct_model_bridge.py'):
            assert 'fixture-key' not in ' '.join(args) and kwargs.get('pipe_stdin') is True
            args = [args[0], args[1], str(bridge), str(ROOT), *args[3:]]
        return original(args, **kwargs)
    monkeypatch.setattr(agent_control, 'JobProcess', launch)
    admin, viewer = login(console, 'administrator'), login(console, 'viewer')
    start = {'agent': 'direct', 'api_key': 'fixture-key', 'model': 'vendor/a:free'}
    assert request(console, '/api/agent/start', start, viewer)[0] == 403
    assert request(console, '/api/agent/start', {'agent': 'direct'}, admin)[0] == 409
    assert request(console, '/api/agent/start', {**start, 'api_key': 'bad\nkey'}, admin)[0] == 400
    assert request(console, '/api/agent/start', start, admin, headers={'X-CSRF-Token': 'wrong'})[0] == 403
    assert request(console, '/api/agent/start', start, admin)[0] == 200
    def wait(phase, response=None):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            value = request(console, '/api/agents', session=admin)[1]['sessions']['direct']
            if value['phase'] == phase and (response is None or value['response'] == response): return value
            time.sleep(.05)
        pytest.fail('direct session did not reach expected state')
    wait('ready')
    assert 'fixture-key' not in json.dumps(request(console, '/api/agents', session=admin)[1])
    assert request(console, '/api/agent/prompt', {'agent': 'direct', 'text': 'x' * 40000}, admin)[0] == 200
    wait('ready', 'vendor/a:free:1')
    assert request(console, '/api/agent/prompt', {'agent': 'direct', 'text': 'follow up'}, admin)[0] == 200
    wait('ready', 'vendor/a:free:3')
    assert request(console, '/api/agent/model', {'agent': 'direct', 'model': 'vendor/b:free'}, admin)[0] == 200
    assert wait('ready')['response'] == ''
    assert request(console, '/api/agent/prompt', {'agent': 'direct', 'text': 'new model'}, admin)[0] == 200
    wait('ready', 'vendor/b:free:1')
    assert request(console, '/api/agent/prompt', {'agent': 'direct', 'text': 'fail'}, admin)[0] == 200
    assert wait('ready')['error'] == 'Agent 請求失敗（HTTP 429）。'
    agent = console['app'].agent_sessions[admin['sid']]['direct']
    pid, created = agent.job.pid, agent.job.creation_time
    assert request(console, '/api/agent/prompt', {'agent': 'direct', 'text': 'wait'}, admin)[0] == 200
    assert request(console, '/api/agent/stop', {'agent': 'direct'}, admin)[0] == 200
    assert identity_state(pid, created) in ('missing', 'exited')
    monkeypatch.setenv('COORDINATION_OPENROUTER_API_KEY', 'fixture-key')
    monkeypatch.setenv('COORDINATION_DIRECT_MODELS', 'vendor/a:free')
    assert request(console, '/api/agent/start', {'agent': 'direct'}, admin)[0] == 200
    wait('ready')
    assert request(console, '/api/agent/stop', {'agent': 'direct'}, admin)[0] == 200
