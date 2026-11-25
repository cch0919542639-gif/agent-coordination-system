"""Team native work uses separate preserved Git worktrees and bound approvals."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

sys.path[:0] = [str(Path(__file__).resolve().parents[2]), str(Path(__file__).resolve().parent)]
from test_parallel_runtime import system
from test_web_console import console, login, request
from web import model_team
from web import team_workspace
from coordination_runtime.state_controller import StateError
import pytest


def test_native_workers_modify_distinct_worktrees_without_touching_dirty_source(console, monkeypatch):
    source = console['p'].root / 'src' / 'task-a.txt'
    source.write_text('existing uncommitted data', encoding='utf8')
    before = subprocess.check_output(['git', 'status', '--porcelain=v1', '--untracked-files=all'], cwd=console['p'].root)
    workers_barrier = threading.Barrier(2, timeout=4)
    class FakeAgent:
        def __init__(self, kind, cwd, direct_config=None):
            self.kind = kind; self.cwd = Path(cwd); self.phase = 'ready'; self.error = None
            self.response = ''; self.model = 'plan' if kind == 'direct' else kind + '/fixture'
        def snapshot(self): return dict(phase=self.phase, error=self.error, response=self.response, model=self.model)
        def prompt(self, text):
            self.phase = 'running'
            def run():
                if text.startswith('將以下總任務'): self.response = json.dumps(['review','write one','write two'])
                elif text.startswith('請根據以下'): self.response = 'summary'
                elif self.kind == 'direct': self.response = 'review complete'
                else:
                    workers_barrier.wait()
                    (self.cwd / 'src' / 'result.txt').write_text(self.kind, encoding='utf8')
                    self.response = self.kind + ' changed a file'
                self.phase = 'ready'
            threading.Thread(target=run, daemon=True).start()
        def close(self): self.phase = 'stopped'
    monkeypatch.setattr(model_team, 'AgentSession', FakeAgent)
    monkeypatch.setattr('web.api.executable', lambda kind: 'fixture.exe')
    admin = login(console, 'administrator')
    direct = dict(provider='deepseek',base_url='',privacy='standard',model='plan',api_key='fixture-key')
    workers = [direct, {'kind':'opencode','model':''}, {'kind':'opencode','model':''}]
    assert request(console, '/api/team/start', {'task':'write independent files','workers':workers}, admin)[0] == 400
    assert request(console, '/api/team/start', {'task':'write independent files','workers':workers,'workspace_ack':True}, admin)[0] == 200
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        state = request(console, '/api/agents', session=admin)[1]['team']
        if state['phase'] in ('done', 'failed', 'cleanup_failed'): break
        time.sleep(.05)
    assert state['phase'] == 'done', state
    paths = [Path(row['workspace']) for row in state['assignments'][1:]]
    assert paths[0] != paths[1] and all((p / 'src' / 'result.txt').read_text() == 'opencode' for p in paths)
    assert source.read_text(encoding='utf8') == 'existing uncommitted data'
    assert subprocess.check_output(['git', 'status', '--porcelain=v1', '--untracked-files=all'], cwd=console['p'].root) == before
    assert all((p / 'src' / 'task-a.txt').read_text() == 'base task-a' for p in paths)
    assert all('src/result.txt' in row['changes'] for row in state['assignments'][1:])
    assert state['base_sha']


def test_native_permission_is_bound_to_team_worker_and_operation(console, monkeypatch):
    class FakeAgent:
        def __init__(self, kind, cwd, direct_config=None):
            self.kind = kind; self.lock = threading.RLock(); self.permission = None
            self.phase = 'ready'; self.error = None; self.response = ''
            self.model = 'plan' if kind == 'direct' else 'hermes/fixture'
        def snapshot(self):
            with self.lock:
                permission = {k:self.permission[k] for k in ('title','details','options')} if self.permission else None
                return dict(phase=self.phase, error=self.error, response=self.response, model=self.model, permission=permission)
        def prompt(self, text):
            if text.startswith('將以下總任務'): self.response = json.dumps(['review','edit']); return
            if text.startswith('請根據以下'): self.response = 'summary'; return
            if self.kind == 'direct': self.response = 'review'; return
            with self.lock:
                self.phase = 'running'; self.permission = dict(token='approval-fixture', title='edit', details='fixture',
                    options=[dict(id='allow',kind='allow_once'),dict(id='deny',kind='reject_once')])
        def answer(self, choice):
            assert choice in ('allow', 'deny')
            self.permission = None; self.response = 'edited'; self.phase = 'ready'
        def close(self): self.phase = 'stopped'
    monkeypatch.setattr(model_team, 'AgentSession', FakeAgent)
    monkeypatch.setattr('web.api.executable', lambda kind: 'fixture.exe')
    monkeypatch.setattr('web.agent_bridge.agent_command', lambda binary: ['fixture'])
    admin, viewer = login(console, 'administrator'), login(console, 'viewer')
    direct = dict(provider='deepseek',base_url='',privacy='standard',model='plan',api_key='fixture-key')
    payload = {'task':'test editing','workers':[direct,{'kind':'hermes','model':''}], 'workspace_ack':True}
    assert request(console, '/api/team/start', payload, admin)[0] == 200
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        team = request(console, '/api/agents', session=admin)[1]['team']
        permission = team['assignments'][1]['permission']
        if permission: break
        time.sleep(.05)
    assert permission and permission['token'] == 'approval-fixture'
    body = dict(instance_id=team['instance_id'],index=1,token='approval-fixture',choice='allow')
    assert request(console, '/api/team/permission', body, viewer)[0] == 403
    assert request(console, '/api/team/permission', {**body,'token':'stale'}, admin)[0] == 409
    assert request(console, '/api/team/permission', body, admin)[0] == 200
    assert request(console, '/api/team/permission', body, admin)[0] == 409
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        team = request(console, '/api/agents', session=admin)[1]['team']
        if team['phase'] in ('done','failed'): break
        time.sleep(.05)
    assert team['phase'] == 'done', team


def test_unsupported_hermes_gateway_refuses_before_creating_workspace(console, tmp_path, monkeypatch):
    monkeypatch.setattr('web.api.executable', lambda kind: str(tmp_path / 'hermes.exe'))
    admin = login(console, 'administrator')
    direct = dict(provider='deepseek',base_url='',privacy='standard',model='plan',api_key='fixture-key')
    payload = {'task':'test','workers':[direct,{'kind':'hermes','model':''}], 'workspace_ack':True}
    code, data, _ = request(console, '/api/team/start', payload, admin)
    assert code == 409 and 'Hermes' in data['error']
    assert request(console, '/api/agents', session=admin)[1]['team'] is None
    assert not console['p'].workspace.root.exists()


def test_failed_native_work_preserves_and_reports_changes(console, monkeypatch):
    class FakeAgent:
        def __init__(self, kind, cwd, direct_config=None):
            self.kind = kind; self.cwd = Path(cwd); self.phase = 'ready'; self.error = None
            self.response = ''; self.model = 'plan' if kind == 'direct' else 'opencode/fixture'
        def snapshot(self): return dict(phase=self.phase,error=self.error,response=self.response,model=self.model)
        def prompt(self, text):
            if text.startswith('將以下總任務'): self.response = json.dumps(['review','edit']); return
            if text.startswith('請根據以下'): self.response = 'partial summary'; return
            if self.kind == 'direct': self.response = 'review'; return
            (self.cwd / 'partial.txt').write_text('retained', encoding='utf8')
            self.error = 'fixture failure'
        def close(self): self.phase = 'stopped'
    monkeypatch.setattr(model_team, 'AgentSession', FakeAgent)
    monkeypatch.setattr('web.api.executable', lambda kind: 'fixture.exe')
    admin = login(console, 'administrator')
    direct = dict(provider='deepseek',base_url='',privacy='standard',model='plan',api_key='fixture-key')
    payload = {'task':'edit','workers':[direct,{'kind':'opencode','model':''}], 'workspace_ack':True}
    assert request(console, '/api/team/start', payload, admin)[0] == 200
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        team = request(console, '/api/agents', session=admin)[1]['team']
        if team['phase'] in ('done','failed','cleanup_failed'): break
        time.sleep(.05)
    assert team['phase'] == 'failed'
    row = team['assignments'][1]
    assert row['phase'] == 'failed' and 'partial.txt' in row['changes']
    assert (Path(row['workspace']) / 'partial.txt').read_text(encoding='utf8') == 'retained'


def test_workspace_retains_existing_work_and_refuses_revision_changes(system):
    manager = system[0].workspace
    base = team_workspace.base_revision(manager)
    path = team_workspace.provision(manager, base, 'team-fixture-1')
    marker = path / 'src' / 'new-file.txt'; marker.write_text('retained', encoding='utf8')
    assert team_workspace.changes(manager, path, base) == ['src/new-file.txt']
    with pytest.raises(StateError): team_workspace.provision(manager, base, 'team-fixture-1')
    assert marker.read_text(encoding='utf8') == 'retained'
    with pytest.raises(StateError): team_workspace.changes(manager, path, '0' * 40)


@pytest.mark.skipif(os.environ.get('CODEX_REAL_OPENCODE_TEST') != '1', reason='explicit real OpenCode probe only')
def test_real_opencode_writes_only_fixture_worktree(system, monkeypatch):
    from web.agent_control import AgentSession as RealAgentSession
    p, _, _ = system
    before = subprocess.check_output(['git', 'status', '--porcelain=v1', '--untracked-files=all'], cwd=p.root)
    class Planner:
        def __init__(self): self.phase='ready'; self.response=''; self.model='fixture'; self.error=None
        def snapshot(self): return dict(phase=self.phase,response=self.response,error=self.error,model=self.model)
        def prompt(self, text):
            if text.startswith('將以下總任務'):
                self.response = json.dumps(['Review the test requirement in text only.',
                    'Create probe-team.txt in the current working directory containing exactly TEAM_NATIVE_OK; do not modify any other file.'])
            elif text.startswith('請根據以下'): self.response = 'Fixture summary.'
            else: self.response = 'Text review complete.'
        def close(self): self.phase = 'stopped'
    def factory(kind, cwd, direct_config=None):
        return Planner() if kind == 'direct' else RealAgentSession(kind, cwd)
    monkeypatch.setattr(model_team, 'AgentSession', factory)
    configs = [dict(kind='direct',provider='fixture',base_url='',privacy='standard',models=['fixture']),
               dict(kind='opencode',provider='opencode',base_url='',privacy='',models=[''])]
    team = model_team.ModelTeam(p.root, 'Create one synthetic marker file in the assigned worktree.', configs, workspace_manager=p.workspace)
    try:
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            state = team.snapshot()
            if state['phase'] in ('done', 'failed', 'cleanup_failed'): break
            time.sleep(.3)
        assert state['phase'] == 'done', state
        worker = state['assignments'][1]
        assert worker['changes'] == ['probe-team.txt']
        assert (Path(worker['workspace']) / 'probe-team.txt').read_text(encoding='utf8').strip() == 'TEAM_NATIVE_OK'
        assert not (p.root / 'probe-team.txt').exists()
        assert subprocess.check_output(['git', 'status', '--porcelain=v1', '--untracked-files=all'], cwd=p.root) == before
    finally:
        team.close()
