"""Independent native-tool evidence and artifact integrity acceptance check."""
import argparse
import json
import sys

from local_agent_loop import LoopError, handoff, relative_path, task_card
from native_tools_worker import READ_TOOLS, WRITE_TOOLS, load_contract, sha


def verify(task_id):
    _, header, _ = task_card(task_id)
    contract_path = relative_path(header['native_tool_contract'])
    raw = json.loads(contract_path.read_text(encoding='utf-8'))
    runtime = raw['runtime']
    contract = load_contract(header,runtime)
    evidence = json.loads(relative_path(header['native_tool_evidence']).read_text(encoding='utf-8'))
    if evidence.get('task_id') != task_id or evidence.get('runtime') != runtime or evidence.get('native_tools_verified') is not True:
        raise LoopError('Wrong or unverified native tool evidence.')
    handoff(task_id,header['owner'],evidence.get('payload_id'))
    if evidence.get('contract_sha256') != header['native_tool_contract_sha256']:
        raise LoopError('Native evidence identifies a different command contract.')
    for path in contract['artifacts']:
        if evidence.get('artifact_sha256',{}).get(path) != sha(relative_path(path)):
            raise LoopError('Native artifact differs from its verified tool delivery.')
    calls = evidence.get('observations',[])
    if not any(c.get('tool') in READ_TOOLS and not c.get('error') for c in calls): raise LoopError('Native read proof missing.')
    if not any(c.get('tool') in WRITE_TOOLS and not c.get('error') for c in calls): raise LoopError('Native edit proof missing.')
    for index in range(len(contract['commands'])):
        if not any(c.get('command_index') == index and c.get('exit_code') == 0 and not c.get('error') for c in calls):
            raise LoopError('Native successful command proof missing.')
    print(json.dumps({'task_id':task_id,'native_tool_evidence':'verified'}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task-id',required=True)
    args=parser.parse_args()
    try: verify(args.task_id)
    except (LoopError,OSError,KeyError,TypeError,ValueError) as exc:
        print(str(exc) if isinstance(exc,LoopError) else type(exc).__name__,file=sys.stderr)
        raise SystemExit(1)
