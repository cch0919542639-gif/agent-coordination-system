"""Explicit, source-pinned ACS memory import and verified recall (stdlib only)."""
from __future__ import annotations

import argparse
from contextlib import closing
import datetime as dt
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

REPOSITORY = 'https://github.com/cch0919542639-gif/agent-coordination-system'
PROJECT = 'agent-coordination-system'
LIMIT = 262144
CARD_FIELDS = {'memory_id', 'title', 'summary', 'source_commit', 'source_path',
               'source_blob_sha256', 'source_anchor', 'source_date', 'approval_ref',
               'applicable_versions', 'status', 'supersedes', 'task_ref'}
SENSITIVE = re.compile(
    r'-----BEGIN .*PRIVATE KEY-----|(?:gh[pousr]_|github_pat_|sk-(?:mem-|ant-)?)[A-Za-z0-9_-]{20,}'
    r'|\bBearer\s+[A-Za-z0-9_.-]{8,}|\b(?:password|api_key|token)\s*[:=]\s*\S+'
    r'|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|[A-Za-z]:[\\/](?:Users|acs-console-private)', re.I)


class Refused(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def emit(value):
    # ASCII JSON transport also works in ordinary CP950 Windows terminals.
    print(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True), flush=True)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Refused('Duplicate JSON key.')
        result[key] = value
    return result


def decode(raw):
    if len(raw) > LIMIT:
        raise Refused('JSON exceeds size bound.')
    try:
        value = json.loads(raw, object_pairs_hook=unique_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(Refused('Nonfinite JSON.')))
    except RecursionError:
        raise Refused('JSON nesting exceeds parser bound.') from None
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > 64:
            raise Refused('JSON nesting exceeds 64 levels.')
        if isinstance(item, dict):
            pending.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            pending.extend((v, depth + 1) for v in item)
    return value


def load_json(path):
    with Path(path).open('rb') as stream:
        return decode(stream.read(LIMIT + 1))


def git(repo, *args):
    run = subprocess.run(['git', '--no-replace-objects', '-C', str(repo), *args],
                         capture_output=True, timeout=15)
    if run.returncode:
        raise Refused('Git source unavailable; no network operation attempted.')
    return run.stdout


def text(value, field, maximum=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise Refused('Invalid ' + field + '.')
    if SENSITIVE.search(value) or any(ord(c) < 32 and c not in '\n\t' for c in value):
        raise Refused('Sensitive or control content refused in ' + field + '; review locally.')
    return value


def validate(repo, batch):
    if not isinstance(batch, dict) or set(batch) != {'schema_version', 'project_id', 'repository', 'cards'}:
        raise Refused('Invalid batch shape.')
    if type(batch['schema_version']) is not int or batch['schema_version'] != 1:
        raise Refused('Unsupported batch schema.')
    if batch['project_id'] != PROJECT or batch['repository'] != REPOSITORY:
        raise Refused('Repository/project boundary mismatch.')
    remote = git(repo, 'remote', 'get-url', 'origin').decode().strip()
    remote = remote.removesuffix('.git').replace('git@github.com:', 'https://github.com/')
    if remote != REPOSITORY:
        raise Refused('Checkout origin differs from approved repository.')
    cards = batch['cards']
    if not isinstance(cards, list) or not 1 <= len(cards) <= 10:
        raise Refused('A batch requires 1..10 cards.')
    ids = {}
    for card in cards:
        if not isinstance(card, dict) or set(card) != CARD_FIELDS:
            raise Refused('Invalid card shape.')
        key = card['memory_id']
        if not isinstance(key, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,47}', key) or key in ids:
            raise Refused('Invalid or duplicate memory_id.')
        ids[key] = card
        for field in ('title', 'summary', 'source_path', 'source_date', 'approval_ref', 'applicable_versions', 'task_ref'):
            text(card[field], field)
        if card['status'] not in ('active', 'superseded', 'withdrawn'):
            raise Refused('Invalid card status.')
        if not isinstance(card['supersedes'], list) or any(not isinstance(x, str) for x in card['supersedes']):
            raise Refused('Invalid supersedes list.')
        if len(set(card['supersedes'])) != len(card['supersedes']):
            raise Refused('Duplicate supersedes entry.')
        try:
            dt.date.fromisoformat(card['source_date'])
        except ValueError:
            raise Refused('Invalid source date.') from None
        path = card['source_path']
        if (not re.fullmatch(r'[A-Za-z0-9/_.-]+\.md', path) or
                any(p in ('', '.', '..') for p in path.split('/')) or
                not path.startswith(('docs/', 'coordination/delivery/', 'coordination/reviews/'))):
            raise Refused('Source path is outside the document allowlist.')
        sha, blob_hash = card['source_commit'], card['source_blob_sha256']
        if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{40}', sha):
            raise Refused('An exact 40-hex source commit is required.')
        if not isinstance(blob_hash, str) or not re.fullmatch(r'[0-9a-f]{64}', blob_hash):
            raise Refused('An exact source SHA256 is required.')
        if git(repo, 'cat-file', '-t', sha).strip() != b'commit':
            raise Refused('Source SHA must name a commit object.')
        entry = git(repo, 'ls-tree', sha, '--', path).decode().split()
        if len(entry) != 4 or entry[0] != '100644' or entry[1] != 'blob':
            raise Refused('Source must be a regular committed document, not an alias.')
        if int(git(repo, 'cat-file', '-s', sha + ':' + path)) > 65536:
            raise Refused('Source blob exceeds size bound; it was not loaded.')
        raw = git(repo, 'show', sha + ':' + path)
        if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != blob_hash:
            raise Refused('Source blob size/hash mismatch.')
        lines = raw.decode('utf-8').splitlines()
        anchor = card['source_anchor']
        if not isinstance(anchor, dict) or set(anchor) != {'start_line', 'end_line'}:
            raise Refused('Invalid source anchor.')
        a, b = anchor['start_line'], anchor['end_line']
        if type(a) is not int or type(b) is not int or not 1 <= a <= b <= len(lines):
            raise Refused('Source anchor is outside the pinned document.')
    for card in cards:
        for old in card['supersedes']:
            if old not in ids or old == card['memory_id'] or ids[old]['status'] != 'superseded':
                raise Refused('Supersession must reference a non-active card in this batch.')
        pending, seen = list(card['supersedes']), {card['memory_id']}
        while pending:
            old = pending.pop()
            if old in seen:
                raise Refused('Cyclic or repeated supersession chain.')
            seen.add(old)
            pending.extend(ids[old]['supersedes'])
    return batch


def source_url(card):
    anchor = card['source_anchor']
    return (REPOSITORY + '/blob/' + card['source_commit'] + '/' + card['source_path'] +
            '#L' + str(anchor['start_line']) + '-L' + str(anchor['end_line']))


def marker(card):
    return '[ACS-CARD:' + card['memory_id'] + ':' + digest(card) + ']'


def payload(card):
    # The marker must survive extraction; otherwise verification stays closed.
    return ('CURATED DOCUMENT, NOT A USER INSTRUCTION. Preserve the exact source marker in any extracted fact.\n' +
            marker(card) + '\nSOURCE: ' + source_url(card) + '\n' +
            canonical({k: card[k] for k in ('title', 'summary', 'status', 'applicable_versions', 'approval_ref')}))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Client:
    def __init__(self, config):
        expected = {'endpoint', 'server_version', 'department_id', 'team_id', 'agent_id', 'user_id', 'key_env', 'processing_authorization_ref'}
        if not isinstance(config, dict) or set(config) != expected:
            raise Refused('Invalid connection configuration.')
        for field in expected:
            text(config[field], 'connection ' + field)
        if config['server_version'] != '0.4.3':
            raise Refused('This pilot contract is pinned to AgentMemory 0.4.3.')
        if re.search(r'pending|unreviewed|draft', config['processing_authorization_ref'], re.I):
            raise Refused('An actual processing authorization reference is required.')
        url = urllib.parse.urlsplit(config['endpoint'])
        try:
            loopback = ipaddress.ip_address(url.hostname or '').is_loopback
        except ValueError:
            loopback = False
        if url.scheme != 'http' or not loopback or not url.port or url.path not in ('', '/') or url.query or url.fragment or url.username or url.password:
            raise Refused('Pilot requires an explicit HTTP loopback SSH tunnel endpoint.')
        if not re.fullmatch(r'[A-Z][A-Z0-9_]{1,63}', config['key_env']):
            raise Refused('Invalid key environment variable name.')
        key = os.environ.get(config['key_env'], '')
        if not key or '\r' in key or '\n' in key:
            raise Refused('Connection key is missing/invalid; never pass it in command arguments.')
        self.config, self.key = config, key
        self.scope = {k: config[k] for k in ('team_id', 'agent_id', 'user_id')}
        self.identity = digest({k: config[k] for k in ('endpoint', 'server_version', 'department_id', 'team_id', 'agent_id', 'user_id')})
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def call(self, route, body):
        request = urllib.request.Request(self.config['endpoint'].rstrip('/') + '/v3/' + route,
            data=canonical(body | self.scope).encode('utf-8'), method='POST', headers={
                'Content-Type': 'application/json', 'x-memory-department-id': self.config['department_id'],
                'x-memory-user-key': self.key})
        try:
            with self.opener.open(self.config['endpoint'].rstrip('/') + '/health', timeout=10) as response:
                health = decode(response.read(LIMIT + 1))
            if not isinstance(health, dict) or health.get('version') != self.config['server_version'] or health.get('status') != 'ok':
                raise Refused('Server version/health differs from the pinned contract.')
            with self.opener.open(request, timeout=10) as response:
                data = decode(response.read(LIMIT + 1))
            if not isinstance(data, dict) or type(data.get('code')) is not int or data['code'] != 0 or not isinstance(data.get('data'), dict):
                raise Refused('Unsuccessful or malformed memory response.')
            return data['data']
        except (urllib.error.URLError, OSError, ValueError) as error:
            # Remote bodies and URLs may contain credentials or private data.
            raise Refused('Memory service unavailable/refused or malformed; delivery may be uncertain.') from None


def external_path(path, repo):
    path, repo = Path(path), Path(repo).resolve()
    if not path.is_absolute() or path != path.resolve() or path.is_relative_to(repo):
        raise Refused('Runtime paths must be absolute canonical paths outside the checkout.')
    return path


def ledger(path, repo, create=False):
    path = external_path(path, repo)
    if not path.parent.is_dir():
        raise Refused('Create the receipt parent explicitly first.')
    if not create and not path.is_file():
        raise Refused('Receipt DB does not exist; query never initializes it.')
    db = sqlite3.connect(path.as_uri() + '?mode=' + ('rwc' if create else 'rw'), uri=True, timeout=3)
    version = db.execute('PRAGMA user_version').fetchone()[0]
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if create and version == 0 and not tables:
        with db:
            db.execute('CREATE TABLE receipts(scope TEXT, card_hash TEXT, state TEXT, atom_ids TEXT, PRIMARY KEY(scope,card_hash))')
            db.execute('CREATE TABLE batches(scope TEXT, batch_hash TEXT, manifest TEXT, connection TEXT, approved_at TEXT, PRIMARY KEY(scope,batch_hash))')
            db.execute('CREATE TABLE active(scope TEXT PRIMARY KEY, batch_hash TEXT)')
            db.execute('PRAGMA user_version=1')
    elif version != 1 or tables != {'receipts', 'batches', 'active'}:
        db.close()
        raise Refused('Foreign receipt DB refused; no repair or migration.')
    return db


def session(card):
    return 'acs-' + digest(card)


def receipt(db, client, card):
    return db.execute('SELECT state,atom_ids FROM receipts WHERE scope=? AND card_hash=?',
                      (client.identity, digest(card))).fetchone()


def import_cards(db, client, batch, approved_hash):
    if approved_hash != digest(batch):
        raise Refused('Operator approval must match the exact preview batch SHA256.')
    require_card_approvals(batch)
    with db:
        db.execute('INSERT OR IGNORE INTO batches VALUES(?,?,?,?,?)', (client.identity, digest(batch),
            canonical(batch), canonical(client.config), dt.datetime.now(dt.timezone.utc).isoformat()))
    submitted = replayed = 0
    for card in batch['cards']:
        if card['status'] != 'active':
            continue
        old = receipt(db, client, card)
        if old:
            if old[0] == 'uncertain':
                raise Refused('Prior delivery uncertain; run reconcile, never blindly resend.')
            replayed += 1
            continue
        # Reserve durably before HTTP: interruption and lost replies cannot cause blind replay.
        with db:
            db.execute('INSERT INTO receipts VALUES(?,?,?,?)', (client.identity, digest(card), 'uncertain', '[]'))
        client.call('conversation/add', {'session_id': session(card), 'messages': [
            {'role': 'user', 'content': payload(card)}]})
        with db:
            db.execute('UPDATE receipts SET state=? WHERE scope=? AND card_hash=?',
                       ('submitted', client.identity, digest(card)))
        submitted += 1
    return dict(batch_sha256=digest(batch), submitted=submitted, replayed=replayed,
                deployment_gate='HOLD until upstream extraction and source verification pass')


def reconcile(db, client, batch):
    require_batch(db, client, batch)
    recovered = 0
    for card in batch['cards']:
        old = receipt(db, client, card)
        if not old or old[0] != 'uncertain':
            continue
        data = client.call('conversation/query', {'session_id': session(card), 'limit': 100})
        rows = data.get('messages')
        if not isinstance(rows, list) or data.get('total') != 1 or len(rows) != 1 or rows[0].get('content') != payload(card):
            raise Refused('Delivery cannot be proven uniquely; keep receipt uncertain.')
        with db:
            db.execute('UPDATE receipts SET state=? WHERE scope=? AND card_hash=?',
                       ('submitted', client.identity, digest(card)))
        recovered += 1
    return dict(recovered=recovered)


def verify(db, client, batch):
    require_batch(db, client, batch)
    cards = [c for c in batch['cards'] if c['status'] == 'active']
    if any(not receipt(db, client, c) or receipt(db, client, c)[0] == 'uncertain' for c in cards):
        raise Refused('Import/reconcile every active card before extraction verification.')
    data = client.call('atomic/query', {'limit': 100}) if cards else {'items': [], 'total': 0}
    rows = data.get('items')
    if not isinstance(rows, list) or type(data.get('total')) is not int or data['total'] != len(rows) or len(rows) > 100:
        raise Refused('Atom snapshot is incomplete; no partial verification.')
    matches = {}
    for card in cards:
        ids = [r['id'] for r in rows if isinstance(r, dict) and isinstance(r.get('id'), str)
               and marker(card) in r.get('content', '')]
        if not ids:
            raise Refused('Extraction missing exact card/source marker; deployment gate remains HOLD.')
        matches[digest(card)] = sorted(set(ids))
    with db:
        for card_hash, ids in matches.items():
            db.execute('UPDATE receipts SET state=?,atom_ids=? WHERE scope=? AND card_hash=?',
                       ('verified', canonical(ids), client.identity, card_hash))
        db.execute('INSERT OR REPLACE INTO active VALUES(?,?)', (client.identity, digest(batch)))
    return dict(verified=len(matches), proof='source markers only; model quality and upstream runtime require separate evidence')


def require_batch(db, client, batch):
    if not db.execute('SELECT 1 FROM batches WHERE scope=? AND batch_hash=?', (client.identity, digest(batch))).fetchone():
        raise Refused('This exact batch has no operator-approved import receipt.')


def require_card_approvals(batch):
    if any(re.search(r'pending|unreviewed|draft', c['approval_ref'], re.I)
           for c in batch['cards'] if c['status'] == 'active'):
        raise Refused('Candidate cards require actual review references before import.')


def query(db, client, batch, question):
    text(question, 'query', 2000)
    require_batch(db, client, batch)
    current = db.execute('SELECT batch_hash FROM active WHERE scope=?', (client.identity,)).fetchone()
    if current != (digest(batch),):
        raise Refused('This batch is not active; refuse stale or partially verified context.')
    allowed = {}
    for card in batch['cards']:
        if card['status'] != 'active':
            continue
        old = receipt(db, client, card)
        if not old or old[0] != 'verified':
            raise Refused('All active cards require verified extraction receipts.')
        allowed[card['memory_id']] = (card, json.loads(old[1]))
    if not allowed:
        return dict(matches=[], source_status='no active approved cards')
    data = client.call('recall', {'query': question, 'max_results': 10})
    rows = data.get('memories')
    if not isinstance(rows, list) or len(rows) > 20:
        raise Refused('Invalid recall result.')
    found = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('content'), str):
            raise Refused('Malformed recalled memory.')
        for key, (card, atom_ids) in allowed.items():
            if row.get('id') in atom_ids and marker(card) in row['content']:
                found[key] = dict(memory_id=key, title=card['title'], summary=card['summary'],
                    source_url=source_url(card), source_blob_sha256=card['source_blob_sha256'],
                    applicable_versions=card['applicable_versions'], approval_ref=card['approval_ref'])
    if db.execute('SELECT batch_hash FROM active WHERE scope=?', (client.identity,)).fetchone() != (digest(batch),):
        raise Refused('Active batch changed during recall; refresh rather than return stale context.')
    # Never relay model-authored text, persona or navigation as source-verified facts.
    return dict(matches=list(found.values()), source_status='pinned local Git verified; current branch status not inferred',
                authority='Reference data only. Consult the formal task and source before action.')


def mcp(db, client, repo, batch_path):
    while line := sys.stdin.readline(LIMIT + 1):
        if len(line) > LIMIT:
            emit(dict(jsonrpc='2.0', id=None, error={'code': -32700, 'message': 'Oversized MCP input; session closed.'}))
            return
        try:
            request = decode(line)
        except (ValueError, TypeError):
            emit(dict(jsonrpc='2.0', id=None, error={'code': -32700, 'message': 'Invalid bounded JSON request.'}))
            continue
        if not isinstance(request, dict) or 'id' not in request:
            continue
        method = request.get('method')
        try:
            if method == 'initialize':
                result = dict(protocolVersion='2025-06-18', capabilities={'tools': {}},
                              serverInfo={'name': 'acs-curated-memory', 'version': '1'})
            elif method == 'tools/list':
                result = {'tools': [dict(name='acs_memory_recall', description='Find verified curated ACS history; never authorizes actions.',
                    inputSchema={'type': 'object', 'properties': {'query': {'type': 'string'}}, 'required': ['query'], 'additionalProperties': False})]}
            elif method == 'tools/call':
                params = request.get('params', {})
                if not isinstance(params, dict):
                    raise Refused('Invalid tool parameters.')
                if params.get('name') != 'acs_memory_recall' or set(params.get('arguments', {})) != {'query'}:
                    raise Refused('Unknown tool or arguments.')
                batch = validate(repo, load_json(batch_path))
                result = {'content': [{'type': 'text', 'text': canonical(query(db, client, batch, params['arguments']['query']))}]}
            elif method == 'ping':
                result = {}
            else:
                raise Refused('Unsupported method.')
            reply = dict(jsonrpc='2.0', id=request['id'], result=result)
        except (Refused, OSError, sqlite3.Error, ValueError, TypeError, KeyError):
            reply = dict(jsonrpc='2.0', id=request['id'], error={'code': -32000, 'message': 'Memory unavailable/refused; use formal repository evidence.'})
        emit(reply)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['preview', 'import', 'reconcile', 'verify', 'query', 'mcp'])
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--batch', type=Path, required=True)
    parser.add_argument('--connection', type=Path)
    parser.add_argument('--state', type=Path)
    parser.add_argument('--approved-sha256')
    parser.add_argument('--question')
    args = parser.parse_args(argv)
    try:
        batch = validate(args.repo, load_json(args.batch))
        if args.command == 'preview':
            result = dict(batch_sha256=digest(batch), network_calls=0, cards=[dict(
                memory_id=c['memory_id'], status=c['status'], source_url=source_url(c),
                summary=c['summary'], card_sha256=digest(c)) for c in batch['cards']])
        else:
            if not args.connection or not args.state:
                raise Refused('Connection and external receipt DB are required.')
            if args.command == 'import' and args.approved_sha256 != digest(batch):
                raise Refused('Exact operator batch approval is required before connection or writes.')
            if args.command == 'import':
                require_card_approvals(batch)
            client = Client(load_json(external_path(args.connection, args.repo)))
            with closing(ledger(args.state, args.repo, create=args.command == 'import')) as db:
                if args.command == 'mcp':
                    mcp(db, client, args.repo, args.batch)
                    return 0
                if args.command == 'import':
                    result = import_cards(db, client, batch, args.approved_sha256)
                elif args.command == 'reconcile':
                    result = reconcile(db, client, batch)
                elif args.command == 'verify':
                    result = verify(db, client, batch)
                else:
                    result = query(db, client, batch, args.question)
        emit(result)
        return 0
    except Refused as error:
        print('Curated memory refused: ' + str(error), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error, subprocess.SubprocessError):
        print('Curated memory refused/unavailable. Check pinned sources, exact approval, connection and receipt state; no automatic retry.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
