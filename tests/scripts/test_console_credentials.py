"""Credential API uses synthetic keys and never returns them to the browser."""
import json
from pathlib import Path
import sys

sys.path[:0] = [str(Path(__file__).resolve().parents[2]), str(Path(__file__).resolve().parent)]
from test_parallel_runtime import system
from test_web_console import console, login, request
from web import credential_store


def test_credential_target_binds_user_project_provider_and_endpoint():
    base = credential_store.target('project-one','admin','custom','https://one.example/v1')
    assert base != credential_store.target('project-two','admin','custom','https://one.example/v1')
    assert base != credential_store.target('project-one','other','custom','https://one.example/v1')
    assert base != credential_store.target('project-one','admin','deepseek','https://one.example/v1')
    assert base != credential_store.target('project-one','admin','custom','https://two.example/v1')


def test_saved_credentials_are_scoped_and_never_returned(console, monkeypatch):
    store = {}
    monkeypatch.setattr(credential_store, 'save', lambda name, value: store.__setitem__(name, value))
    monkeypatch.setattr(credential_store, 'load', lambda name: store.get(name))
    monkeypatch.setattr(credential_store, 'delete', lambda name: store.pop(name, None))
    admin, viewer = login(console, 'administrator'), login(console, 'viewer')
    scope = {'provider':'custom', 'base_url':'https://one.example.test/v1'}
    save = {**scope, 'api_key':'synthetic-secret-key'}
    assert request(console, '/api/keys/save', save, viewer)[0] == 403
    code, result, _ = request(console, '/api/keys/save', save, admin)
    assert code == 200 and result == {'saved':True} and 'synthetic-secret-key' not in json.dumps(result)
    assert request(console, '/api/keys/status', scope, admin)[1] == {'saved':True}
    assert request(console, '/api/keys/status', {**scope,'base_url':'https://two.example.test/v1'}, admin)[1] == {'saved':False}
    assert request(console, '/api/keys/status', {'provider':'deepseek','base_url':''}, admin)[1] == {'saved':False}
    assert request(console, '/api/keys/save', {**save,'base_url':'http://one.example.test'}, admin)[0] == 400
    assert request(console, '/api/keys/save', {**save,'api_key':'bad\nkey'}, admin)[0] == 400
    assert request(console, '/api/keys/delete', scope, admin)[1] == {'saved':False}
    assert not store


def test_windows_credential_storage_round_trip(tmp_path):
    import os, subprocess, uuid, pytest
    if os.name != 'nt': pytest.skip('Windows Credential Manager')
    name = 'coordination-console-test/' + uuid.uuid4().hex
    try:
        credential_store.save(name, 'synthetic-key')
        assert credential_store.load(name) == 'synthetic-key'
        code = 'from web.credential_store import load; import sys; print(load(sys.argv[1]) == "synthetic-key")'
        result = subprocess.run([sys.executable, '-c', code, name], cwd=Path(__file__).resolve().parents[2],
                                capture_output=True, text=True, timeout=15, check=True)
        assert result.stdout.strip() == 'True'
    finally:
        credential_store.delete(name)
    assert credential_store.load(name) is None


def test_saved_keys_are_used_only_for_matching_direct_and_team_routes(console, monkeypatch):
    from web import api
    store, captured = {}, []
    monkeypatch.setattr(credential_store, 'save', lambda name, value: store.__setitem__(name, value))
    monkeypatch.setattr(credential_store, 'load', lambda name: store.get(name))
    class Agent:
        def __init__(self, name, root, direct_config=None): captured.append(direct_config)
        def snapshot(self): return {'phase':'starting'}
        def close(self): pass
    class Team:
        def __init__(self, root, task, configs): captured.extend(configs); self.instance_id='fixture'
        def snapshot(self): return {'phase':'done', 'instance_id':self.instance_id}
        def close(self): pass
    monkeypatch.setattr(api, 'AgentSession', Agent)
    monkeypatch.setattr(api, 'ModelTeam', Team)
    admin = login(console, 'administrator')
    for provider in ('deepseek','agnes'):
        assert request(console, '/api/keys/save', {'provider':provider,'base_url':'','api_key':'synthetic-'+provider}, admin)[0] == 200
    direct = {'agent':'direct','provider':'deepseek','base_url':'','privacy':'standard',
              'model':'fixture','api_key':'','use_saved':True}
    code, data, _ = request(console, '/api/agent/start', direct, admin)
    assert code == 200 and captured[-1]['key'] == 'synthetic-deepseek'
    assert 'synthetic-' not in json.dumps(data)
    worker = {'provider':'deepseek','base_url':'','privacy':'standard','model':'fixture','api_key':'','use_saved':True}
    second = {**worker,'provider':'agnes'}
    code, data, _ = request(console, '/api/team/start', {'task':'fixture','workers':[worker,second]}, admin)
    assert code == 200 and [c['key'] for c in captured[-2:]] == ['synthetic-deepseek','synthetic-agnes']
    assert 'synthetic-' not in json.dumps(data)
    assert request(console, '/api/team/start', {'task':'fixture','workers':[worker,{**worker,'provider':'custom','base_url':'https://other.example/v1'}]}, admin)[0] == 409
