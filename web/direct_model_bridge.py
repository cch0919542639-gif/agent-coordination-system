"""Owned text-only OpenRouter session; no tools, retries, or provider fallback policy changes."""
import http.client
import json
import os
import re
import queue
import socket
import sys
import threading
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ENDPOINT = 'https://openrouter.ai/api/v1/chat/completions'
CATALOG = 'https://openrouter.ai/api/v1/endpoints/zdr'
MODELS = 'https://openrouter.ai/api/v1/models'
PROVIDERS = {'openrouter': 'https://openrouter.ai/api/v1',
             'deepseek': 'https://api.deepseek.com',
             'agnes': 'https://apihub.agnes-ai.com/v1'}

# ponytail: at most one abandoned error-body reader per bridge process.
_error_reader_slot = threading.BoundedSemaphore(1)
ERROR_BODY_WAIT_SECONDS = 2


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def valid_model(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}', value))


def valid_key(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[!-~]{1,512}', value))


def provider_endpoint(provider, base_url='', privacy='zdr'):
    """Resolve a session-bound HTTPS endpoint; never accept embedded credentials."""
    if not isinstance(provider, str) or not isinstance(base_url, str) or privacy not in ('zdr', 'standard'):
        raise ValueError('invalid provider or privacy')
    if provider == 'openrouter':
        if base_url: raise ValueError('unexpected custom endpoint')
        return PROVIDERS[provider]
    if privacy != 'standard':
        raise ValueError('zero retention routing is only available on OpenRouter')
    if provider in PROVIDERS:
        if base_url: raise ValueError('unexpected custom endpoint')
        return PROVIDERS[provider]
    if provider != 'custom' or not isinstance(base_url, str) or not 1 <= len(base_url) <= 512:
        raise ValueError('invalid custom endpoint')
    if any(ord(c) <= 32 or ord(c) >= 127 for c in base_url) or any(c in base_url for c in '\\?#'):
        raise ValueError('invalid custom endpoint')
    try:
        parts = urlsplit(base_url)
        if (parts.scheme != 'https' or not parts.hostname or parts.username is not None or
                parts.password is not None or parts.query or parts.fragment or
                parts.port == 0 or not re.fullmatch(r'/[A-Za-z0-9._~/-]*|', parts.path)):
            raise ValueError('invalid custom endpoint')
    except ValueError:
        raise ValueError('invalid custom endpoint') from None
    return base_url.rstrip('/')


def model_ids():
    values = os.environ.get('COORDINATION_DIRECT_MODELS', '').split(',')
    return list(dict.fromkeys(v for x in values if valid_model(v := x.strip())))[:32]


def catalog(opener=None, privacy='zdr'):
    if privacy not in ('zdr', 'standard'):
        raise ValueError('invalid privacy mode')
    if opener is None:
        opener = urllib.request.build_opener(NoRedirect()).open
    def read(url):
        with opener(url, timeout=15) as response:
            raw = response.read(4194305)
        if len(raw) > 4194304:
            raise ValueError('catalog too large')
        rows = json.loads(raw)['data']
        if not isinstance(rows, list) or len(rows) > 10000:
            raise ValueError('invalid catalog')
        return rows
    allowed = {row['model_id'] for row in read(CATALOG)
               if isinstance(row, dict) and valid_model(row.get('model_id'))} if privacy == 'zdr' else None
    result = {}
    for row in read(MODELS):
        if not isinstance(row, dict):
            continue
        model = row.get('id')
        architecture = row.get('architecture')
        if (valid_model(model) and isinstance(architecture, dict)
                and 'text' in (architecture.get('input_modalities') or [])
                and 'text' in (architecture.get('output_modalities') or [])
                and (allowed is None or model in allowed)):
            result[model] = {'id': model, 'free': model.endswith(':free')}
    if len(result) > 2000:
        raise ValueError('catalog too large')
    return sorted(result.values(), key=lambda x: x['id'])


def complete(key, model, messages, opener=None, privacy='zdr', provider='openrouter', base_url=''):
    endpoint = provider_endpoint(provider, base_url, privacy) + '/chat/completions'
    payload = {'model': model, 'messages': messages, 'max_tokens': 4096}
    if provider == 'openrouter' and privacy == 'zdr':
        payload['provider'] = {'zdr': True, 'data_collection': 'deny'}
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    request = urllib.request.Request(endpoint, data=body, method='POST',
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    if opener is None:
        opener = urllib.request.build_opener(NoRedirect()).open
    with opener(request, timeout=90) as response:
        raw = response.read(1048577)
    if len(raw) > 1048576:
        raise ValueError('response too large')
    choice = json.loads(raw)['choices'][0]
    text = choice['message'].get('content')
    if not isinstance(text, str) or not text.strip() or len(text) > 30000:
        raise ValueError('empty or oversized response')
    return text, choice.get('finish_reason')


def provider_404_reason(error, model):
    """Map known bounded OpenRouter messages to fixed non-sensitive codes."""
    if not isinstance(error, urllib.error.HTTPError) or error.code != 404:
        return None
    if not _error_reader_slot.acquire(blocking=False):
        return None
    result = queue.Queue(maxsize=1)
    def read_body():
        try:
            raw = error.read(16385)
        except Exception:
            raw = None
        finally:
            try:
                error.close()
            except Exception:
                pass
            _error_reader_slot.release()
        result.put_nowait(raw)
    try:
        threading.Thread(target=read_body, daemon=True).start()
    except Exception:
        _error_reader_slot.release()
        return None
    try:
        raw = result.get(timeout=ERROR_BODY_WAIT_SECONDS)
        if not isinstance(raw, bytes) or len(raw) > 16384:
            return None
        data = json.loads(raw)
        message = data['error']['message']
        if not isinstance(message, str):
            return None
    except (ValueError, TypeError, KeyError, OSError, AttributeError, RecursionError, http.client.HTTPException, queue.Empty):
        return None
    # Only complete known messages are recognized; never forward provider text.
    if message in (
        'No endpoints found matching your data policy (Zero data retention).',
        'No endpoints found matching your data policy (Zero data retention). Configure: https://openrouter.ai/settings/privacy',
        'No endpoints found matching your data policy.',
        'No endpoints found matching your data policy. Configure: https://openrouter.ai/settings/privacy',
    ):
        return 'privacy_policy'
    if message == 'No endpoints found supporting your data region.':
        return 'data_region'
    if message == 'No endpoints found that satisfy the max price for this request':
        return 'price_limit'
    if message in (f'{model} is not a valid model ID', f'{model} is not a valid model ID.',
                   f'No model found for "{model}"', f'No model found for "{model}".'):
        return 'model_not_found'
    if message in ('No endpoints found', 'No endpoints found.', 'No endpoints found for this model.',
                   f'No endpoint found for model "{model}"', f'No endpoint found for model "{model}".'):
        return 'no_endpoints'
    return None


def transport_error_reason(error):
    """Classify network failures without passing exception text to the UI."""
    if isinstance(error, urllib.error.HTTPError): return None
    if isinstance(error, TimeoutError): return 'transport_timeout'
    if isinstance(error, urllib.error.URLError):
        return 'transport_timeout' if isinstance(error.reason, TimeoutError) else 'transport_error'
    if isinstance(error, ConnectionError): return 'transport_error'
    return None


def main():
    port, token = sys.argv[1:]
    os.environ.pop('COORDINATION_OPENROUTER_API_KEY', None)
    raw_config = sys.stdin.buffer.readline(8193)
    sys.stdin.close()
    config = json.loads(raw_config)
    key, models, privacy = config.get('key'), config.get('models'), config.get('privacy', 'zdr')
    provider, base_url = config.get('provider', 'openrouter'), config.get('base_url', '')
    try:
        provider_endpoint(provider, base_url, privacy)
    except ValueError:
        return 1
    if (not valid_key(key) or not isinstance(models, list) or not 1 <= len(models) <= 32
            or not all(valid_model(x) for x in models) or privacy not in ('zdr', 'standard')):
        return 1
    del config, raw_config
    model = models[0]
    messages = []
    with socket.create_connection(('127.0.0.1', int(port)), timeout=10) as sock:
        sock.sendall((token + '\n').encode('ascii'))
        sock.settimeout(None)
        with sock.makefile('rb') as stream:
            def send(message):
                sock.sendall((json.dumps(message, ensure_ascii=False) + '\n').encode('utf-8'))
            def options():
                return [{'id': 'model', 'category': 'model', 'currentValue': model,
                         'options': [{'value': x, 'name': x} for x in models]}]
            while True:
                raw = stream.readline(262145)
                if not raw or len(raw) > 262144 or not raw.endswith(b'\n'):
                    return 0
                msg = json.loads(raw)
                method, ident = msg.get('method'), msg.get('id')
                params = msg.get('params') or {}
                try:
                    if method == 'initialize':
                        result = {}
                    elif method == 'session/new':
                        result = {'sessionId': 'direct', 'configOptions': options()}
                    elif method == 'session/set_config_option':
                        selected = params.get('value')
                        if params.get('configId') != 'model' or not valid_model(selected):
                            raise ValueError('model unavailable')
                        if selected != model:
                            model = selected
                            messages.clear()
                        if selected not in models:
                            models = [selected]
                        result = {'configOptions': options()}
                    elif method == 'session/prompt':
                        parts = params.get('prompt')
                        if not isinstance(parts, list) or len(parts) != 1 or parts[0].get('type') != 'text':
                            raise ValueError('invalid prompt')
                        text = parts[0].get('text')
                        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 50000:
                            raise ValueError('invalid prompt')
                        pending = messages + [{'role': 'user', 'content': text}]
                        if sum(len(x['content']) for x in pending) > 100000:
                            raise ValueError('conversation too long')
                        if provider == 'openrouter':
                            answer, finish = complete(key, model, pending, privacy=privacy)
                        else:
                            answer, finish = complete(key, model, pending, privacy=privacy, provider=provider, base_url=base_url)
                        if finish == 'stop':
                            messages = pending + [{'role': 'assistant', 'content': answer}]
                        send({'jsonrpc': '2.0', 'method': 'session/update', 'params': {
                            'update': {'sessionUpdate': 'agent_message_chunk',
                                       'content': {'type': 'text', 'text': answer}}}})
                        result = {'stopReason': 'end_turn' if finish == 'stop' else 'max_tokens'}
                    else:
                        raise ValueError('unsupported request')
                    send({'jsonrpc': '2.0', 'id': ident, 'result': result})
                except Exception as error:
                    status = error.code if isinstance(error, urllib.error.HTTPError) else None
                    reason = provider_404_reason(error, model) if method == 'session/prompt' and provider == 'openrouter' else None
                    if method == 'session/prompt' and reason is None:
                        reason = transport_error_reason(error)
                    send({'jsonrpc': '2.0', 'id': ident, 'error': {'status': status, 'reason': reason}})


if __name__ == '__main__':
    raise SystemExit(main())
