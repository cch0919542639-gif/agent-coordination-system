"""User-owned, bounded ACP sessions for installed local agents."""
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import sys
import threading
import time

from coordination_runtime.state_controller import StateError
from web.direct_model_bridge import model_ids, valid_key, valid_model
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from worker_process_guard import GuardError, JobProcess

AGENTS = {'opencode': 'OpenCode', 'hermes': 'Hermes', 'direct': '直接模型（OpenRouter）'}

DIRECT_404_REASONS = {
    'privacy_policy': '供應商表示沒有符合資料隱私政策的端點；請檢查零資料保留與帳號隱私設定，或選擇其他模型。',
    'data_region': '供應商表示沒有符合資料地區限制的端點；請檢查帳號或工作區的地區設定。',
    'price_limit': '供應商表示沒有符合價格上限的端點；請檢查帳號或請求的價格限制。',
    'model_not_found': '供應商找不到此模型 ID；請重新取得清單並確認模型是否停用或改名。',
    'no_endpoints': '供應商表示目前找不到此模型的可用端點；請檢查模型或路由設定後再試。',
}


def response_status(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ('status', 'statusCode', 'status_code') and type(item) is int and item in (400, 401, 403, 404, 408, 413, 429, 500, 502, 503, 504): return item
            found = response_status(item)
            if found: return found
    elif isinstance(value, list):
        for item in value:
            found = response_status(item)
            if found: return found
    elif isinstance(value, str):
        match = re.search(r'\bHTTP\s+(400|401|403|404|408|413|429|500|502|503|504)\b', value)
        if match: return int(match.group(1))
    return None


def executable(agent):
    if agent == 'opencode':
        # Prefer the desktop CLI which shares the user's native account store.
        folder = Path(os.environ.get('APPDATA', '')) / 'ai.opencode.desktop' / 'cli'
        candidates = []
        if folder.is_dir():
            for item in folder.iterdir():
                name = item.name.split('-')[0].split('.')
                if len(name) == 3 and all(x.isdigit() for x in name):
                    path = item / 'opencode-cli.exe'
                    if path.is_file() and int(name[0]) >= 2:
                        candidates.append((tuple(map(int, name)), path))
        return str(max(candidates)[1]) if candidates else None
    if agent == 'hermes':
        return shutil.which('hermes.exe')
    return None


def inventory():
    return [dict(id=k, name=v, installed=True, configured=bool(valid_key(os.environ.get('COORDINATION_OPENROUTER_API_KEY')) and model_ids()))
            if k == 'direct' else dict(id=k, name=v, installed=bool(executable(k))) for k, v in AGENTS.items()]


def models_from_result(result):
    """OpenCode config options and Hermes' legacy ACP session model state."""
    selected = None; choices = []; method = None
    for option in result.get('configOptions', []):
        if option.get('category') == 'model' or option.get('id') == 'model':
            selected = option.get('currentValue'); method = 'config'
            for item in option.get('options', []):
                for choice in item.get('options', [item]):
                    if isinstance(choice, dict):
                        choices.append((choice.get('value'), choice.get('name')))
            break
    if method is None and isinstance(result.get('models'), dict):
        state = result['models']; selected = state.get('currentModelId'); method = 'legacy'
        choices = [(x.get('modelId'), x.get('name')) for x in state.get('availableModels', []) if isinstance(x, dict)]
    unique = {}
    for value, name in choices[:512]:
        if isinstance(value, str) and 0 < len(value) <= 200 and isinstance(name, str) and len(name) <= 200:
            unique[value] = dict(id=value, name=name)
    return list(unique.values()), selected if selected in unique else None, method


class AgentSession:
    def __init__(self, agent, cwd, deadline=None, direct_config=None):
        self.agent = agent; self.cwd = str(cwd); self.lock = threading.RLock()
        self.direct_config = direct_config
        self.privacy = (direct_config or {}).get('privacy', 'zdr') if agent == 'direct' else None
        self.instance_id = secrets.token_urlsafe(24) if agent == 'direct' else None
        self.phase = 'starting'; self.error = None; self.models = []; self.model = None
        self.method = None; self.session = None; self.response = ''; self.activity = []; self.turn = 0
        self.permission = None; self.pending = {}; self.next_id = 1
        self.job = self.sock = self.listener = None; self.closed = False
        self.started = threading.Event()
        self.expiry = None
        if deadline is not None:
            self.expiry = threading.Timer(max(0, deadline - time.monotonic()), self.close)
            self.expiry.daemon = True; self.expiry.start()
        threading.Thread(target=self._run, daemon=True).start()

    def snapshot(self):
        with self.lock:
            return dict(agent=self.agent, phase=self.phase, error=self.error, privacy=self.privacy, instance_id=self.instance_id, models=list(self.models),
                        model=self.model, response=self.response, activity=list(self.activity),
                        permission=self.permission and {k: self.permission[k] for k in ('title', 'details', 'options')})

    def _send(self, value):
        raw = (json.dumps(value, ensure_ascii=False) + '\n').encode('utf-8')
        if len(raw) > (262144 if self.agent == 'direct' else 32768) or not self.sock: raise StateError('Agent connection unavailable.')
        self.sock.sendall(raw)

    def _request(self, method, params, kind, data=None):
        ident = self.next_id; self.next_id += 1
        self.pending[ident] = (kind, data)
        self._send(dict(jsonrpc='2.0', id=ident, method=method, params=params))

    def _run(self):
        try:
            binary = sys.executable if self.agent == 'direct' else executable(self.agent)
            if not binary: raise StateError('Agent is not installed.')
            with self.lock:
                if self.closed: return
                listener = socket.socket(); self.listener = listener
                listener.bind(('127.0.0.1', 0)); listener.listen(1); listener.settimeout(20)
                token = secrets.token_hex(32)
                bridge = ROOT / ('web/direct_model_bridge.py' if self.agent == 'direct' else 'web/agent_bridge.py')
                args = [sys.executable, '-B', str(bridge), str(listener.getsockname()[1]), token]
                if self.agent != 'direct': args.append(binary)
                self.job = JobProcess(args, cwd=self.cwd, pipe_stdin=True) if self.agent == 'direct' else JobProcess(args, cwd=self.cwd)
                self.job.resume()
                if self.agent == 'direct':
                    config = self.direct_config or {'key': os.environ.get('COORDINATION_OPENROUTER_API_KEY', ''), 'models': model_ids()}
                    self.direct_config = None
                    try:
                        self.job.stdin.write((json.dumps(config) + '\n').encode('utf-8'))
                    finally:
                        self.job.stdin.close()
                        del config
            sock, _ = listener.accept()
            with self.lock:
                if self.closed:
                    sock.close(); return
                self.sock = sock
            sock.settimeout(20)
            stream = sock.makefile('rb')
            if not hmac.compare_digest(stream.readline(130).decode('ascii').strip(), token):
                raise StateError('Agent bridge authentication failed.')
            sock.settimeout(None); listener.close(); self.listener = None
            with self.lock:
                self._request('initialize', {'protocolVersion': 1, 'clientCapabilities': {},
                    'clientInfo': {'name': 'coordination-console', 'version': '1'}}, 'init')
            # Bounded setup; the timer only interrupts sessions that never become ready.
            # Hermes can spend over 30 seconds validating configured providers.
            timer = threading.Timer(90 if self.agent == 'hermes' else 30, self._startup_timeout)
            timer.daemon = True; timer.start()
            try:
                while not self.closed:
                    raw = stream.readline(262145)
                    if not raw: break
                    if len(raw) > 262144 or not raw.endswith(b'\n'): raise StateError('Agent message exceeds limit.')
                    value = json.loads(raw)
                    if not isinstance(value, dict): raise StateError('Invalid agent response.')
                    self._message(value)
            finally:
                timer.cancel(); stream.close()
            with self.lock:
                if not self.closed and self.phase != 'failed':
                    self.phase = 'failed'; self.error = self.error or 'Agent 已結束；請重新連線。'
        except Exception:
            with self.lock:
                if not self.closed:
                    self.phase = 'failed'; self.error = self.error or 'Agent 無法啟動或連線；請檢查安裝與原生設定。'
        finally:
            self.direct_config = None
            self._cleanup()

    def _startup_timeout(self):
        with self.lock:
            if self.phase == 'starting':
                self.phase = 'failed'; self.error = 'Agent 連線逾時。'
                self._cleanup()

    def _message(self, msg):
        with self.lock:
            if getattr(self, 'closed', False) or self.phase == 'failed':
                return
            if 'method' in msg:
                method = msg.get('method'); params = msg.get('params') or {}
                if method == '_bridge/diagnostic' and isinstance(params, dict):
                    module = params.get('module')
                    if params.get('category') == 'compact_profile_unavailable':
                        self.error = 'Hermes 精簡工具設定無法啟用；請檢查安裝或版本。'
                    if params.get('category') == 'hermes_gateway_unsupported':
                        self.error = '新版 Hermes 使用共享後端；主控台尚未驗證其工具與審批保護，暫時無法連線。'
                    if params.get('category') == 'missing_module' and isinstance(module, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', module):
                        self.error = 'Agent 啟動環境缺少 Python 模組：' + module
                    return
                if method == 'session/update' and isinstance(params, dict):
                    update = params.get('update') or {}; kind = update.get('sessionUpdate')
                    if kind == 'agent_message_chunk':
                        content = update.get('content') or {}
                        if content.get('type') == 'text' and isinstance(content.get('text'), str):
                            self.response = (self.response + content['text'])[-30000:]
                    elif kind in ('tool_call', 'tool_call_update'):
                        title = update.get('title', 'Agent 操作'); status = update.get('status', '')
                        if isinstance(title, str) and isinstance(status, str):
                            self.activity = (self.activity + [dict(title=title[:300], status=status[:30])])[-30:]
                    elif kind == 'config_option_update' and isinstance(update.get('configOptions'), list):
                        if self.agent == 'hermes':
                            self.phase = 'failed'; self.error = '無法確認 Hermes 模型或提供者；工作階段已停止。'
                            self._cleanup()
                            return
                        self.models, self.model, self.method = models_from_result({'configOptions': update['configOptions']})
                    return
                if 'id' in msg and method == 'session/request_permission' and not self.permission:
                    choices = []
                    for option in params.get('options', [])[:16]:
                        if isinstance(option, dict) and option.get('kind') in ('allow_once', 'reject_once') and isinstance(option.get('optionId'), str):
                            choices.append(dict(id=option['optionId'][:100], kind=option['kind'], name=str(option.get('name', ''))[:100]))
                    if any(x['kind'] == 'reject_once' for x in choices):
                        tool = params.get('toolCall') or {}; title = tool.get('title', 'Agent 要求操作')
                        details = json.dumps({k: tool[k] for k in ('rawInput', 'locations', 'content') if k in tool}, ensure_ascii=False)
                        # A truncated operation is not reviewable, so only rejection remains.
                        if len(details) > 6000 or len(str(title)) > 1000:
                            details = details[:6000] + '\n…內容過長，請拒絕並在原生介面處理。'
                            choices = [x for x in choices if x['kind'] == 'reject_once']
                        self.permission = dict(request_id=msg['id'], title=str(title)[:1000], details=details, options=choices)
                        return
                if 'id' in msg:
                    self._send(dict(jsonrpc='2.0', id=msg['id'], error=dict(code=-32601, message='Unsupported request')))
                return
            pending = self.pending.pop(msg.get('id'), None)
            if not pending: return
            kind, supplied = pending
            if 'error' in msg:
                error = msg.get('error') or {}
                # Do not expose raw provider errors, which may contain credentials or paths.
                status = response_status(error)
                detail = '（HTTP ' + str(status) + '）' if status else ''
                if kind in ('model', 'prompt') and self.agent == 'hermes':
                    self.phase = 'failed'; self.error = 'Hermes 請求失敗或來源無法確認；工作階段已停止。'
                    self._cleanup()
                    return
                if self.session:
                    self.error = 'Agent 請求失敗' + detail + '。'
                    if self.agent == 'direct' and kind == 'prompt' and status == 404 and isinstance(error, dict):
                        reason = error.get('reason')
                        self.error += DIRECT_404_REASONS.get(reason, '') if isinstance(reason, str) else ''
                        if not isinstance(reason, str) or reason not in DIRECT_404_REASONS:
                            self.error += '無法安全辨識供應商原因；請檢查模型 ID、隱私政策與端點可用性。'
                else:
                    self.error = self.error or 'Agent 連線失敗' + detail + '；請稍候後重新連線。'
                self.phase = 'ready' if self.session else 'failed'
                if not self.session:
                    self._cleanup()
                return
            result = msg.get('result') or {}
            if kind == 'init':
                self._request('session/new', {'cwd': self.cwd, 'mcpServers': []}, 'new')
            elif kind == 'new':
                self.session = result.get('sessionId')
                if not isinstance(self.session, str) or len(self.session) > 200: raise StateError('Agent session missing.')
                self.models, self.model, self.method = models_from_result(result)
                meta = result.get('_meta')
                if self.agent == 'hermes' and (self.method != 'legacy' or not isinstance(meta, dict)
                        or meta.get('consoleRouteVerified') is not True or not self.model
                        or meta.get('accountVerified') is not False or meta.get('modelId') != self.model):
                    self.phase = 'failed'; self.error = '無法確認 Hermes 模型或提供者；工作階段已停止。'
                    self._cleanup()
                    return
                self.phase = 'ready'; self.started.set()
                if not self.models: self.error = 'Agent 沒有提供可選模型；請在原生介面檢查登入。'
            elif kind == 'model':
                if self.agent == 'hermes' and self.method != 'legacy':
                    self.phase = 'failed'; self.error = '無法確認 Hermes 模型或提供者；工作階段已停止。'
                    self._cleanup()
                    return
                if self.method == 'config':
                    models, current, method = models_from_result(result)
                    if method:
                        if self.agent == 'direct' and current == supplied and current != self.model:
                            self.response = ''; self.activity = []
                        self.models, self.model, self.method = models, current, method
                    self.error = None if current == supplied else 'Agent 未確認切換到指定模型。'
                else:
                    meta = result.get('_meta')
                    if (self.agent == 'hermes' and (not isinstance(meta, dict)
                            or meta.get('consoleRouteVerified') is not True or meta.get('accountVerified') is not False
                            or meta.get('modelId') != supplied)):
                        self.phase = 'failed'; self.error = '無法確認 Hermes 模型或提供者；工作階段已停止。'
                        self._cleanup()
                        return
                    self.model = supplied; self.error = None
                self.phase = 'ready'
            elif kind == 'prompt':
                self.phase = 'ready'; self.permission = None
                self.error = {'end_turn': None, 'refusal': 'Agent 拒絕了這次請求。',
                              'max_tokens': 'Agent 達到回覆長度上限，回覆可能不完整。',
                              'max_turn_requests': 'Agent 達到本次操作次數上限，回覆可能不完整。',
                              'cancelled': 'Agent 已取消這次請求。'}.get(
                                  result.get('stopReason'), 'Agent 未提供可辨識的結束原因。')

    def select(self, model):
        with self.lock:
            if self.phase != 'ready' or self.permission or not isinstance(model, str) or (not valid_model(model) if self.agent == 'direct' else model not in {x['id'] for x in self.models}): raise StateError('Choose an available model.')
            if self.agent == 'hermes' and self.method != 'legacy': raise StateError('Hermes model selection is not verified.')
            self.phase = 'switching'
            if self.method == 'config':
                self._request('session/set_config_option', dict(sessionId=self.session, configId='model', value=model), 'model', model)
            elif self.method == 'legacy':
                self._request('session/set_model', dict(sessionId=self.session, modelId=model), 'model', model)
            else: raise StateError('Model selection unavailable.')

    def prompt(self, text):
        with self.lock:
            limit = 50000 if self.agent == 'direct' else 8000
            if self.phase != 'ready' or not self.model or not isinstance(text, str) or not 1 <= len(text.strip()) <= limit: raise StateError('Agent is not ready.')
            parts = text.strip().split(maxsplit=1)
            if self.agent == 'hermes' and len(parts) > 1 and parts[0].startswith('/') and parts[0].lstrip('/').lower() == 'model':
                raise StateError('Use the model selector to switch Hermes models.')
            self.response = ''; self.activity = []; self.error = None; self.phase = 'running'; self.turn += 1
            self._request('session/prompt', dict(sessionId=self.session, prompt=[dict(type='text', text=text)]), 'prompt')

    def answer(self, choice):
        with self.lock:
            if not self.permission or not isinstance(choice, str) or choice not in {x['id'] for x in self.permission['options']}: raise StateError('Permission request expired.')
            self._send(dict(jsonrpc='2.0', id=self.permission['request_id'], result=dict(outcome=dict(outcome='selected', optionId=choice))))
            self.permission = None

    def close(self):
        if self.expiry is not None:
            self.expiry.cancel()
        with self.lock:
            self.closed = True; self.phase = 'stopped'; self.permission = None
        self._cleanup()

    def _cleanup(self):
        with self.lock:
            sock, job, listener = self.sock, self.job, self.listener
            self.sock = self.job = self.listener = None
        if sock:
            try: sock.shutdown(socket.SHUT_RDWR)
            except OSError: pass
            sock.close()
        if listener: listener.close()
        if job:
            try: job.stop()
            except GuardError:
                with self.lock: self.phase = 'failed'; self.error = '無法確認 Agent 程序已停止。'
            finally: job.close()
