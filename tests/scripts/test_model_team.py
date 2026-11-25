"""Isolated end-to-end tests for bounded multi-model orchestration."""
import json
from pathlib import Path
import sys
import threading
import time

sys.path[:0] = [str(Path(__file__).resolve().parents[2]), str(Path(__file__).resolve().parent)]
from test_parallel_runtime import system
from test_web_console import console, login, request
from web import model_team


def test_team_plans_and_runs_workers_in_parallel_without_exposing_keys(console, monkeypatch):
    barrier = threading.Barrier(2, timeout=3)
    received = []
    class FakeAgent:
        def __init__(self, agent, root, direct_config):
            self.provider = direct_config['provider']; self.model = direct_config['models'][0]
            self.phase = 'ready'; self.error = None; self.response = ''; self.closed = False
        def snapshot(self): return dict(phase=self.phase, error=self.error, response=self.response)
        def prompt(self, text):
            received.append((self.provider, text))
            self.phase = 'running'; self.response = ''
            def finish():
                if text.startswith('將以下總任務'):
                    result = json.dumps(['first assignment', 'second assignment'])
                elif text.startswith('請根據以下'):
                    result = 'combined result'
                else:
                    barrier.wait(); result = 'result from ' + self.provider
                self.response = result; self.phase = 'ready'
            threading.Thread(target=finish, daemon=True).start()
        def close(self): self.closed = True
    monkeypatch.setattr(model_team, 'AgentSession', FakeAgent)
    admin, viewer = login(console, 'administrator'), login(console, 'viewer')
    workers = [dict(provider='openrouter',base_url='',privacy='zdr',model='openai/test',api_key='fixture-key-one'),
               dict(provider='deepseek',base_url='',privacy='standard',model='deepseek-flash',api_key='fixture-key-two')]
    payload = dict(task='Analyse the sample', workers=workers)
    assert request(console, '/api/team/start', payload, viewer)[0] == 403
    status, initial, _ = request(console, '/api/team/start', payload, admin)
    assert status == 200
    assert request(console, '/api/team/stop', {'instance_id':'stale'}, admin)[0] == 409
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        state = request(console, '/api/agents', session=admin)[1]['team']
        if state['phase'] in ('done','failed'): break
        time.sleep(.05)
    assert state['phase'] == 'done', state
    assert [row['task'] for row in state['assignments']] == ['first assignment','second assignment']
    assert [row['result'] for row in state['assignments']] == ['result from openrouter','result from deepseek']
    assert state['summary'] == 'combined result'
    assert 'fixture-key' not in json.dumps(state)
    assert len(received) == 4
    assert request(console, '/api/team/start', {**payload,'workers':[workers[0],{**workers[1],'privacy':'zdr'}]}, admin)[0] == 400


def test_team_stop_cancels_owned_sessions(console, monkeypatch):
    active = threading.Event()
    agents = []
    class FakeAgent:
        def __init__(self, agent, root, direct_config):
            self.phase = 'ready'; self.closed = False; agents.append(self)
        def snapshot(self): return dict(phase=self.phase, error=None, response='')
        def prompt(self, text): self.phase = 'running'; active.set()
        def close(self): self.closed = True; self.phase = 'stopped'
    monkeypatch.setattr(model_team, 'AgentSession', FakeAgent)
    admin = login(console, 'administrator')
    config = dict(provider='deepseek',base_url='',privacy='standard',model='deepseek-flash',api_key='fixture-key')
    status, started, _ = request(console, '/api/team/start', {'task':'test', 'workers':[config,config]}, admin)
    assert status == 200 and active.wait(3)
    assert request(console, '/api/team/stop', {'instance_id':started['instance_id']}, admin)[0] == 200
    assert all(agent.closed for agent in agents)
    assert request(console, '/api/agents', session=admin)[1]['team']['phase'] == 'stopped'


def test_invalid_plan_never_dispatches_workers(console, monkeypatch):
    prompts = []
    class FakeAgent:
        def __init__(self, agent, root, direct_config): self.phase = 'ready'; self.response = ''
        def snapshot(self): return dict(phase=self.phase, error=None, response=self.response)
        def prompt(self, text): prompts.append(text); self.response = '["only one assignment"]'
        def close(self): self.phase = 'stopped'
    monkeypatch.setattr(model_team, 'AgentSession', FakeAgent)
    admin = login(console, 'administrator')
    config = dict(provider='deepseek',base_url='',privacy='standard',model='deepseek-flash',api_key='fixture-key')
    assert request(console, '/api/team/start', {'task':'test', 'workers':[config,config]}, admin)[0] == 200
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        state = request(console, '/api/agents', session=admin)[1]['team']
        if state['phase'] == 'failed': break
        time.sleep(.05)
    assert state['phase'] == 'failed' and len(prompts) == 1
    assert not any(row['result'] for row in state['assignments'])


def test_one_dispatch_failure_preserves_other_result(console, monkeypatch):
    class FakeAgent:
        def __init__(self, agent, root, direct_config):
            self.provider = direct_config['provider']; self.phase = 'ready'; self.response = ''
        def snapshot(self): return dict(phase=self.phase, error=None, response=self.response)
        def prompt(self, text):
            if text.startswith('將以下總任務'): self.response = '["alpha", "beta"]'
            elif text.startswith('請根據以下'): self.response = 'partial summary'
            elif self.provider == 'deepseek': raise OSError('private transport details')
            else: self.response = 'first result'
        def close(self): self.phase = 'stopped'
    monkeypatch.setattr(model_team, 'AgentSession', FakeAgent)
    admin = login(console, 'administrator')
    workers = [dict(provider='openrouter',base_url='',privacy='zdr',model='one',api_key='fixture-key'),
               dict(provider='deepseek',base_url='',privacy='standard',model='two',api_key='fixture-key')]
    assert request(console, '/api/team/start', {'task':'test', 'workers':workers}, admin)[0] == 200
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        state = request(console, '/api/agents', session=admin)[1]['team']
        if state['phase'] == 'failed': break
        time.sleep(.05)
    assert state['phase'] == 'failed'
    assert state['assignments'][0]['phase'] == 'done' and state['assignments'][0]['result'] == 'first result'
    assert state['assignments'][1]['phase'] == 'failed' and state['assignments'][1]['error']
    assert 'private transport' not in json.dumps(state)
    assert state['summary'] == 'partial summary'


def test_unconfirmed_cleanup_blocks_new_team(console, monkeypatch):
    active = threading.Event()
    class FakeAgent:
        def __init__(self, agent, root, direct_config):
            self.phase = 'ready'; self.cleanup_failed = False
        def snapshot(self): return dict(phase=self.phase, error=None, response='')
        def prompt(self, text): self.phase = 'running'; active.set()
        def close(self): self.phase = 'failed'; self.cleanup_failed = True
    monkeypatch.setattr(model_team, 'AgentSession', FakeAgent)
    admin = login(console, 'administrator')
    config = dict(provider='deepseek',base_url='',privacy='standard',model='test',api_key='fixture-key')
    payload = {'task':'test', 'workers':[config,config]}
    _, started, _ = request(console, '/api/team/start', payload, admin)
    assert active.wait(3)
    code, stopped, _ = request(console, '/api/team/stop', {'instance_id':started['instance_id']}, admin)
    assert code == 200 and stopped['phase'] == 'cleanup_failed' and stopped['error']
    assert request(console, '/api/team/start', payload, admin)[0] == 503
    assert request(console, '/api/logout', {}, admin)[0] == 200
    fresh_admin = login(console, 'administrator')
    assert request(console, '/api/team/start', payload, fresh_admin)[0] == 503


def test_team_waits_for_inflight_agent_cleanup():
    class FakeAgent:
        def __init__(self):
            self.cleanup_done = threading.Event(); self.cleanup_failed = False
        def close(self): pass
    agent = FakeAgent()
    team = model_team.ModelTeam.__new__(model_team.ModelTeam)
    team.lock = threading.RLock(); team.cleanup_lock = threading.Lock()
    team.cleanup_finished = False; team.agents = [agent]
    team.phase = 'cleaning'; team.outcome = 'done'; team.error = None
    worker = threading.Thread(target=team.finish_cleanup)
    worker.start()
    time.sleep(.05)
    assert worker.is_alive() and team.phase == 'cleaning'
    agent.cleanup_failed = True; agent.cleanup_done.set()
    worker.join(2)
    assert not worker.is_alive() and team.phase == 'cleanup_failed'


def test_background_cleanup_non_guard_error_is_sticky():
    from web.agent_control import AgentSession
    class FakeJob:
        def stop(self): raise OSError('fixture')
        def close(self): pass
    agent = AgentSession.__new__(AgentSession)
    agent.lock = threading.RLock(); agent.cleanup_done = threading.Event(); agent.cleanup_done.set()
    agent.cleanup_failed = False; agent.prompt_timer = None
    agent.sock = agent.listener = None; agent.job = FakeJob()
    agent.phase = 'ready'; agent.error = None; agent.expiry = None; agent.closed = False
    agent._cleanup()
    assert agent.cleanup_done.is_set() and agent.cleanup_failed
    agent.close()
    assert agent.cleanup_failed


def test_team_frontend_submits_distinct_workers_and_hides_keys(tmp_path):
    import os
    import shutil
    import pytest
    from worker_process_guard import JobProcess
    if os.name != 'nt': pytest.skip('Windows owned Job')
    binary = shutil.which('node')
    if not binary: pytest.skip('Node required')
    script = tmp_path / 'team-ui.cjs'
    script.write_text(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class E { constructor(){this.children=[];this.listeners={};this.value='';this.hidden=false;this.disabled=false;this.dataset={};this.textContent='';} append(...a){this.children.push(...a)} replaceChildren(...a){this.children=a} addEventListener(n,f){this.listeners[n]=f} setAttribute(){} removeAttribute(){} focus(){} }
const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new E());return nodes.get(id)},requests=[];
const ctx={AbortController,Date,Set,Number,JSON,Error,document:{hidden:false,getElementById:get,createElement:()=>new E(),querySelectorAll:()=>[],addEventListener(){}},clearTimeout(){},setTimeout(){return 1},fetch(path,opts){return new Promise(resolve=>requests.push({path,opts,resolve}))}};
const reply=(req,status,body)=>req.resolve({ok:status===200,status,json:async()=>body});
(async()=>{get('action').value='resource.probe';vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),ctx);reply(requests.shift(),401,{});await new Promise(r=>setImmediate(r));
vm.runInContext("session={role:'administrator',csrf:'x'}; agentSnapshot={sessions:{},agents:[]}; renderTeam(null)",ctx);
vm.runInContext("teamRows[0].provider.value='openrouter';teamRows[0].privacy.value='zdr';teamRows[0].model.value='first';teamRows[0].key.value='key-one';teamRows[1].provider.value='deepseek';teamRows[1].privacy.value='standard';teamRows[1].model.value='second';teamRows[1].key.value='key-two'",ctx);
get('team-task').value='example task';const started=get('team-start').listeners.click();const post=requests.shift();assert.equal(post.path,'/api/team/start');const body=JSON.parse(post.opts.body);assert.equal(body.workers.length,2);assert.equal(body.workers[1].provider,'deepseek');
reply(post,200,{instance_id:'team',phase:'planning',assignments:[],summary:''});await started;
assert.equal(vm.runInContext('teamRows[0].key.value',ctx),'');assert.equal(vm.runInContext('teamRows[1].key.value',ctx),'');assert(get('team-start').disabled);console.log('team UI passed');
})().catch(e=>{console.error(e);process.exitCode=1});
''', encoding='utf-8')
    job = JobProcess([binary, str(script), str(Path(__file__).resolve().parents[2] / 'web/static/app.js')], cwd=tmp_path, capture_output=True)
    try:
        job.resume()
        assert job.wait(10) == 0 and job.wait_empty(3)
        assert b'team UI passed' in job.stdout.read()
    finally:
        job.close()


def test_team_with_real_owned_bridges_and_synthetic_provider(console, tmp_path, monkeypatch):
    import os
    import pytest
    from web import agent_control
    from worker_process_guard import identity_state
    if os.name != 'nt': pytest.skip('Windows owned Job')
    root = Path(__file__).resolve().parents[2]
    bridge = tmp_path / 'fake_team_bridge.py'
    bridge.write_text('''import json,sys\nsys.path.insert(0,sys.argv.pop(1))\nfrom web import direct_model_bridge as bridge\ndef complete(key,model,messages,privacy="zdr",provider="openrouter",base_url=""):\n    if provider == "openrouter" and len(messages) == 1: return json.dumps(["alpha","beta"]), "stop"\n    if provider == "openrouter" and len(messages) == 5: return "merged", "stop"\n    return "result-" + provider, "stop"\nbridge.complete=complete\nbridge.main()\n''', encoding='utf-8')
    original = agent_control.JobProcess
    identities = []
    def launch(args, **kwargs):
        assert 'fixture-key' not in ' '.join(args) and kwargs.get('pipe_stdin') is True
        args = [args[0], args[1], str(bridge), str(root), *args[3:]]
        job = original(args, **kwargs)
        identities.append((job.pid, job.creation_time))
        return job
    monkeypatch.setattr(agent_control, 'JobProcess', launch)
    admin = login(console, 'administrator')
    workers = [dict(provider='openrouter',base_url='',privacy='zdr',model='sample-one',api_key='fixture-key-one'),
               dict(provider='deepseek',base_url='',privacy='standard',model='sample-two',api_key='fixture-key-two')]
    assert request(console, '/api/team/start', {'task':'fixture task', 'workers':workers}, admin)[0] == 200
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        state = request(console, '/api/agents', session=admin)[1]['team']
        if state['phase'] in ('done', 'failed'): break
        time.sleep(.05)
    assert state['phase'] == 'done', state
    assert state['summary'] == 'merged'
    assert [x['result'] for x in state['assignments']] == ['result-openrouter', 'result-deepseek']
    deadline = time.monotonic() + 5
    while any(identity_state(pid, created) not in ('missing', 'exited') for pid, created in identities) and time.monotonic() < deadline:
        time.sleep(.05)
    assert len(identities) == 2 and all(identity_state(pid, created) in ('missing', 'exited') for pid, created in identities)
