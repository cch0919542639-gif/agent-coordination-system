"""Parallel model teams using owned sessions and separate native worktrees."""
import json
import secrets
import re
import threading
import time

from .agent_control import AgentSession, DIRECT_404_REASONS
from .team_workspace import base_revision, changes, provision, run_id


def summary_failure(agent):
    """Publish only fixed categories; provider text and exception details stay private."""
    try:
        error = agent.snapshot().get('error')
    except Exception:
        return '彙整失敗，無法確認原因。'
    if error == '直接模型請求逾時；工作階段已停止，請重新連線。':
        return '彙整模型請求逾時；工作者結果已保留。'
    if error == '模型供應商連線逾時。':
        return '彙整模型供應商連線逾時；工作者結果已保留。'
    if error == '模型供應商連線失敗。':
        return '彙整模型供應商連線失敗；工作者結果已保留。'
    if error == 'Agent 達到回覆長度上限，回覆可能不完整。':
        return '彙整模型回覆達到長度上限；工作者結果已保留。'
    if error == 'Agent 拒絕了這次請求。':
        return '彙整模型拒絕了請求；工作者結果已保留。'
    if isinstance(error, str):
        match = re.match(r'^Agent 請求失敗（HTTP (400|401|403|404|408|413|429|500|502|503|504)）。', error)
        if match:
            status = int(match.group(1))
            if status == 404:
                prefix = 'Agent 請求失敗（HTTP 404）。'
                for known in DIRECT_404_REASONS.values():
                    if error == prefix + known:
                        return '彙整模型請求失敗（HTTP 404）。' + known
            hint = ('請檢查額度或稍後再試。' if status == 429 else
                    '請檢查授權與金鑰。' if status in (401, 403) else
                    '請檢查模型、隱私設定與端點。' if status == 404 else
                    '請檢查請求或供應商服務狀態。')
            return '彙整模型請求失敗（HTTP ' + str(status) + '）；' + hint
    return '彙整失敗，無法確認原因；工作者結果已保留。'


class ModelTeam:
    def __init__(self, root, task, configs, workspace_manager=None, workspace_base=None):
        self.lock = threading.RLock()
        self.cancelled = threading.Event()
        self.cleanup_lock = threading.Lock()
        self.cleanup_finished = False
        self.provisioning = False
        self.outcome = None
        self.instance_id = secrets.token_urlsafe(24)
        self.phase = 'starting'
        self.error = None
        self.summary = ''
        self.assignments = [dict(kind=c.get('kind', 'direct'), provider=c['provider'], base_url=c['base_url'], privacy=c['privacy'], model=c['models'][0], workspace='', changes=[], activity=[], permission=None, task='', phase='starting', result='', error=None) for c in configs]
        self.agents = []
        self.root = root
        self.workspace_manager = workspace_manager
        self.workspace_base = workspace_base
        self.base_sha = None
        self.task = task
        self.configs = configs
        threading.Thread(target=self.run, daemon=True).start()

    def snapshot(self):
        with self.lock:
            return dict(instance_id=self.instance_id, phase=self.phase, error=self.error, summary=self.summary, base_sha=self.base_sha,
                        assignments=[dict(x) for x in self.assignments])

    def close(self):
        with self.lock:
            self.cancelled.set()
            if not self.cleanup_finished:
                self.outcome = 'stopped'; self.phase = 'stopping'
        self.finish_cleanup()

    def finish_cleanup(self):
        with self.cleanup_lock:
            if self.cleanup_finished: return
            failed = False; workspace_error = False
            for i, agent in enumerate(self.agents):
                try:
                    agent.close()
                    done = getattr(agent, 'cleanup_done', None)
                    if (done is not None and not done.wait(10)) or getattr(agent, 'cleanup_failed', False):
                        failed = True
                        continue
                    row = self.assignments[i]
                    if row['kind'] != 'direct' and row['workspace']:
                        try:
                            paths = changes(self.workspace_manager, row['workspace'], self.base_sha)
                            with self.lock: row['changes'] = paths
                        except Exception:
                            workspace_error = True
                            with self.lock: row['error'] = '無法確認工作目錄的版本或變更，請人工檢查。'
                except Exception:
                    failed = True
            with self.lock:
                if getattr(self, 'provisioning', False) and not failed:
                    self.phase = 'stopping'
                    return
                self.cleanup_finished = True
                if failed:
                    self.phase = 'cleanup_failed'; self.error = '無法確認模型程序已停止，請檢查主控台程序。'
                elif workspace_error:
                    self.phase = 'failed'; self.error = '工作目錄驗證失敗，請人工檢查保留的成果。'
                else:
                    self.phase = self.outcome or 'failed'

    def send(self, agent, text):
        with self.lock:
            if self.cancelled.is_set(): raise ValueError('stopped')
            agent.prompt(text)

    def answer(self, index, token, choice):
        with self.lock:
            if (self.cancelled.is_set() or type(index) is not int or index < 0
                    or index >= len(self.agents) or not isinstance(token, str)):
                raise ValueError('Expired permission.')
            agent = self.agents[index]
            with agent.lock:
                if not agent.permission or agent.permission.get('token') != token:
                    raise ValueError('Expired permission.')
                agent.answer(choice)

    @staticmethod
    def stop_worker(agent):
        agent.close()
        done = getattr(agent, 'cleanup_done', None)
        if (done is not None and not done.wait(10)) or getattr(agent, 'cleanup_failed', False):
            raise ValueError('無法確認 Agent 程序已停止。')

    def wait_ready(self, agent):
        deadline = time.monotonic() + 125
        while not self.cancelled.wait(.1) and time.monotonic() < deadline:
            state = agent.snapshot()
            if state['phase'] == 'ready':
                if state['error']: raise ValueError(state['error'])
                return state
            if state['phase'] in ('failed', 'stopped'): raise ValueError(state['error'] or '模型工作階段已停止。')
        raise ValueError('模型工作階段已停止或逾時。')

    def wait_worker(self, index, agent):
        while not self.cancelled.wait(.1):
            state = agent.snapshot()
            if state.get('permission'):
                with agent.lock:
                    state = agent.snapshot()
                    if state.get('permission') and agent.permission:
                        state['permission']['token'] = agent.permission['token']
            with self.lock:
                self.assignments[index]['activity'] = state.get('activity') or []
                self.assignments[index]['permission'] = state.get('permission')
            if state['phase'] == 'ready':
                if state['error']: raise ValueError(state['error'])
                return state
            if state['phase'] in ('failed', 'stopped'):
                raise ValueError(state['error'] or '模型工作階段已停止。')
        raise ValueError('任務已停止。')

    def run(self):
        try:
            if any(c.get('kind', 'direct') != 'direct' for c in self.configs):
                if self.workspace_manager is None: raise ValueError('工作區未設定。')
                self.base_sha = self.workspace_base or base_revision(self.workspace_manager)
                self.workspace_manager.pinned(self.base_sha)
            requested_models = [c['models'][0] for c in self.configs]
            for i, config in enumerate(self.configs):
                kind = config.get('kind', 'direct')
                if kind != 'direct':
                    identifier = run_id(i)
                    with self.lock:
                        if self.cancelled.is_set(): return
                        self.assignments[i]['workspace'] = str(self.workspace_manager.path(identifier))
                        self.provisioning = True
                    try: path = provision(self.workspace_manager, self.base_sha, identifier)
                    except Exception:
                        with self.lock:
                            self.assignments[i].update(phase='failed', error='無法建立或確認工作目錄；已建立的資料會保留。')
                        raise
                    finally:
                        with self.lock: self.provisioning = False
                with self.lock:
                    if self.cancelled.is_set(): return
                    if kind == 'direct':
                        agent = AgentSession('direct', self.root, direct_config=config)
                    else:
                        agent = AgentSession(kind, path)
                    self.agents.append(agent)
            self.configs = []
            del config
            for i, agent in enumerate(self.agents):
                try:
                    state = self.wait_ready(agent)
                    requested = requested_models[i]
                    if self.assignments[i]['kind'] != 'direct' and requested and requested != state.get('model'):
                        agent.select(requested)
                        state = self.wait_ready(agent)
                        if state['model'] != requested: raise ValueError('Agent 未確認指定模型。')
                    with self.lock: self.assignments[i].update(model=state.get('model') or requested, phase='ready')
                except Exception:
                    with self.lock:
                        self.assignments[i].update(phase='failed', error=agent.snapshot().get('error') or '工作者未能啟動或確認指定模型。')
                    raise
            with self.lock:
                if self.cancelled.is_set(): return
                self.phase = 'planning'
            planner = self.agents[0]
            abilities = ', '.join('模型 ' + str(i + 1) + (' 可在獨立工作目錄使用工具' if row['kind'] != 'direct' else ' 僅能文字回覆') for i, row in enumerate(self.assignments))
            self.send(planner, '將以下總任務拆成 ' + str(len(self.agents)) + ' 個可獨立並行的子任務，依各模型能力分配，並避免它們修改同一項成果。只輸出 JSON 字串陣列，順序與模型相同、數量必須完全相同。能力：' + abilities + '\n總任務：\n' + self.task)
            raw = self.wait_ready(planner)['response']
            fenced = re.fullmatch(r'\s*```(?:json)?\s*(.*?)\s*```\s*', raw, re.DOTALL | re.IGNORECASE)
            parts = json.loads(fenced.group(1) if fenced else raw)
            if (not isinstance(parts, list) or len(parts) != len(self.agents)
                    or any(not isinstance(x, str) or not 1 <= len(x.strip()) <= (3500 if row['kind'] != 'direct' else 8000)
                           for x, row in zip(parts, self.assignments))):
                raise ValueError('規劃模型未回傳有效的子任務清單。')
            with self.lock:
                if self.cancelled.is_set(): return
                self.phase = 'running'
                for row, part in zip(self.assignments, parts): row.update(task=part, phase='pending')
            submitted = []
            for i, (agent, part) in enumerate(zip(self.agents, parts)):
                try:
                    instruction = ('這是分工中的獨立任務。僅在目前工作目錄操作，不要執行 git commit、merge 或 push。回報實際變更及測試；不要聲稱執行了未執行的操作。' if self.assignments[i]['kind'] != 'direct' else '這是分工中的獨立文字任務。請明確說明限制，不要聲稱執行了未執行的工具或操作。')
                    self.send(agent, instruction + '\n總任務：' + self.task + '\n你的子任務：' + part)
                except Exception:
                    if self.cancelled.is_set(): return
                    paths = []
                    if self.assignments[i]['kind'] != 'direct':
                        try:
                            self.stop_worker(agent)
                            paths = changes(self.workspace_manager, self.assignments[i]['workspace'], self.base_sha)
                        except Exception: pass
                    with self.lock: self.assignments[i].update(phase='failed', error='無法送出子任務。', changes=paths)
                else:
                    with self.lock: self.assignments[i]['phase'] = 'running'
                    submitted.append((i, agent))
            def collect(i, agent):
                try:
                    state = self.wait_worker(i, agent)
                    if not state['response']: raise ValueError('模型沒有回覆。')
                    if self.assignments[i]['kind'] != 'direct': self.stop_worker(agent)
                    paths = changes(self.workspace_manager, self.assignments[i]['workspace'], self.base_sha) if self.assignments[i]['kind'] != 'direct' else []
                    with self.lock: self.assignments[i].update(phase='done', result=state['response'], changes=paths)
                except Exception as exc:
                    paths = []
                    if self.assignments[i]['kind'] != 'direct':
                        try:
                            self.stop_worker(agent)
                            paths = changes(self.workspace_manager, self.assignments[i]['workspace'], self.base_sha)
                        except Exception: pass
                    with self.lock: self.assignments[i].update(phase='failed', error=str(exc)[:300], changes=paths)
            threads = [threading.Thread(target=collect, args=(i, agent), daemon=True) for i, agent in submitted]
            for thread in threads: thread.start()
            for thread in threads: thread.join()
            if self.cancelled.is_set(): return
            with self.lock:
                if self.cancelled.is_set(): return
                self.phase = 'summarizing'
                rows = [dict(x) for x in self.assignments]
            summary_ok = False
            if planner.snapshot()['phase'] == 'ready':
                try:
                    material = '\n'.join('模型 ' + str(i + 1) + '：' + ((row['result'][:4000] + (' [結果已截短，請查看完整結果]' if len(row['result']) > 4000 else '')) if row['phase'] == 'done' else '此子任務失敗') for i, row in enumerate(rows))
                    instruction = ('請區分工作者回報與你無法自行查證的事項，不要虛構已執行的工具或操作。' if any(row['kind'] != 'direct' for row in rows) else '不要宣稱工具或動作已執行。')
                    self.send(planner, '請根據以下子任務結果彙整總任務，明確指出缺漏及不確定性。' + instruction + '\n總任務：' + self.task + '\n結果：\n' + material)
                    summary = self.wait_ready(planner)['response']
                    if not summary or summary == '彙整失敗，請查看各模型的個別結果。': raise ValueError('invalid summary')
                    with self.lock:
                        if self.cancelled.is_set(): return
                        self.summary = summary
                    summary_ok = True
                except Exception:
                    reason = summary_failure(planner)
                    with self.lock:
                        if self.cancelled.is_set(): return
                        self.summary = '彙整失敗，請查看各模型的個別結果。'
                        self.error = reason
            with self.lock:
                if self.cancelled.is_set(): return
                if not self.summary:
                    self.summary = '彙整失敗，請查看各模型的個別結果。'
                    self.error = '彙整模型已停止或尚未就緒，未執行彙整；工作者結果已保留。'
                self.outcome = 'done' if all(x['phase'] == 'done' for x in self.assignments) and summary_ok else 'failed'
                self.phase = 'cleaning'
        except Exception as exc:
            with self.lock:
                if not self.cancelled.is_set(): self.outcome = 'failed'; self.phase = 'cleaning'; self.error = '任務規劃或模型連線失敗；請檢查供應商、模型與設定。'
        finally:
            self.configs = []
            self.finish_cleanup()
