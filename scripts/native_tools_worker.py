"""Run one acknowledged task with native CLI tools and explicit command grants."""
from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

from coordination_common import ROOT
from local_agent_loop import (LoopError, allowed_file, atomic_json, fingerprints,
                              handoff, relative_path, scope_changes, task_card, task_contract)
from structured_agent_worker import OWNERS, cli_command, external_authorized

CONTROL = ('coordination/task-board/', 'coordination/reviews/', 'coordination/monitor/',
           'coordination/plans/', 'coordination/delivery/', 'coordination/progress/', '.git/')
READ_TOOLS = {'view_file', 'sed_file', 'read_file'}
WRITE_TOOLS = {'write_to_file', 'replace_file_content', 'multi_replace_file_content', 'write_file', 'edit_file'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scoped_path(name, header, *, artifact=False):
    path = relative_path(name)
    resolved = path.relative_to(ROOT.resolve()).as_posix()
    if not allowed_file(name, header) or not allowed_file(resolved, header):
        raise LoopError('Native output is outside the declared task scope.')
    if artifact and any(n.casefold().startswith(CONTROL) for n in (name, resolved)):
        raise LoopError('Native artifacts cannot write coordination control files.')
    return path


def command_text(argv):
    # Restrict grants to plain tokens; never authorize shell syntax or substitutions.
    if not isinstance(argv, list) or not argv or not all(isinstance(a, str) and re.fullmatch(r'[A-Za-z0-9_./:=+,@%-]+', a) for a in argv):
        raise LoopError('Native command contract must contain plain argv tokens.')
    return ' '.join(argv)


def normalized_command(text):
    if not isinstance(text, str) or any(c in text for c in '\n\r;&|<>`$'):
        return None
    try:
        return tuple(shlex.split(text, posix=True))
    except ValueError:
        return None


def load_contract(header, runtime):
    name = header.get('native_tool_contract')
    if not isinstance(name, str) or not name.startswith('coordination/plans/'):
        raise LoopError('Native task requires a reviewer-owned command contract.')
    path = relative_path(name)
    if allowed_file(name, header) or sha(path) != header.get('native_tool_contract_sha256'):
        raise LoopError('Native command contract is mutable or has changed.')
    contract = json.loads(path.read_text(encoding='utf-8'))
    if contract.get('version') != 1 or contract.get('runtime') != runtime:
        raise LoopError('Native command contract runtime/version mismatch.')
    artifacts = contract.get('artifacts')
    if not isinstance(artifacts, list) or not artifacts or len(set(artifacts)) != len(artifacts):
        raise LoopError('Native task requires unique explicit artifacts.')
    for output in artifacts:
        scoped_path(output, header, artifact=True)
    evidence = header.get('native_tool_evidence')
    scoped_path(evidence, header, artifact=True)
    if evidence in artifacts:
        raise LoopError('Tool evidence must be separate from model artifacts.')
    for name in contract.get('read_paths', []):
        if not relative_path(name).is_file():
            raise LoopError('A declared native input is missing.')
    commands = contract.get('commands')
    if not isinstance(commands, list) or not commands or len(commands) > 10:
        raise LoopError('Native tasks need one to ten explicit commands.')
    for command in commands:
        argv = command.get('argv')
        if not isinstance(argv, list) or not argv or argv[0] != '$PYTHON':
            raise LoopError('Native command execution currently requires explicit $PYTHON argv.')
        command['resolved_argv'] = [sys.executable.replace('\\', '/'), *argv[1:]]
        command_text(command['resolved_argv'])
        pins = command.get('pins')
        if not isinstance(pins, dict) or not pins:
            raise LoopError('Native command scripts must be independently pinned.')
        for name, expected in pins.items():
            path = relative_path(name)
            if allowed_file(name, header) or sha(path) != expected:
                raise LoopError('Native test source is mutable or its hash changed.')
    return contract


def atomic_bytes(path, value):
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        Path(name).unlink(missing_ok=True)


def restore_permission_lease(settings, journal):
    """Caller must hold the per-user permission lock; journal stays private."""
    lease = json.loads(journal.read_text(encoding='utf-8'))
    original = base64.b64decode(lease['original_base64'],validate=True) if lease['original_base64'] is not None else None
    try: current = settings.read_bytes()
    except FileNotFoundError: current = None
    if current is not None and hashlib.sha256(current).hexdigest() == lease['temporary_sha256']:
        if original is None: settings.unlink()
        else: atomic_bytes(settings,original)
    elif current is not None and current != original:
        updated = json.loads(current)
        permissions = updated.setdefault('permissions',{})
        permissions['allow'] = [r for r in permissions.get('allow',[]) if r not in lease['added_rules']]
        atomic_bytes(settings,(json.dumps(updated,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    journal.unlink()


@contextlib.contextmanager
def antigravity_grants(read_paths, write_paths, commands, settings=None):
    """Add exact grants for one run and restore bytes; never override deny/ask."""
    settings = settings or Path.home()/'.gemini/antigravity-cli/settings.json'
    settings.parent.mkdir(parents=True, exist_ok=True)
    lock_path = settings.with_name('acs-worker-permissions.lock')
    with lock_path.open('a+b') as lock:
        lock.seek(0, 2)
        if not lock.tell(): lock.write(b'0'); lock.flush()
        lock.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        journal = settings.with_name('acs-worker-permission-lease.json')
        if journal.exists():
            restore_permission_lease(settings,journal)
        original = settings.read_bytes() if settings.exists() else None
        config = json.loads(original or b'{}')
        rules = config.setdefault('permissions', {}).setdefault('allow', [])
        additions = [f'read_file({p})' for p in read_paths] + [f'write_file({p})' for p in write_paths] + [f'command({c})' for c in commands]
        additions = [rule for rule in additions if rule not in rules]
        rules.extend(additions)
        written = (json.dumps(config, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
        atomic_json(journal,{'original_base64':base64.b64encode(original).decode('ascii') if original is not None else None,
                             'temporary_sha256':hashlib.sha256(written).hexdigest(),'added_rules':additions})
        atomic_bytes(settings,written)
        try:
            yield
        finally:
            # Restores byte-for-byte normally, removes only our grants on a race,
            # and can recover the original state after an earlier process death.
            restore_permission_lease(settings,journal)
            if os.name == 'nt':
                lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else: fcntl.flock(lock, fcntl.LOCK_UN)


def native_argv(runtime, prompt, contract):
    argv = cli_command(runtime, prompt)
    argv[argv.index('--output-format')+1] = 'stream-json'
    if runtime == 'reasonix':
        argv += ['--permission-mode', 'dontAsk', '--max-steps', '24', '--add-dir', str(ROOT)]
        for name in contract['artifacts']:
            for rule in (f'Write({name})', f'Edit({name})'):
                argv += ['--allowed-tools', rule]
        for command in contract['commands']:
            argv += ['--allowed-tools', f'Bash({command_text(command["resolved_argv"])})']
    return argv


def observe(runtime, stdout, contract):
    """Keep tool provenance and numeric status, never prompts or tool file content."""
    required = {tuple(c['resolved_argv']) for c in contract['commands']}
    observations, complete = [], None
    for line in stdout.splitlines():
        try: event = json.loads(line)
        except ValueError: continue
        name, args, code, error = None, {}, None, False
        if runtime == 'antigravity':
            if event.get('event') == 'result': complete = event.get('result')
            step = event.get('step_update', {})
            if step.get('step_type') != 'tool' or step.get('state') not in {'DONE', 'ERROR'}: continue
            info = step.get('tool_info', {})
            name, args, error = step.get('tool_name'), info.get('parameters', {}), bool(info.get('error'))
            output = str(info.get('output', ''))
            if name == 'run_command':
                # Native stream does not always expose exitCode. A completed pytest
                # summary is observed output, not the model's claimed exit status.
                if not error and re.search(r'\b\d+ passed\b', output) and not re.search(r'\b[1-9]\d* (?:failed|error)', output): code = 0
        else:
            if event.get('type') == 'result': complete = event
            if event.get('kind') == 'turn_done' and event.get('err'):
                raise LoopError('Reasonix ended with unresolved native readiness obligations.')
            if event.get('kind') != 'tool_result': continue
            info = event.get('tool', {})
            name, error = info.get('name'), bool(info.get('error'))
            try: args = json.loads(info.get('args') or '{}')
            except ValueError: args = {}
            code = info.get('execution', {}).get('exitCode')
        if not name: continue
        item = {'tool': name, 'error': error}
        if name in {'run_command', 'bash'}:
            text = args.get('CommandLine', args.get('command'))
            normalized = normalized_command(text)
            if normalized not in required:
                executable = Path(normalized[0]).name if normalized else 'unparsed'
                executable = executable if re.fullmatch('[A-Za-z0-9_.-]{1,32}',executable) else 'unparsed'
                raise LoopError(f'Native worker attempted a command outside its explicit contract: {executable}.')
            item.update(command_index=next(i for i,c in enumerate(contract['commands']) if tuple(c['resolved_argv']) == normalized), exit_code=code)
        observations.append(item)
    if not isinstance(complete, dict): raise LoopError('Native CLI returned no terminal result.')
    if runtime == 'antigravity':
        if complete.get('status') != 'SUCCESS' or complete.get('denied_actions'): raise LoopError('Antigravity native run failed or needed ungranted permission.')
    elif complete.get('subtype') != 'success' or complete.get('is_error') is not False or complete.get('permission_denials') or complete.get('readiness', {}).get('missing'):
        raise LoopError('Reasonix native run failed, was denied or remains unverified.')
    if not any(o['tool'] in READ_TOOLS and not o['error'] for o in observations): raise LoopError('No successful native file read was observed.')
    if not any(o['tool'] in WRITE_TOOLS and not o['error'] for o in observations): raise LoopError('No successful native file edit was observed.')
    last_write = max(i for i,o in enumerate(observations) if o['tool'] in WRITE_TOOLS and not o['error'])
    for i in range(len(contract['commands'])):
        if not any(index > last_write and o.get('command_index') == i and o.get('exit_code') == 0 and not o['error'] for index,o in enumerate(observations)):
            raise LoopError('A required native test command has no successful tool result.')
    return observations


def invoke_native(argv, environment, timeout=600):
    process = subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                               text=True,encoding='utf-8',errors='replace',env=environment,start_new_session=os.name != 'nt')
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(argv,process.returncode,stdout,stderr)
    except BaseException:
        if os.name == 'nt':
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,check=False)
        else:
            import signal
            with contextlib.suppress(ProcessLookupError): os.killpg(process.pid,signal.SIGKILL)
        process.wait()
        raise


def _run(runtime, payload_id):
    owner = OWNERS[runtime]
    payload = json.loads((ROOT/f'coordination/monitor/inbox/{owner}/{payload_id}.json').read_text(encoding='utf-8'))
    task_id = payload.get('task_id')
    handoff(task_id, owner, payload_id)
    card, header, body = task_card(task_id)
    if not external_authorized(header) or header.get('worker_execution') != 'native_tools' or header.get('status') not in {'READY','IN_PROGRESS'}:
        raise LoopError('This exact task has not authorized native tool execution.')
    contract = load_contract(header, runtime)
    frozen = task_contract(header, body)
    before = fingerprints()
    if header['status'] == 'READY':
        subprocess.run([sys.executable,str(ROOT/'scripts/claim_task.py'),'--task-id',task_id,'--agent',owner],cwd=ROOT,check=True,capture_output=True)
    commands = [command_text(c['resolved_argv']) for c in contract['commands']]
    prompt = f'''You are the controlled native-tools {runtime} worker for task {task_id}.
This task is explicitly operator-authorized. Use your NATIVE FILE TOOLS to read the input,
edit the declared implementation file, then use your NATIVE TERMINAL TOOL to run ALL exact
commands listed below from {ROOT.as_posix()}. Do real tool work, not a JSON manifest.
Only declared artifact files may be changed. Read the task objective and inspect its code;
fix implementation until the test passes. Do not change reviewer-owned tests or contracts.
Claim is already complete; do not activate/claim/submit. The runner will verify tool evidence,
generate the report and submit REVIEW after your process exits. Never review, accept,
dispatch, spawn agents, enable automatic approval, commit, push, merge, inspect credentials
or access private transcripts. Do not wrap the command in cd, a shell, or another interpreter.
Use ONLY the exact command text. No additional shell commands, including git diff,
git status, pwd, ls, cat, rtk or wrapper commands; use native FILE TOOLS for inspection.
If this is a retry and the implementation is already correct, add a concise function
docstring using a native edit tool, then rerun the exact authorized test command.
Keep output concise; stop after the test succeeds.
Read paths: {json.dumps(contract.get('read_paths', []))}
Writable artifacts: {json.dumps(contract['artifacts'])}
Exact authorized commands:
{chr(10).join(commands)}
Task objective and constraints:
{body}
'''
    review = ROOT/f'coordination/reviews/review-{task_id}.md'
    if review.is_file(): prompt += '\nSame-task repair findings:\n'+review.read_text(encoding='utf-8')[:16000]
    reads = [str(relative_path(p)).replace('\\','/') for p in contract.get('read_paths', [])]
    writes = [str(relative_path(p)).replace('\\','/') for p in contract['artifacts']]
    grants = antigravity_grants(reads, writes, commands) if runtime == 'antigravity' else contextlib.nullcontext()
    with grants:
        result = invoke_native(native_argv(runtime,prompt,contract),dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    if result.returncode: raise LoopError(f'Native {runtime} CLI exited {result.returncode}; no submission accepted.')
    observations = observe(runtime, result.stdout, contract)
    _, current, current_body = task_card(task_id)
    if current.get('status') != 'IN_PROGRESS' or task_contract(current,current_body) != frozen:
        raise LoopError('Native worker changed the task contract.')
    load_contract(current, runtime)
    if scope_changes(before, header): raise LoopError('Native worker wrote outside the allowed task scope.')
    for name in contract['artifacts']:
        if not scoped_path(name,header,artifact=True).is_file(): raise LoopError('Native artifact is missing.')
    evidence = scoped_path(header['native_tool_evidence'],header,artifact=True)
    atomic_json(evidence, {'task_id':task_id,'runtime':runtime,'payload_id':payload_id,'observations':observations,
                           'contract_sha256':header['native_tool_contract_sha256'], 'native_tools_verified':True,
                           'artifact_sha256':{name:sha(relative_path(name)) for name in contract['artifacts']}})
    argv = [sys.executable,str(ROOT/'scripts/submit_task.py'),'--task-id',task_id,'--agent',owner,'--payload-id',payload_id,
            '--summary','Native file read/edit and explicitly authorized test commands succeeded; tool evidence recorded.']
    for name in [*contract['artifacts'],header['native_tool_evidence']]: argv += ['--artifact',name]
    submitted = subprocess.run(argv,cwd=ROOT,capture_output=True)
    if submitted.returncode or task_card(task_id)[1]['status'] != 'REVIEW': raise LoopError('Native task has no canonical REVIEW receipt.')
    print(json.dumps({'completed':True,'native_tools':True,'task_id':task_id,'tool_calls':len(observations)}))
    return 0


def run(runtime, payload_id):
    try:
        return _run(runtime,payload_id)
    except (LoopError,OSError,ValueError,TypeError,subprocess.SubprocessError) as exc:
        if re.fullmatch('[a-f0-9]{16}',payload_id):
            atomic_json(ROOT/f'coordination/monitor/runtime/native-tools/{payload_id}/last-error.json',
                        {'completed':False,'reason':str(exc) if isinstance(exc,LoopError) else type(exc).__name__})
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',required=True,choices=OWNERS)
    parser.add_argument('--payload-id',required=True)
    args=parser.parse_args()
    try:
        if not re.fullmatch('[a-f0-9]{16}',args.payload_id): raise LoopError('Invalid payload identifier.')
        return run(args.runtime,args.payload_id)
    except (LoopError,OSError,ValueError,TypeError,subprocess.SubprocessError) as exc:
        failure = {'completed':False,'reason':str(exc) if isinstance(exc,LoopError) else type(exc).__name__}
        if re.fullmatch('[a-f0-9]{16}',args.payload_id):
            atomic_json(ROOT/f'coordination/monitor/runtime/native-tools/{args.payload_id}/last-error.json',failure)
        print(json.dumps(failure))
        return 1


if __name__=='__main__': raise SystemExit(main())
