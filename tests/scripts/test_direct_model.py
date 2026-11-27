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


def test_multi_provider_transport_and_validation():
    captured = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size): return json.dumps({'choices':[{'message':{'content':'ok'},'finish_reason':'stop'}]}).encode()
    def opener(req, timeout):
        captured.append((req.full_url, json.loads(req.data), req.get_header('Authorization')))
        return Response()
    providers = [('deepseek', '', 'https://api.deepseek.com/chat/completions'),
                 ('agnes', '', 'https://apihub.agnes-ai.com/v1/chat/completions'),
                 ('custom', 'https://api.example.test/v1/', 'https://api.example.test/v1/chat/completions')]
    for name, base, expected in providers:
        assert direct.complete('fixture-key', 'example/model', [{'role':'user','content':'hello'}], opener,
                               privacy='standard', provider=name, base_url=base) == ('ok', 'stop')
        url, payload, auth = captured[-1]
        assert url == expected and auth == 'Bearer fixture-key'
        assert 'provider' not in payload and 'fixture-key' not in json.dumps(payload)
        with pytest.raises(ValueError): direct.complete('fixture-key','m',[],opener, privacy='zdr', provider=name, base_url=base)
    for bad in ('http://example.test/v1', 'https://name:password@example.test/v1',
                'https://example.test/v1?key=secret', 'https://example.test/v1#fragment',
                'https://example.test/v1?', 'https://example.test:99999/v1',
                'https://example.test/space here', 'https://example.test/\\evil'):
        with pytest.raises(ValueError): direct.provider_endpoint('custom', bad, 'standard')
    for bad_provider, base, privacy in [('invalid','','standard'), ('deepseek','https://evil.test','standard'),
                                         ('openrouter','https://evil.test','zdr'), ('custom','','standard'),
                                         ('custom',[],'standard')]:
        with pytest.raises(ValueError): direct.provider_endpoint(bad_provider,base,privacy)


def test_provider_404_classification_is_bounded_and_never_forwards_untrusted_text():
    import io
    import urllib.error

    def classify(payload, status=404, model='vendor/model'):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        error = urllib.error.HTTPError('https://invalid.example/secret', status, 'private', None, io.BytesIO(body))
        return direct.provider_404_reason(error, model)

    def body(message): return {'error': {'message': message}}
    assert classify(body('No endpoints found matching your data policy (Zero data retention). Configure: https://openrouter.ai/settings/privacy')) == 'privacy_policy'
    assert classify(body('No endpoints found supporting your data region.')) == 'data_region'
    assert classify(body('No endpoints found that satisfy the max price for this request')) == 'price_limit'
    assert classify(body('vendor/model is not a valid model ID')) == 'model_not_found'
    assert classify(body('No endpoint found for model "vendor/model"')) == 'no_endpoints'
    for payload in (b'bad json', b'x' * 16385, b'[' * 8000 + b'0' + b']' * 8000, {}, {'error': None},
                    body('No endpoints found matching your data policy. secret-key'),
                    body('vendor/model is not a valid model ID secret-key'),
                    body('No endpoints found for private prompt secret-key')):
        assert classify(payload) is None
    assert classify(body('No endpoints found.'), status=429) is None
    assert classify(body('other/model is not a valid model ID')) is None


def test_slow_404_body_has_deadline_and_limits_concurrent_readers(monkeypatch):
    import io
    import threading
    import urllib.error

    started, release, closed = threading.Event(), threading.Event(), threading.Event()
    class SlowBody:
        def read(self, size):
            started.set()
            release.wait(5)
            return b'{}'
        def close(self): closed.set()
    monkeypatch.setattr(direct, 'ERROR_BODY_WAIT_SECONDS', 0.05)
    error = urllib.error.HTTPError('https://invalid.example', 404, '', None, SlowBody())
    then = time.monotonic()
    try:
        assert direct.provider_404_reason(error, 'vendor/model') is None
        assert started.is_set() and time.monotonic() - then < 1
        second = urllib.error.HTTPError('https://invalid.example', 404, '', None, io.BytesIO(b'{}'))
        then = time.monotonic()
        assert direct.provider_404_reason(second, 'vendor/model') is None
        assert time.monotonic() - then < 0.5
    finally:
        release.set()
        assert closed.wait(2)


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
 assert.deepEqual(JSON.parse(post.opts.body),{agent:'direct',api_key:'fixture-key',model:'vendor/model:free',privacy:'zdr',provider:'openrouter'});
 reply(post,200,{phase:'starting',models:[],response:''});await running;
 reply(requests.shift(),200,{agents:[{id:'direct',name:'direct',installed:true}],sessions:{direct:{phase:'starting',models:[]}}});await tick();
 const loading=get('direct-model-load').listeners.click();const catalog=requests.shift();assert.equal(catalog.path,'/api/direct/models?privacy=zdr');
 reply(catalog,200,{models:[{id:'vendor/model:free',free:true}]});await loading;
 assert.equal(get('direct-model-options').children[1].value,'vendor/model:free');
 assert(!get('direct-model-options').disabled);get('direct-model-options').value='vendor/model:free';get('direct-model-options').listeners.change();
 assert.equal(get('direct-model').value,'vendor/model:free');
 get('direct-model').value='vendor/manual';get('direct-model').listeners.input();assert.equal(get('direct-model-options').value,'');
 get('direct-privacy').value='standard';get('direct-privacy').listeners.change();
 assert(get('direct-privacy-note').textContent.includes('可能'));assert(get('direct-model-options').disabled);assert.equal(get('direct-model-options').children.length,1);
 const loading2=get('direct-model-load').listeners.click();const catalog2=requests.shift();assert.equal(catalog2.path,'/api/direct/models?privacy=standard');
 reply(catalog2,200,{models:[{id:'vendor/ordinary:free',free:true}]});await loading2;
 assert.equal(get('direct-model-options').children[1].value,'vendor/ordinary:free');
 const stale=get('direct-model-load').listeners.click(), staleRequest=requests.shift();
 vm.runInContext("renderAgents({agents:[{id:'direct',installed:true}],sessions:{direct:{phase:'ready',privacy:'zdr',model:'vendor/model:free',models:[]}}})",ctx);
 assert.equal(get('direct-privacy').value,'zdr');assert(get('direct-model-options').disabled);
 vm.runInContext("renderAgents({agents:[{id:'direct',installed:true}],sessions:{direct:{phase:'ready',privacy:'standard',model:'vendor/ordinary:free',models:[]}}})",ctx);
 reply(staleRequest,200,{models:[{id:'vendor/stale',free:true}]});await stale;
 assert(get('direct-model-options').disabled);assert.equal(get('direct-model-options').children.length,1);
 vm.runInContext("renderAgents({agents:[{id:'direct',installed:true}],sessions:{direct:{phase:'ready',privacy:'standard',instance_id:'snapshot-id',provider:'openrouter',base_url:'',model:'vendor/ordinary:free',models:[]}}})",ctx);
 assert.equal(get('direct-model').value,'vendor/ordinary:free');
 get('direct-key').value='stale-key';
 vm.runInContext('directCredentials.use.checked=true',ctx);
 vm.runInContext("renderAgents({agents:[{id:'direct',installed:true}],sessions:{direct:{phase:'ready',privacy:'standard',instance_id:'new-id',provider:'deepseek',base_url:'',model:'deepseek-chat',models:[]}}})",ctx);
 assert(!vm.runInContext('directCredentials.use.checked',ctx));
 assert.equal(get('direct-model').value,'deepseek-chat');assert.equal(get('direct-provider').value,'deepseek');assert.equal(get('direct-key').value,'');
 vm.runInContext("renderAgents({agents:[{id:'direct',installed:true}],sessions:{direct:{phase:'ready',privacy:'standard',instance_id:'snapshot-id',provider:'openrouter',base_url:'',model:'vendor/ordinary:free',models:[]}}})",ctx);
 assert.equal(get('direct-privacy').value,'standard');assert(get('direct-privacy').disabled);
 assert(get('direct-privacy-note').textContent.includes('可能'));
 get('agent-prompt').value='hello';const sending=get('agent-prompt-form').listeners.submit({preventDefault(){}});
 const prompt=requests.shift();assert.deepEqual(JSON.parse(prompt.opts.body),{agent:'direct',text:'hello',instance_id:'snapshot-id',privacy:'standard',model:'vendor/ordinary:free',provider:'openrouter',base_url:''});
 reply(prompt,200,{phase:'running',privacy:'standard',instance_id:'snapshot-id',models:[]});await sending;
 reply(requests.shift(),200,{agents:[{id:'direct',installed:true}],sessions:{direct:{phase:'stopped',models:[]}}});await tick();
 vm.runInContext("renderAgents({agents:[{id:'direct',installed:true}],sessions:{direct:{phase:'stopped',models:[]}}})",ctx);
 get('direct-key').value='old-fixture-key';get('direct-provider').value='deepseek';get('direct-provider').listeners.change();
 assert.equal(get('direct-key').value,'');assert.equal(get('direct-privacy').value,'standard');
 assert(get('direct-privacy').disabled);assert(get('direct-model-load').disabled);
 assert(get('direct-privacy-note').textContent.includes('不提供'));
 get('direct-model-options').value='deepseek-flash';get('direct-model-options').listeners.change();
 assert.equal(get('direct-model').value,'deepseek-flash');
 get('direct-provider').value='custom';get('direct-provider').listeners.change();
 assert(!get('direct-base-field').hidden);get('direct-base-url').value='https://api.example.test/v1';
 get('direct-model').value='custom-model';get('direct-key').value='fixture-key';
 const customStart=get('agent-start').listeners.click(), customPost=requests.shift();
 assert.deepEqual(JSON.parse(customPost.opts.body),{agent:'direct',api_key:'fixture-key',model:'custom-model',privacy:'standard',provider:'custom',base_url:'https://api.example.test/v1'});
 assert.equal(get('direct-key').value,'');
 reply(customPost,200,{phase:'starting',provider:'custom',base_url:'https://api.example.test/v1',privacy:'standard',models:[]});await customStart;
 reply(requests.shift(),200,{agents:[{id:'direct',installed:true}],sessions:{direct:{phase:'ready',provider:'custom',base_url:'https://api.example.test/v1',privacy:'standard',models:[]}}});await tick();
 assert.equal(get('direct-provider').value,'custom');assert(get('direct-provider').disabled);
 vm.runInContext('directCredentials.use.checked=true',ctx);
 vm.runInContext("renderAgents({agents:[{id:'direct',installed:true}],sessions:{direct:{phase:'ready',privacy:'standard',provider:'custom',base_url:'https://other.example.test/v1',model:'custom-model',models:[]}}})",ctx);
 assert(!vm.runInContext('directCredentials.use.checked',ctx));
 assert.equal(get('direct-base-url').value,'https://other.example.test/v1');
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
    bridge.write_text('''import io,json,sys,time,urllib.error
sys.path.insert(0,sys.argv.pop(1))
from web import direct_model_bridge as bridge
bridge.ERROR_BODY_WAIT_SECONDS=0.05
def complete(key,model,messages,privacy='zdr',provider='openrouter',base_url=''):
    if messages[-1]['content']=='wait': time.sleep(60)
    if messages[-1]['content']=='fail': raise urllib.error.HTTPError('https://example.invalid',429,'private',None,None)
    if messages[-1]['content']=='privacy404':
        body=json.dumps({'error':{'message':'No endpoints found matching your data policy (Zero data retention).'}}).encode()
        raise urllib.error.HTTPError('https://example.invalid',404,'private',None,io.BytesIO(body))
    if messages[-1]['content']=='slow404':
        class Slow:
            def read(self, size): time.sleep(1); return b'{}'
            def close(self): pass
        raise urllib.error.HTTPError('https://example.invalid',404,'private',None,Slow())
    if messages[-1]['content']=='deep404':
        raise urllib.error.HTTPError('https://example.invalid',404,'private',None,io.BytesIO(b'[' * 8000 + b'0' + b']' * 8000))
    if messages[-1]['content']=='incomplete404':
        import http.client
        class Incomplete:
            def read(self, size): raise http.client.IncompleteRead(b'partial')
            def close(self): pass
        raise urllib.error.HTTPError('https://example.invalid',404,'private',None,Incomplete())
    if messages[-1]['content']=='unsafe404':
        body=json.dumps({'error':{'message':'private fixture-key https://secret.invalid'}}).encode()
        raise urllib.error.HTTPError('https://example.invalid',404,'private',None,io.BytesIO(body))
    return model+':'+str(len(messages))+(':'+privacy if privacy!='zdr' else '')+(':'+provider if provider!='openrouter' else ''), 'stop'
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
    assert request(console, '/api/agent/start', {**start, 'provider': 'deepseek', 'privacy': 'zdr'}, admin)[0] == 400
    assert request(console, '/api/agent/start', {**start, 'provider': 'custom', 'privacy': 'standard', 'base_url': 'http://example.test'}, admin)[0] == 400
    assert request(console, '/api/agent/start', {**start, 'provider': 'deepseek', 'privacy': 'standard', 'base_url': 'https://evil.test'}, admin)[0] == 400
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
            'instance_id': state['instance_id'], 'privacy': state['privacy'], 'model': state['model'],
            'provider': state['provider'], 'base_url': state['base_url']}, admin)[0]
    def stop(state):
        return request(console, '/api/agent/stop', {'agent': 'direct', 'instance_id': state['instance_id'],
            'provider': state['provider'], 'base_url': state['base_url']}, admin)[0]
    def select(state, model):
        return request(console, '/api/agent/model', {'agent': 'direct', 'model': model, 'instance_id': state['instance_id'],
            'privacy': state['privacy'], 'provider': state['provider'], 'base_url': state['base_url'], 'current_model': state['model']}, admin)[0]
    assert 'fixture-key' not in json.dumps(request(console, '/api/agents', session=admin)[1])
    assert request(console, '/api/agent/prompt', {'agent': 'direct', 'text': 'legacy'}, admin)[0] == 409
    assert prompt('wrong session', {**initial, 'instance_id': 'wrong'}) == 409
    assert prompt('x' * 40000, initial) == 200
    wait('ready', 'vendor/a:free:1')
    assert prompt('follow up', initial) == 200
    wait('ready', 'vendor/a:free:3')
    assert request(console, '/api/agent/model', {'agent': 'direct', 'model': 'vendor/b:free'}, admin)[0] == 409
    assert select(initial, 'vendor/b:free') == 200
    changed = wait('ready')
    assert changed['response'] == '' and changed['model'] == 'vendor/b:free'
    assert prompt('stale model', initial) == 409
    assert prompt('new model', changed) == 200
    wait('ready', 'vendor/b:free:1')
    assert prompt('fail', changed) == 200
    assert wait('ready')['error'] == 'Agent 請求失敗（HTTP 429）。'
    assert prompt('privacy404', changed) == 200
    assert wait('ready')['error'] == 'Agent 請求失敗（HTTP 404）。' + agent_control.DIRECT_404_REASONS['privacy_policy']
    assert prompt('unsafe404', changed) == 200
    fallback = 'Agent 請求失敗（HTTP 404）。無法安全辨識供應商原因；請檢查模型 ID、隱私政策與端點可用性。'
    assert wait('ready')['error'] == fallback
    for broken in ('deep404', 'incomplete404', 'slow404'):
        assert prompt(broken, changed) == 200
        assert wait('ready')['error'] == fallback
    assert prompt('still working', changed) == 200
    wait('ready', 'vendor/b:free:3')
    agent = console['app'].agent_sessions[admin['sid']]['direct']
    pid, created = agent.job.pid, agent.job.creation_time
    assert prompt('wait', changed) == 200
    assert request(console, '/api/agent/stop', {'agent': 'direct'}, admin)[0] == 409
    assert stop(changed) == 200
    assert request(console, '/api/agent/start', {**start, 'privacy': 'standard'}, admin)[0] == 200
    current = wait('ready')
    assert current['privacy'] == 'standard' and current['instance_id'] != initial['instance_id']
    assert request(console, '/api/agent/prompt', {'agent': 'direct', 'text': 'legacy'}, admin)[0] == 409
    assert prompt('stale ZDR tab', initial) == 409
    assert prompt('wrong privacy', {**current, 'privacy': 'zdr'}) == 409
    assert current['response'] == '' and prompt('hello', current) == 200
    wait('ready', 'vendor/a:free:1:standard')
    assert stop(current) == 200
    assert identity_state(pid, created) in ('missing', 'exited')
    for provider, base in [('deepseek',''), ('agnes',''), ('custom','https://api.example.test/v1')]:
        payload = {**start, 'provider':provider, 'privacy':'standard'}
        if base: payload['base_url'] = base
        assert request(console, '/api/agent/start', payload, admin)[0] == 200
        current = wait('ready')
        assert current['provider'] == provider and current['base_url'] == base and current['privacy'] == 'standard'
        assert 'fixture-key' not in json.dumps(current)
        legacy = {'agent':'direct', 'text':'legacy', 'instance_id':current['instance_id'], 'privacy':current['privacy'], 'model':current['model']}
        assert request(console, '/api/agent/prompt', legacy, admin)[0] == 409
        assert prompt('wrong provider', {**current, 'provider':'openrouter'}) == 409
        assert select(initial, 'vendor/b:free') == 409
        assert stop(initial) == 409
        assert prompt('hello', current) == 200
        wait('ready', 'vendor/a:free:1:standard:' + provider)
        assert stop(current) == 200
    monkeypatch.setattr(agent_control, 'DIRECT_PROMPT_TIMEOUT_SECONDS', .3)
    assert request(console, '/api/agent/start', start, admin)[0] == 200
    current = wait('ready')
    timed_agent = console['app'].agent_sessions[admin['sid']]['direct']
    timed_pid, timed_created = timed_agent.job.pid, timed_agent.job.creation_time
    assert prompt('wait', current) == 200
    assert '逾時' in wait('failed')['error']
    deadline = time.monotonic() + 5
    while identity_state(timed_pid, timed_created) not in ('missing', 'exited') and time.monotonic() < deadline: time.sleep(.05)
    assert identity_state(timed_pid, timed_created) in ('missing', 'exited')
    monkeypatch.setenv('COORDINATION_OPENROUTER_API_KEY', 'fixture-key')
    monkeypatch.setenv('COORDINATION_DIRECT_MODELS', 'vendor/a:free')
    assert request(console, '/api/agent/start', {'agent': 'direct'}, admin)[0] == 200
    current = wait('ready')
    assert stop(current) == 200


@pytest.mark.skipif(os.name != 'nt', reason='Windows owned Job')
def test_direct_prompt_timeout_stops_only_current_turn(monkeypatch):
    import threading
    session = agent_control.AgentSession.__new__(agent_control.AgentSession)
    session.agent = 'direct'; session.lock = threading.RLock(); session.closed = False
    session.phase = 'running'; session.turn = 2; session.prompt_timer = None
    cleaned = []; session._cleanup = lambda: cleaned.append(True)
    session._prompt_timeout(1)
    assert session.phase == 'running' and not cleaned
    session._prompt_timeout(2)
    assert session.phase == 'failed' and session.closed and cleaned
    assert '逾時' in session.error
