"""Bounded, isolated core or handoff regression evidence for the fixed merge."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,time
root=Path(__file__).resolve().parents[3]
ev=Path(__file__).parent
group=sys.argv[1]
files={'core':['test_console_setup.py','test_web_console.py','test_state_controller.py','test_board_projection.py','test_parallel_runtime.py','test_worker_activation.py','test_worker_poller.py','test_local_agent_loop.py'],'handoff':['test_github_handoff.py','test_handoff_console.py']}[group]
base=Path(tempfile.mkdtemp(prefix='codex-pr9-'+group+'-'))/'pytest'
cmd=[sys.executable,'-B','-m','pytest',*['tests/scripts/'+f for f in files],'-q','--basetemp',str(base),'--junitxml',str(ev/(group+'.xml'))]
manifest=json.loads((root/'coordination/evidence/console-release-01/manifest.json').read_bytes())
hashes={p['path']:hashlib.sha256((root/p['path']).read_bytes()).hexdigest() for p in manifest['source_pins']}
start=time.monotonic()
with (ev/(group+'.log')).open('wb') as log:
    try:
        result=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=300)
        record=dict(returncode=result.returncode,timed_out=False)
    except subprocess.TimeoutExpired:
        record=dict(returncode=None,timed_out=True)
record.update(group=group,command=cmd,elapsed_seconds=round(time.monotonic()-start,3),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),tested_raw_sha256=hashes)
(ev/(group+'-result.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k!='tested_raw_sha256'}))
print((ev/(group+'.log')).read_text(encoding='utf-8',errors='replace')[-6500:])
