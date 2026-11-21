"""Owned text-only OpenRouter session; no tools, retries, or provider fallback policy changes."""
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request

ENDPOINT = 'https://openrouter.ai/api/v1/chat/completions'
CATALOG = 'https://openrouter.ai/api/v1/endpoints/zdr'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def valid_model(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}', value))


def valid_key(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[!-~]{1,512}', value))


def model_ids():
    values = os.environ.get('COORDINATION_DIRECT_MODELS', '').split(',')
    return list(dict.fromkeys(v for x in values if valid_model(v := x.strip())))[:32]


def catalog(opener=None):
    if opener is None:
        opener = urllib.request.build_opener(NoRedirect()).open
    with opener(CATALOG, timeout=15) as response:
        raw = response.read(4194305)
    if len(raw) > 4194304:
        raise ValueError('catalog too large')
    rows = json.loads(raw)['data']
    if not isinstance(rows, list) or len(rows) > 10000:
        raise ValueError('invalid catalog')
    result = {}
    for row in rows:
        if isinstance(row, dict) and valid_model(row.get('model_id')):
            model = row['model_id']
            result[model] = {'id': model, 'free': model.endswith(':free')}
    if len(result) > 2000:
        raise ValueError('catalog too large')
    return sorted(result.values(), key=lambda x: x['id'])


def complete(key, model, messages, opener=None):
    body = json.dumps({'model': model, 'messages': messages, 'max_tokens': 4096,
                       'provider': {'zdr': True, 'data_collection': 'deny'}},
                      ensure_ascii=False).encode('utf-8')
    request = urllib.request.Request(ENDPOINT, data=body, method='POST',
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


def main():
    port, token = sys.argv[1:]
    os.environ.pop('COORDINATION_OPENROUTER_API_KEY', None)
    raw_config = sys.stdin.buffer.readline(8193)
    sys.stdin.close()
    config = json.loads(raw_config)
    key, models = config.get('key'), config.get('models')
    if (not valid_key(key) or not isinstance(models, list) or not 1 <= len(models) <= 32
            or not all(valid_model(x) for x in models)):
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
                        answer, finish = complete(key, model, pending)
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
                    send({'jsonrpc': '2.0', 'id': ident, 'error': {'status': status}})


if __name__ == '__main__':
    raise SystemExit(main())
