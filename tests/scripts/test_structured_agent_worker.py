import importlib.util
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from local_agent_loop import LoopError
from structured_agent_worker import decode_result,validate_artifacts


def header():
    return {'structured_output_paths':['coordination/evidence/test/result.json'],
            'allowed_scope':['coordination/evidence/test/*'], 'forbidden_scope':[]}


def manifest(path='coordination/evidence/test/result.json',content='{"value":22}'):
    return {'summary':'Calculated dependency value plus one.', 'artifacts':[{'path':path,'content':content}]}


@pytest.mark.parametrize('runtime,envelope',[
    ('antigravity',{'status':'SUCCESS','response':json.dumps(manifest())}),
    ('reasonix',{'subtype':'success','is_error':False,'result':json.dumps(manifest())})])
def test_native_success_envelope(runtime,envelope):
    result=decode_result(runtime,json.dumps(envelope))
    validated=validate_artifacts(result,header())
    assert json.loads(next(iter(validated.values()))[1])=={'value':22}


@pytest.mark.parametrize('runtime,envelope',[
    ('antigravity',{'status':'ERROR','response':json.dumps(manifest())}),
    ('antigravity',{'status':'SUCCESS','denied_actions':['write'],'response':json.dumps(manifest())}),
    ('reasonix',{'subtype':'error','is_error':True,'result':json.dumps(manifest())}),
    ('reasonix',{'subtype':'success','is_error':False,'permission_denials':['shell'],'result':json.dumps(manifest())}),
    ('reasonix',{'subtype':'success','is_error':False,'result':'Narration only'})])
def test_cli_exit_zero_is_not_delivery(runtime,envelope):
    with pytest.raises(LoopError): decode_result(runtime,json.dumps(envelope))


@pytest.mark.parametrize('path',['../escape.json','D:/escape.json','coordination/evidence/test/../../reviews/x.md','scripts/check.py'])
def test_out_of_scope_outputs_rejected_before_writes(path):
    with pytest.raises(LoopError): validate_artifacts(manifest(path),header())


def test_forbidden_and_receipt_outputs_rejected():
    h=header(); h['forbidden_scope']=['coordination/evidence/**']
    with pytest.raises(LoopError): validate_artifacts(manifest(),h)
    h={'structured_output_paths':['coordination/plans/plan.json'],'allowed_scope':['coordination/**'],'forbidden_scope':[]}
    with pytest.raises(LoopError): validate_artifacts(manifest('coordination/plans/plan.json'),h)


def test_duplicate_or_missing_outputs_rejected():
    result=manifest(); result['artifacts']*=2
    with pytest.raises(LoopError): validate_artifacts(result,header())
    result=manifest(); result['artifacts']=[]
    with pytest.raises(LoopError): validate_artifacts(result,header())


@pytest.mark.parametrize('value,expected',[(True,True),('True',True),('true',True),(False,False),('False',False),('false',False),(None,False),(1,False),('yes',False)])
def test_explicit_processing_authorization(value,expected):
    from structured_agent_worker import external_authorized
    assert external_authorized({'external_processing_authorized':value}) is expected


def test_processing_authorization_survives_repository_frontmatter(tmp_path):
    from coordination_common import save_task,load_task
    from structured_agent_worker import external_authorized
    path=tmp_path/'task.md'
    save_task(path,{'external_processing_authorized':True},'# Synthetic task')
    assert external_authorized(load_task(path)[0])


def test_alias_cannot_resolve_to_coordination_control(monkeypatch):
    import structured_agent_worker as worker
    monkeypatch.setattr(worker,'relative_path',lambda name:worker.ROOT.resolve()/'coordination/plans/protected.json')
    with pytest.raises(LoopError): validate_artifacts(manifest(),header())


def test_case_variation_cannot_write_control_metadata():
    name='Coordination/Plans/protected.json'
    h={'structured_output_paths':[name],'allowed_scope':['**'],'forbidden_scope':[]}
    with pytest.raises(LoopError): validate_artifacts(manifest(name),h)


def test_resolved_aliases_cannot_deliver_duplicate_files(monkeypatch):
    import structured_agent_worker as worker
    monkeypatch.setattr(worker,'relative_path',lambda name:worker.ROOT.resolve()/'coordination/evidence/test/shared.json')
    h=header(); h['structured_output_paths'].append('coordination/evidence/test/alias.json')
    result=manifest();result['artifacts'].append({'path':'coordination/evidence/test/alias.json','content':'other'})
    with pytest.raises(LoopError): validate_artifacts(result,h)
