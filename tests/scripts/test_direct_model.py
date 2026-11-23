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
    assert direct.complete('fixture-key', 'vendor/model:free', [{'role': 'user', 'content': 'hello'}], opener, privacy='standard') == ('review', 'stop')
    assert 'provider' not in captured['body']
    with pytest.raises(ValueError):
        direct.complete('fixture-key', 'vendor/model', [], opener, privacy='unexpected')
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
        def __init__(self, url): self.url = url
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size):
            if self.url == direct.CATALOG:
                return json.dumps({'data': [{'model_id': 'provider/a:free'}, {'model_id': 'provider/a:free'},
                                            {'model_id': 'provider/decision'}]}).encode()
            return json.dumps({'data': [
                {'id': 'provider/a:free', 'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']}},
                {'id': 'provider/b', 'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']}},
                {'id': 'provider/decision', 'architecture': {'input_modalities': ['text'], 'output_modalities': ['decision']}},
                {'id': 'invalid space', 'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']}}]}).encode()
    opener = lambda url, timeout: Response(url)
    assert direct.catalog(opener) == [{'id': 'provider/a:free', 'free': True}]
    assert direct.catalog(opener, privacy='standard') == [
        {'id': 'provider/a:free', 'free': True}, {'id': 'provider/b', 'free': False}]
    with pytest.raises(ValueError): direct.catalog(opener, privacy='bad')


def test_catalog_requires_administrator(console, monkeypatch):
    monkeypatch.setattr('web.api.catalog', lambda privacy='zdr': [{'id': 'vendor/' + privacy, 'free': True}])
    admin, viewer = login(console, 'administrator'), login(console, 'viewer')
    assert request(console, '/api/direct/models', session=viewer)[0] == 403
    assert request(console, '/api/direct/models', session=admin)[1]['models'][0]['id'] == 'vendor/zdr'
    assert request(console, '/api/direct/models?privacy=standard', session=viewer)[0] == 403
    assert request(console, '/api/direct/models?privacy=standard', session=admin)[1]['models'][0]['id'] == 'vendor/standard'
    assert request(console, '/api/direct/models?privacy=invalid', session=admin)[0] == 400


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
 assert.deepEqual(JSON.parse(post.opts.body),{agent:'direct',api_key:'fixture-key',model:'vendor/model:free',privacy:'zdr'});
 reply(post,200,{phase:'starting',models:[],response:''});await running;
 reply(requests.shift(),200,{agents:[{id:'direct',name:'direct',installed:true}],sessions:{direct:{phase:'starting',models:[]}}});await tick();
 const loading=get('direct-model-load').listeners.click();const catalog=requests.shift();assert.equal(catalog.path,'/api/direct/models?privacy=zdr');
 reply(catalog,200,{models:[{id:'vendor/model:free',free:true}]});await loading;
 assert.equal(get('direct-model-options').children[1].value,'vendor/model:free');
 assert(!get('direct-model-options').disabled);get('direct-model-options').value='vendor/model:free';get('direct-model-options').listeners.change();
 assert.equal(get('direct-model').value,'vendor/model:free');
 get('direct-privacy').value='standard';get('direct-privacy').listeners.change();
 assert(get('direct-privacy-note').textContent.includes('可能'));assert(get('direct-model-options').disabled);assert.equal(get('direct-model-options').children.length,1);
 const loading2=get('direct-model-load').listeners.click();const catalog2=requests.shift();assert.equal(catalog2.path,'/api/direct/models?privacy=standard');
 reply(catalog2,200,{models:[{id:'vendor/ordinary:free',free:true}]});await loading2;
 assert.equal(get('direct-model-options').children[1].value,'vendor/ordinary:free');
 vm.runInContext("renderAgents({agents:[{id:'direct',installed:true}],sessions:{direct:{phase:'ready',privacy:'standard',instance_id:'snapshot-id',model:'vendor/ordinary:free',models:[]}}})",ctx);
 assert.equal(get('direct-privacy').value,'standard');assert(get('direct-privacy').disabled);
 assert(get('direct-privacy-note').textContent.includes('可能'));
 get('agent-prompt').value='hello';const sending=get('agent-prompt-form').listeners.submit({preventDefault(){}});
 const prompt=requests.shift();assert.deepEqual(JSON.parse(prompt.opts.body),{agent:'direct',text:'hello',instance_id:'snapshot-id',privacy:'standard',model:'vendor/ordinary:free'});
 reply(prompt,200,{phase:'running',privacy:'standard',instance_id:'snapshot-id',models:[]});await sending;
 console.log('direct UI passed');
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
def complete(key,model,messages,privacy='zdr'):
    if messages[-1]['content']=='wait': time.sleep(60)
    if messages[-1]['content']=='fail': raise urllib.error.HTTPError('https://example.invalid',429,'private',None,None)
    return model+':'+str(len(messages))+(':'+privacy if privacy!='zdr' else ''), 'stop'
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
    assert request(console, '/api/agent/start', {**start, 'privacy': 'bad'}, admin)[0] == 400
    assert request(console, '/api/agent/start', start, admin)[0] == 200
    def wait(phase, response=None):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            value = request(console, '/api/agents', session=admin)[1]['sessions']['direct']
            if value['phase'] == phase and (response is None or value['response'] == response): return value
            time.sleep(.05)
        pytest.fail('direct session did not reach expected state')
    initial = wait('ready')
    assert initial['privacy'] == 'zdr'
    def prompt(text, state):
        return request(console, '/api/agent/prompt', {'agent': 'direct', 'text': text,
            'instance_id': state['instance_id'], 'privacy': state['privacy'], 'model': state['model']}, admin)[0]
    assert 'fixture-key' not in json.dumps(request(console, '/api/agents', session=admin)[1])
    assert request(console, '/api/agent/prompt', {'agent': 'direct', 'text': 'legacy'}, admin)[0] == 409
    assert prompt('wrong session', {**initial, 'instance_id': 'wrong'}) == 409
    assert prompt('x' * 40000, initial) == 200
    wait('ready', 'vendor/a:free:1')
    assert prompt('follow up', initial) == 200
    wait('ready', 'vendor/a:free:3')
    assert request(console, '/api/agent/model', {'agent': 'direct', 'model': 'vendor/b:free'}, admin)[0] == 200
    changed = wait('ready')
    assert changed['response'] == '' and changed['model'] == 'vendor/b:free'
    assert prompt('stale model', initial) == 409
    assert prompt('new model', changed) == 200
    wait('ready', 'vendor/b:free:1')
    assert prompt('fail', changed) == 200
    assert wait('ready')['error'] == 'Agent 請求失敗（HTTP 429）。'
    agent = console['app'].agent_sessions[admin['sid']]['direct']
    pid, created = agent.job.pid, agent.job.creation_time
    assert prompt('wait', changed) == 200
    assert request(console, '/api/agent/stop', {'agent': 'direct'}, admin)[0] == 200
    assert request(console, '/api/agent/start', {**start, 'privacy': 'standard'}, admin)[0] == 200
    current = wait('ready')
    assert current['privacy'] == 'standard' and current['instance_id'] != initial['instance_id']
    assert request(console, '/api/agent/prompt', {'agent': 'direct', 'text': 'legacy'}, admin)[0] == 409
    assert prompt('stale ZDR tab', initial) == 409
    assert prompt('wrong privacy', {**current, 'privacy': 'zdr'}) == 409
    assert current['response'] == '' and prompt('hello', current) == 200
    wait('ready', 'vendor/a:free:1:standard')
    assert request(console, '/api/agent/stop', {'agent': 'direct'}, admin)[0] == 200
    assert identity_state(pid, created) in ('missing', 'exited')
    monkeypatch.setenv('COORDINATION_OPENROUTER_API_KEY', 'fixture-key')
    monkeypatch.setenv('COORDINATION_DIRECT_MODELS', 'vendor/a:free')
    assert request(console, '/api/agent/start', {'agent': 'direct'}, admin)[0] == 200
    wait('ready')
    assert request(console, '/api/agent/stop', {'agent': 'direct'}, admin)[0] == 200
