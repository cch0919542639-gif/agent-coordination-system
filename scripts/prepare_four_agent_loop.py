"""Create a fresh finite four-runtime chain, without launching a worker."""
import argparse
import json

from coordination_common import ROOT, load_task, save_task, utc_now_string
from local_agent_loop import WORKERS, digest
from prepare_local_loop import prepare


def prepare_four(run_id):
    plan_path = ROOT / prepare(run_id, workers=WORKERS)
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    cards = [next((ROOT/'coordination/task-board/ready').glob(f'*_{item["task_id"]}_*.md')) for item in plan['tasks']]
    base, _ = load_task(cards[0])
    owners = ['opencode-coordination-pilot','hermes-coordination-pilot','antigravity-coordination-pilot','reasonix-coordination-pilot','opencode-coordination-pilot']
    outputs = [f'coordination/evidence/{run_id}/stage{i}.json' for i in range(1,5)] + [f'coordination/evidence/{run_id}/final.json']
    expected = [{'stage':1,'agent':'opencode','value':7}, {'stage':2,'agent':'hermes','value':21},
                {'stage':3,'agent':'antigravity','value':22}, {'stage':4,'agent':'reasonix','value':44},
                {'status':'completed','value':44,'workers':['opencode','hermes','antigravity','reasonix']}]
    objectives = [
        f'Write {outputs[0]} with stage1, agent opencode and value7. Submit using the acknowledged payload and stop.',
        f'Read {outputs[0]}, multiply its value by3, and write {outputs[1]} with stage2, agent hermes and the calculated value. Submit and stop.',
        f'Read the supplied accepted stage2 input, add1 to its value, and produce {outputs[2]} as JSON with stage3, agent antigravity and the calculated value.',
        f'Read the supplied accepted stage3 input, double its value, and produce {outputs[3]} as JSON with stage4, agent reasonix and the calculated value.',
        f'Read {outputs[3]} and write {outputs[4]} with status completed, its accepted value, and workers [opencode, hermes, antigravity, reasonix]. Submit and stop.',
    ]
    plan['tasks'] = []
    date=utc_now_string().split()[0]
    for i, owner in enumerate(owners):
        task_id=f'{run_id}-{i+1:02}'
        basename=f'{date}_{task_id}_download-loop-demo.md'
        checks=[{'path':outputs[i], 'json_equals':expected[i]}]
        header=dict(base,task_id=task_id,phase='four-agent-local-verification',owner=owner,
                    dependencies=[f'{run_id}-{i:02}'] if i else [],local_loop_checks_sha256=digest(checks),
                    allowed_scope=[f'coordination/task-board/{s}/{basename}' for s in ['ready','in_progress','review']] +
                    [outputs[i],f'coordination/delivery/{task_id}-delivery-report.md',f'coordination/progress/{owner}.md'])
        if owner in {'antigravity-coordination-pilot','reasonix-coordination-pilot'}:
            header.update(external_processing_authorized=True,structured_output_paths=[outputs[i]],worker_input_paths=[outputs[i-1]])
        body=f'''# Task Packet

## Objective

{objectives[i]}

## Context

Operator-authorized finite four-agent local verification. Read AGENTS.md, PLAN.md,
PROGRESS.md and docs/operations/agent-task-execution-protocol.md before lifecycle work.
Structured runtimes receive the packet and accepted inputs through their runner.
Only synthetic JSON task inputs may be sent to the existing configured providers.

## Constraints

Write only allowed paths. No credentials, other task changes, self-review, dispatch,
agents, commit, push or merge. Preserve all existing receipts and files.

## Implementation Notes

For OpenCode/Hermes, claim this task only if READY, then use scripts/submit_task.py
--task-id {task_id} --agent {owner} --payload-id YOUR_ACK --summary 'factual summary'
--artifact {outputs[i]}. On repair skip claim and correct the same task.
For structured runtimes, return the requested manifest; the runner performs claim,
bounded writes and canonical submission, and never accepts its own work.

## Validation Steps

Run coordination validation and submit to REVIEW. LOCAL_LOOP independently compares
the pinned JSON and scope evidence before dispatching the dependent task.

## Escalation Rules

Stop on missing input, wrong ACK, provider failure or scope conflict. Record the
blocker in the allowed progress file. Never fabricate delivery or acceptance.
'''
        save_task(ROOT/f'coordination/task-board/ready/{basename}',header,body)
        plan['tasks'].append({'task_id':task_id,'owner':owner,'checks':checks})
    plan_path.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
    return plan_path.relative_to(ROOT).as_posix()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args()
    print(json.dumps({'prepared_plan':prepare_four(args.run_id),'workers_launched':0}))
