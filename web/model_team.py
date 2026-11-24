"""Bounded text-only planning and parallel work using owned direct sessions."""
import json
import secrets
import re
import threading
import time

from .agent_control import AgentSession


class ModelTeam:
    def __init__(self, root, task, configs):
        self.lock = threading.RLock()
        self.cancelled = threading.Event()
        self.instance_id = secrets.token_urlsafe(24)
        self.phase = 'starting'
        self.error = None
        self.summary = ''
        self.assignments = [dict(provider=c['provider'], model=c['models'][0], task='', phase='starting', result='', error=None) for c in configs]
        self.agents = []
        self.root = root
        self.task = task
        self.configs = configs
        threading.Thread(target=self.run, daemon=True).start()

    def snapshot(self):
        with self.lock:
            return dict(instance_id=self.instance_id, phase=self.phase, error=self.error, summary=self.summary,
                        assignments=[dict(x) for x in self.assignments])

    def close(self):
        with self.lock:
            self.cancelled.set()
            agents = list(self.agents)
            if self.phase not in ('done', 'failed'): self.phase = 'stopped'
        for agent in agents:
            agent.close()

    def send(self, agent, text):
        with self.lock:
            if self.cancelled.is_set(): raise ValueError('stopped')
            agent.prompt(text)

    def wait_ready(self, agent):
        deadline = time.monotonic() + 125
        while not self.cancelled.wait(.1) and time.monotonic() < deadline:
            state = agent.snapshot()
            if state['phase'] == 'ready':
                if state['error']: raise ValueError(state['error'])
                return state
            if state['phase'] in ('failed', 'stopped'): raise ValueError(state['error'] or '模型工作階段已停止。')
        raise ValueError('模型工作階段已停止或逾時。')

    def run(self):
        try:
            for config in self.configs:
                with self.lock:
                    if self.cancelled.is_set(): return
                    agent = AgentSession('direct', self.root, direct_config=config)
                    self.agents.append(agent)
            self.configs = []
            for agent in self.agents: self.wait_ready(agent)
            with self.lock:
                if self.cancelled.is_set(): return
                self.phase = 'planning'
            planner = self.agents[0]
            self.send(planner, '將以下總任務拆成 ' + str(len(self.agents)) + ' 個可獨立並行的純文字子任務。只輸出 JSON 字串陣列，數量必須完全相同；不要宣稱可以操作電腦。總任務：\n' + self.task)
            raw = self.wait_ready(planner)['response']
            fenced = re.fullmatch(r'\s*```(?:json)?\s*(.*?)\s*```\s*', raw, re.DOTALL | re.IGNORECASE)
            parts = json.loads(fenced.group(1) if fenced else raw)
            if not isinstance(parts, list) or len(parts) != len(self.agents) or any(not isinstance(x, str) or not 1 <= len(x.strip()) <= 8000 for x in parts):
                raise ValueError('規劃模型未回傳有效的子任務清單。')
            with self.lock:
                if self.cancelled.is_set(): return
                self.phase = 'running'
                for row, part in zip(self.assignments, parts): row.update(task=part, phase='running')
            for agent, part in zip(self.agents, parts):
                self.send(agent, '這是分工中的獨立文字任務。請明確說明限制，不要聲稱執行了未執行的工具或操作。\n總任務：' + self.task + '\n你的子任務：' + part)
            def collect(i, agent):
                try:
                    state = self.wait_ready(agent)
                    if not state['response']: raise ValueError('模型沒有回覆。')
                    with self.lock: self.assignments[i].update(phase='done', result=state['response'])
                except Exception as exc:
                    with self.lock: self.assignments[i].update(phase='failed', error=str(exc)[:300])
            threads = [threading.Thread(target=collect, args=(i, agent), daemon=True) for i, agent in enumerate(self.agents)]
            for thread in threads: thread.start()
            for thread in threads: thread.join()
            if self.cancelled.is_set(): return
            with self.lock:
                if self.cancelled.is_set(): return
                self.phase = 'summarizing'
                rows = [dict(x) for x in self.assignments]
            if planner.snapshot()['phase'] == 'ready':
                try:
                    material = '\n'.join('模型 ' + str(i + 1) + '：' + ((row['result'][:4000] + (' [結果已截短，請查看完整結果]' if len(row['result']) > 4000 else '')) if row['phase'] == 'done' else '此子任務失敗') for i, row in enumerate(rows))
                    self.send(planner, '請根據以下子任務結果彙整總任務，明確指出缺漏及不確定性。不要宣稱工具或動作已執行。\n總任務：' + self.task + '\n結果：\n' + material)
                    summary = self.wait_ready(planner)['response']
                    if not summary: raise ValueError('empty summary')
                    with self.lock: self.summary = summary
                except Exception:
                    with self.lock: self.summary = '彙整失敗，請查看各模型的個別結果。'
            with self.lock:
                if not self.summary: self.summary = '彙整失敗，請查看各模型的個別結果。'
                if not self.cancelled.is_set(): self.phase = 'done' if all(x['phase'] == 'done' for x in self.assignments) and self.summary != '彙整失敗，請查看各模型的個別結果。' else 'failed'
        except Exception as exc:
            with self.lock:
                if not self.cancelled.is_set(): self.phase = 'failed'; self.error = '任務規劃或模型連線失敗；請檢查供應商、模型與設定。'
        finally:
            self.configs = []
            for agent in self.agents: agent.close()
