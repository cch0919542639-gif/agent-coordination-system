"""One acknowledged task via native CLI, with validated artifact-only delivery."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from coordination_common import ROOT, load_task
from local_agent_loop import LoopError, allowed_file, handoff, relative_path, task_card, task_contract

OWNERS = {'antigravity': 'antigravity-coordination-pilot', 'reasonix': 'reasonix-coordination-pilot'}
MAX_OUTPUT = 128_000


def decode_result(runtime, stdout):
    try:
        result = json.loads(stdout)
    except (ValueError, TypeError) as exc:
        raise LoopError('CLI did not return one JSON result.') from exc
    if not isinstance(result, dict):
        raise LoopError('Malformed CLI result.')
    if runtime == 'antigravity':
        if result.get('status') != 'SUCCESS' or result.get('denied_actions'):
            raise LoopError('Antigravity did not return an unblocked SUCCESS result.')
        content = result.get('response')
    else:
        if result.get('is_error') is not False or result.get('subtype') != 'success' or result.get('permission_denials'):
            raise LoopError('Reasonix did not return an unblocked success result.')
        content = result.get('result')
    if not isinstance(content, str) or len(content.encode('utf-8')) > MAX_OUTPUT:
        raise LoopError('Missing or oversized structured response.')
    try:
        return json.loads(content)
    except ValueError as exc:
        raise LoopError('Worker response is not strict JSON.') from exc


def validate_artifacts(result, header):
    expected = header.get('structured_output_paths')
    if not isinstance(expected, list) or not expected or len(expected) != len(set(expected)):
        raise LoopError('Task requires unique explicit structured_output_paths.')
    if not isinstance(result, dict) or set(result) != {'summary', 'artifacts'}:
        raise LoopError('Expected summary and artifacts only.')
    if not isinstance(result['summary'], str) or not result['summary'].strip() or len(result['summary']) > 1000:
        raise LoopError('A bounded truthful summary is required.')
    artifacts = result['artifacts']
    if not isinstance(artifacts, list) or len(artifacts) != len(expected):
        raise LoopError('Every declared output must be delivered exactly once.')
    validated = {}
    resolved_targets = set()
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {'path', 'content'}:
            raise LoopError('Malformed artifact.')
        name, content = item['path'], item['content']
        if not isinstance(name, str) or name not in expected or name in validated or not allowed_file(name, header):
            raise LoopError('Artifact path is duplicate, unexpected or outside scope.')
        path = relative_path(name)
        resolved_name = path.relative_to(ROOT.resolve()).as_posix()
        if not allowed_file(resolved_name, header):
            raise LoopError('Resolved artifact target is outside the declared scope.')
        target_key = str(path).casefold() if os.name == 'nt' else str(path)
        if target_key in resolved_targets:
            raise LoopError('Multiple outputs resolve to the same file.')
        resolved_targets.add(target_key)
        if any(candidate.casefold().startswith(('coordination/task-board/', 'coordination/reviews/', 'coordination/monitor/', 'coordination/plans/', 'coordination/delivery/', 'coordination/progress/')) for candidate in (name, resolved_name)):
            raise LoopError('Model outputs cannot modify coordination control or receipt files.')
        if not isinstance(content, str) or not content or len(content.encode('utf-8')) > MAX_OUTPUT:
            raise LoopError('Invalid artifact content.')
        validated[name] = (path, content)
    return validated


def cli_command(runtime, prompt):
    if runtime == 'antigravity':
        executable = shutil.which('agy')
        if not executable:
            raise LoopError('Antigravity agy CLI is missing.')
        return [executable, '-p', prompt, '--model', os.environ.get('COORDINATION_ANTIGRAVITY_MODEL', 'gemini-3.8-flash-low'),
                '--output-format', 'json', '--print-timeout', '8m', '--disable-slash-commands']
    shim = shutil.which('reasonix')
    node = shutil.which('node')
    entry = Path(shim).parent / 'node_modules/reasonix/bin/reasonix.js' if shim else None
    if not node or entry is None or not entry.is_file():
        raise LoopError('Installed Reasonix Node entrypoint is missing.')
    return [node, str(entry), '-p', prompt, '--output-format', 'json']


def external_authorized(header):
    # The repo's compact frontmatter parser round-trips YAML booleans as strings.
    value = header.get('external_processing_authorized')
    return value is True or value in ('true', 'True')


def run(runtime, payload_id):
    owner = OWNERS[runtime]
    inbox = ROOT / 'coordination/monitor/inbox' / owner / f'{payload_id}.json'
    payload = json.loads(inbox.read_text(encoding='utf-8'))
    task_id = payload.get('task_id')
    # Reuse exact project, owner, ACK, inbox and current-card checks.
    handoff(task_id, owner, payload_id)
    card, header, body = task_card(task_id)
    if not external_authorized(header):
        raise LoopError('Task has no explicit external processing authorization.')
    if header['status'] not in {'READY', 'IN_PROGRESS'} or header['owner'] != owner:
        raise LoopError('Task ownership or state mismatch.')
    mode = header.get('worker_execution', 'structured_artifacts')
    if mode == 'native_tools':
        from native_tools_worker import run as run_native
        return run_native(runtime, payload_id)
    if mode != 'structured_artifacts':
        raise LoopError('Unsupported external worker execution mode.')
    contract = task_contract(header, body)
    inputs = {}
    for name in header.get('worker_input_paths', []):
        path = relative_path(name)
        if path.stat().st_size > 64_000:
            raise LoopError('Input exceeds the bounded worker context.')
        inputs[name] = path.read_text(encoding='utf-8-sig')
    outputs = header.get('structured_output_paths')
    # Validate the complete declared destination set before consuming a model call.
    validate_artifacts({'summary': 'preflight', 'artifacts': [{'path': p, 'content': 'preflight'} for p in outputs or []]}, header)
    if header['status'] == 'READY':
        subprocess.run([sys.executable, str(ROOT/'scripts/claim_task.py'), '--task-id', task_id, '--agent', owner], cwd=ROOT, check=True, capture_output=True)
    prompt = (
        f'You are the controlled {runtime} worker for task {task_id}. This single task is operator-authorized for model processing. '
        'Use NO tools: the runner supplies all task inputs and writes your validated outputs. Do not read files, run commands, delegate, '
        'accept, review, commit, merge or push. Return ONLY strict JSON, no Markdown fences: '
        '{"summary":"short factual description of produced content","artifacts":[{"path":"exact declared output path","content":"complete UTF-8 file text"}]}. '
        'Produce every declared output exactly once; calculate from the supplied dependency inputs. Never invent execution or test claims. '
        f'Allowed output paths: {json.dumps(outputs)}\nTask packet:\n{body}\nInputs:\n{json.dumps(inputs, ensure_ascii=False)}'
    )
    review = ROOT / 'coordination/reviews' / f'review-{task_id}.md'
    if review.is_file():
        prompt += '\nRepair the same task using these reviewer findings:\n' + review.read_text(encoding='utf-8')[:16000]
    result = subprocess.run(cli_command(runtime, prompt), cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=600)
    if result.returncode:
        raise LoopError(f'{runtime} CLI exited {result.returncode}; no delivery submitted.')
    manifest = decode_result(runtime, result.stdout.strip())
    artifacts = validate_artifacts(manifest, header)
    _, current, current_body = task_card(task_id)
    if current.get('status') != 'IN_PROGRESS' or task_contract(current, current_body) != contract:
        raise LoopError('Task contract changed during model execution.')
    for path, content in artifacts.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
    arguments = [sys.executable, str(ROOT/'scripts/submit_task.py'), '--task-id', task_id, '--agent', owner,
                 '--payload-id', payload_id, '--summary', manifest['summary']]
    for name in artifacts:
        arguments += ['--artifact', name]
    submitted = subprocess.run(arguments, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    if submitted.returncode or task_card(task_id)[1]['status'] != 'REVIEW':
        raise LoopError('Canonical report/REVIEW submission failed; no acceptance claimed.')
    print(json.dumps({'runtime': runtime, 'task_id': task_id, 'submitted': True, 'artifact_count': len(artifacts)}))
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True, choices=OWNERS)
    parser.add_argument('--payload-id', required=True)
    args=parser.parse_args()
    import re
    try:
        if not re.fullmatch('[a-f0-9]{16}', args.payload_id):
            raise LoopError('Invalid payload identifier.')
        return run(args.runtime, args.payload_id)
    except (LoopError, OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({'submitted': False, 'reason': str(exc) if isinstance(exc, LoopError) else type(exc).__name__}))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
