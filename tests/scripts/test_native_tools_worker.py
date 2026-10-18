import hashlib
import json
from pathlib import Path
import sys
import shutil
import subprocess

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import local_agent_loop as loop
import native_tools_worker as worker
from local_agent_loop import LoopError


def contract():
    return {'commands':[{'resolved_argv':['D:/acs/.venv/Scripts/python.exe','-m','pytest','test.py','-q']}]}


def agy_event(name,*,command=None,output=None,state='DONE',error=None):
    info={'parameters':{}}
    if command is not None:info['parameters']['CommandLine']=command
    if output is not None:info['output']=output
    if error is not None:info['error']=error
    return {'event':'step_update','step_update':{'step_type':'tool','state':state,'tool_name':name,'tool_info':info}}


def agy_trace():
    return [agy_event('view_file'),agy_event('replace_file_content'),
            agy_event('run_command',command='D:/acs/.venv/Scripts/python.exe -m pytest test.py -q',output='1 passed in 0.01s'),
            {'event':'result','result':{'status':'SUCCESS'}}]


def reasonix_trace():
    return [{'kind':'tool_result','tool':{'name':'read_file','args':'{}'}},
            {'kind':'tool_result','tool':{'name':'edit_file','args':'{}'}},
            {'kind':'tool_result','tool':{'name':'bash','args':json.dumps({'command':'D:/acs/.venv/Scripts/python.exe -m pytest test.py -q'}),'execution':{'exitCode':0}}},
            {'type':'result','subtype':'success','is_error':False,'permission_denials':[]}]


@pytest.mark.parametrize('runtime,events',[('antigravity',agy_trace()),('reasonix',reasonix_trace())])
def test_observed_native_file_edit_and_test(runtime,events):
    calls=worker.observe(runtime,'\n'.join(map(json.dumps,events)),contract())
    assert calls[-1]['command_index']==0 and calls[-1]['exit_code']==0
    assert all(set(c)<= {'tool','error','command_index','exit_code'} for c in calls)


@pytest.mark.parametrize('case',['narration','missing_edit','failed_test','unapproved_command','denial','readiness'])
def test_native_rejection_paths(case):
    events=reasonix_trace()
    if case=='narration':events=events[-1:]
    if case=='missing_edit':events.pop(1)
    if case=='failed_test':events[2]['tool']['execution']['exitCode']=1
    if case=='unapproved_command':events[2]['tool']['args']=json.dumps({'command':'git push origin main'})
    if case=='denial':events[-1]['permission_denials']=['bash']
    if case=='readiness':events[-1]['readiness']={'missing':['verification']}
    with pytest.raises(LoopError):worker.observe('reasonix','\n'.join(map(json.dumps,events)),contract())


def test_antigravity_failed_or_denied_command_is_not_success():
    events=agy_trace();events[2]['step_update']['tool_info']['output']='1 failed, 1 passed'
    with pytest.raises(LoopError):worker.observe('antigravity','\n'.join(map(json.dumps,events)),contract())


def test_error_with_passed_text_and_edit_after_test_cannot_pass():
    events=agy_trace();events[2]['step_update']['tool_info']['error']={'type':'TOOL_ERROR'}
    with pytest.raises(LoopError):worker.observe('antigravity','\n'.join(map(json.dumps,events)),contract())
    events=agy_trace();events.insert(-1,agy_event('replace_file_content'))
    with pytest.raises(LoopError):worker.observe('antigravity','\n'.join(map(json.dumps,events)),contract())
    events=reasonix_trace();events.insert(-1,{'kind':'tool_result','tool':{'name':'edit_file','args':'{}'}})
    with pytest.raises(LoopError):worker.observe('reasonix','\n'.join(map(json.dumps,events)),contract())
    events=agy_trace();events[-1]['result']['denied_actions']=[{'action':'write_file'}]
    with pytest.raises(LoopError):worker.observe('antigravity','\n'.join(map(json.dumps,events)),contract())


@pytest.mark.parametrize('text',['python test.py; git push','python test.py && echo x','python $(whoami)','python test.py\nother','python test.py > file'])
def test_shell_injection_cannot_match_contract(text):
    assert worker.normalized_command(text) is None


@pytest.mark.parametrize('original',[None,b'{"theme":"dark","permissions":{"deny":["command(git push)"],"allow":["read_file(existing)"]}}'])
def test_scoped_antigravity_grants_restore_original_bytes(tmp_path,original):
    path=tmp_path/'settings.json'
    if original is not None:path.write_bytes(original)
    with pytest.raises(RuntimeError,match='simulated'):
        with worker.antigravity_grants(['D:/acs/input.py'],['D:/acs/output.py'],['python -m pytest test.py'],path):
            config=json.loads(path.read_bytes())
            assert 'command(python -m pytest test.py)' in config['permissions']['allow']
            assert all('*' not in rule for rule in config['permissions']['allow'])
            if original:assert config['permissions']['deny']==['command(git push)']
            raise RuntimeError('simulated CLI failure')
    assert (path.read_bytes() if path.exists() else None)==original


def test_concurrent_settings_change_is_preserved(tmp_path):
    path=tmp_path/'settings.json';path.write_text('{}')
    with worker.antigravity_grants([],[],['python test.py'],path):
        updated=json.loads(path.read_text());updated['theme']='new';updated['permissions']['allow'].append('read_file(user-added)')
        path.write_text(json.dumps(updated))
    assert json.loads(path.read_text())=={'theme':'new','permissions':{'allow':['read_file(user-added)']}}


@pytest.mark.parametrize('original',[None,b'{"theme":"dark","permissions":{"allow":["read_file(user-owned)"]}}'])
def test_abrupt_process_death_recovers_original_permissions(tmp_path,original):
    path=tmp_path/'settings.json'
    if original is not None:path.write_bytes(original)
    scripts=Path(__file__).resolve().parents[2]/'scripts'
    program=(f'import sys,os;sys.path.insert(0,{str(scripts)!r});'
             'from pathlib import Path;from native_tools_worker import antigravity_grants;'
             f'lease=antigravity_grants([],[],["python approved.py"],Path({str(path)!r}));'
             'lease.__enter__();os._exit(0)')
    subprocess.run([sys.executable,'-c',program],check=True,timeout=15)
    journal=path.with_name('acs-worker-permission-lease.json')
    assert journal.exists() and 'command(python approved.py)' in path.read_text()
    with worker.antigravity_grants([],[],[],path):pass
    assert (path.read_bytes() if path.exists() else None)==original
    assert not journal.exists()


def test_contract_rejects_changed_or_worker_writable_checker(tmp_path,monkeypatch):
    monkeypatch.setattr(worker,'ROOT',tmp_path);monkeypatch.setattr(loop,'ROOT',tmp_path)
    test=tmp_path/'tests/test_result.py';test.parent.mkdir();test.write_text('assert True')
    name='coordination/plans/native.json';path=tmp_path/name;path.parent.mkdir(parents=True)
    value={'version':1,'runtime':'reasonix','read_paths':[], 'artifacts':['coordination/evidence/result.py'],
           'commands':[{'argv':['$PYTHON','-m','pytest','tests/test_result.py'],'pins':{'tests/test_result.py':worker.sha(test)}}]}
    path.write_text(json.dumps(value))
    header={'native_tool_contract':name,'native_tool_contract_sha256':worker.sha(path),
            'native_tool_evidence':'coordination/evidence/tools.json','allowed_scope':['coordination/evidence/*'],'forbidden_scope':[]}
    assert worker.load_contract(header,'reasonix')['runtime']=='reasonix'
    test.write_text('assert False')
    with pytest.raises(LoopError):worker.load_contract(header,'reasonix')
    test.write_text('assert True');header['allowed_scope'].append('tests/*')
    with pytest.raises(LoopError):worker.load_contract(header,'reasonix')


def test_reasonix_uses_session_grants_without_bypass(monkeypatch):
    monkeypatch.setattr(worker,'cli_command',lambda *_:['node','reasonix.js','-p','prompt','--output-format','json'])
    c=contract();c['artifacts']=['coordination/evidence/result.py']
    argv=worker.native_argv('reasonix','prompt',c)
    assert argv[argv.index('--permission-mode')+1]=='dontAsk'
    assert 'Bash(D:/acs/.venv/Scripts/python.exe -m pytest test.py -q)' in argv
    assert not any('yolo' in a.lower() or 'skip-permissions' in a for a in argv)


def test_fresh_native_plan_has_pinned_checks_and_keeps_duplicate_state(tmp_path):
    source=Path(__file__).resolve().parents[2]
    shutil.copytree(source/'scripts',tmp_path/'scripts',ignore=shutil.ignore_patterns('__pycache__'))
    argv=[sys.executable,str(tmp_path/'scripts/prepare_native_tools_loop.py'),'--run-id','native-test']
    result=subprocess.run(argv,capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['workers_launched']==0
    cards=list((tmp_path/'coordination/task-board/ready').glob('*.md'))
    from coordination_common import load_task
    native=[load_task(p)[0] for p in cards if load_task(p)[0].get('worker_execution')=='native_tools']
    assert len(native)==2
    hermes_body=next(load_task(p)[1] for p in cards if load_task(p)[0].get('owner')=='hermes-coordination-pilot')
    assert '"stage":2' in hermes_body and 'exact JSON value types' in hermes_body
    for h in native:
        contract_path=tmp_path/h['native_tool_contract']
        assert worker.sha(contract_path)==h['native_tool_contract_sha256']
        c=json.loads(contract_path.read_text())
        for name,expected in c['commands'][0]['pins'].items():assert worker.sha(tmp_path/name)==expected
        assert c['artifacts'][0] in h['allowed_scope']
        assert h['native_tool_evidence'] in h['allowed_scope']
    before={p.relative_to(tmp_path):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert subprocess.run(argv,capture_output=True,timeout=20).returncode!=0
    assert before=={p.relative_to(tmp_path):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
