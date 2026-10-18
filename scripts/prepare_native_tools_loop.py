"""Prepare a fresh four-runtime loop with real native edits/tests in stages 3/4."""
import argparse
import json

from coordination_common import ROOT,save_task
from local_agent_loop import digest,task_card
from native_tools_worker import sha
from prepare_four_agent_loop import prepare_four


def prepare_native(run_id):
    from local_agent_loop import identifier
    identifier(run_id)
    if (ROOT/f'coordination/evidence/{run_id}').exists():
        raise ValueError('Native run output directory already exists; existing files are preserved.')
    plan_path=ROOT/prepare_four(run_id)
    plan=json.loads(plan_path.read_text(encoding='utf-8'))
    for stage,runtime,expression in [(3,'antigravity','value + 1'),(4,'reasonix','value * 2')]:
        task_id=f'{run_id}-{stage:02}'
        card,header,body=task_card(task_id)
        code=f'coordination/evidence/{run_id}/native{stage}.py'
        previous=f'coordination/evidence/{run_id}/stage{stage-1}.json'
        output=f'coordination/evidence/{run_id}/stage{stage}.json'
        evidence=f'coordination/evidence/{run_id}/{runtime}-native-tools.json'
        test=f'coordination/checks/{run_id}/test_native{stage}.py'
        test_path=ROOT/test
        test_path.parent.mkdir(parents=True,exist_ok=True)
        source=f'''from pathlib import Path
import importlib.util
import json

ROOT=Path(__file__).resolve().parents[3]

def test_native_calculation():
    spec=importlib.util.spec_from_file_location('worker_native{stage}',ROOT/{code!r})
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    for value in [-3,0,5,21]:
        assert module.transform(value)=={expression}
    previous=json.loads((ROOT/{previous!r}).read_text(encoding='utf-8'))
    value=previous['value']
    result={{'stage':{stage},'agent':{runtime!r},'value':module.transform(value)}}
    (ROOT/{output!r}).write_text(json.dumps(result),encoding='utf-8')
'''
        test_path.write_text(source,encoding='utf-8')
        code_path=ROOT/code
        code_path.parent.mkdir(parents=True,exist_ok=True)
        code_path.write_text('def transform(value):\n    return value - 7\n',encoding='utf-8')
        contract={'version':1,'runtime':runtime,'read_paths':[code,previous,test],
                  'artifacts':[code,output],
                  'commands':[{'argv':['$PYTHON','-m','pytest',test,'-q','-p','no:cacheprovider'],
                               'pins':{test:sha(test_path)}}]}
        contract_name=f'coordination/plans/{task_id}-native-tools.json'
        contract_path=ROOT/contract_name
        contract_path.write_text(json.dumps(contract,indent=2)+'\n',encoding='utf-8')
        checks=plan['tasks'][stage-1]['checks']
        checks.append({'command':['$PYTHON','scripts/verify_native_tools.py','--task-id',task_id]})
        header.update(worker_execution='native_tools',native_tool_contract=contract_name,
                      native_tool_contract_sha256=sha(contract_path),native_tool_evidence=evidence,
                      local_loop_checks_sha256=digest(checks))
        header['allowed_scope'] += [code,evidence]
        header.pop('structured_output_paths',None)
        header.pop('worker_input_paths',None)
        body=body.replace('For structured runtimes, return the requested manifest; the runner performs claim,\nbounded writes and canonical submission, and never accepts its own work.',
            f'Use native file tools to read {code}, {previous} and {test}.\nFix transform(value) to return {expression}. Execute the exact pinned pytest command\nusing your native terminal tool. The passing test produces {output}.\nThe runner performs lifecycle claim/submission and verifies native tool provenance.\nNever change the test, command contract or tool evidence yourself.')
        save_task(card,header,body)
    # Make scalar types explicit to every worker; "stage2" alone is ambiguous.
    for task in plan['tasks']:
        card,header,body=task_card(task['task_id'])
        expected=task['checks'][0]['json_equals']
        objective='The delivered JSON must equal '+json.dumps(expected,separators=(',',':'))+'. Preserve the exact JSON value types.\n'
        if header['owner'] in {'opencode-coordination-pilot','hermes-coordination-pilot'}:
            objective+='After writing the artifact, use scripts/submit_task.py with --summary and --artifact for canonical submission; do not manually build a delivery report.\n'
        body=body.replace('## Objective\n\n','## Objective\n\n'+objective+'\n',1)
        save_task(card,header,body)
    plan_path.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
    return plan_path.relative_to(ROOT).as_posix()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args()
    print(json.dumps({'prepared_plan':prepare_native(args.run_id),'workers_launched':0}))
