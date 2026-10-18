import json
from pathlib import Path
import shutil
import subprocess
import sys

import yaml


def test_four_runtime_plan_preserves_ack_and_checks(tmp_path):
    source=Path(__file__).resolve().parents[2]
    shutil.copytree(source/'scripts',tmp_path/'scripts',ignore=shutil.ignore_patterns('__pycache__'))
    command=[sys.executable,str(tmp_path/'scripts/prepare_four_agent_loop.py'),'--run-id','four-test']
    result=subprocess.run(command,capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['workers_launched']==0
    plan=json.loads((tmp_path/'coordination/plans/four-test.json').read_text())
    assert [t['owner'] for t in plan['tasks']]==['opencode-coordination-pilot','hermes-coordination-pilot','antigravity-coordination-pilot','reasonix-coordination-pilot','opencode-coordination-pilot']
    workers=json.loads((tmp_path/'coordination/monitor/workers.json').read_text())
    assert len(workers)==4 and all(w['enabled'] for w in workers)
    cards=list((tmp_path/'coordination/task-board/ready').glob('*.md'))
    assert len(cards)==5
    for card in cards:
        header=yaml.safe_load(card.read_text().split('---')[1])
        n=int(header['task_id'].rsplit('-',1)[1])
        assert header['dependencies']==([f'four-test-{n-1:02}'] if n>1 else [])
        if n in [3,4]:
            assert header['external_processing_authorized'] is True
            assert len(header['structured_output_paths'])==len(header['worker_input_paths'])==1
    assert not (tmp_path/'coordination/monitor/inbox').exists()
    before={p.relative_to(tmp_path):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert subprocess.run(command,capture_output=True,timeout=20).returncode!=0
    assert before=={p.relative_to(tmp_path):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
