"""Independent UI regression checks using disposable sessions and fixture keys."""
from pathlib import Path
import os
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from worker_process_guard import JobProcess


@pytest.mark.skipif(os.name != 'nt', reason='Windows owned Job')
def test_team_controls_and_delayed_session_responses(tmp_path):
    binary = shutil.which('node')
    if not binary:
        pytest.skip('Node required')
    script = tmp_path / 'review-ui.cjs'
    script.write_text(r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
class E {
  constructor() { this.children=[]; this.listeners={}; this.value=''; this.hidden=false;
    this.disabled=false; this.dataset={}; this.textContent=''; }
  append(...args) { this.children.push(...args); }
  replaceChildren(...args) { this.children=args; }
  addEventListener(name, fn) { this.listeners[name]=fn; }
  setAttribute() {} removeAttribute() {} focus() {}
}
const nodes = new Map(), get = id => { if (!nodes.has(id)) nodes.set(id,new E()); return nodes.get(id); };
const requests = [];
const ctx = {AbortController,Date,Set,Number,JSON,Error,
  document:{hidden:false,getElementById:get,createElement:()=>new E(),querySelectorAll:()=>[],addEventListener(){}},
  clearTimeout(){},setTimeout(){return 1},fetch(path,opts){return new Promise(resolve=>requests.push({path,opts,resolve}));}};
const run = s => vm.runInContext(s,ctx);
const reply = (req,status,body={}) => { assert(req); req.resolve({ok:status===200,status,json:async()=>body}); };
const fixtureTeam = (phase='done', summary='') => ({instance_id:'old-team',phase,assignments:[],summary});
const setRows = () => run("teamRows[0].provider.value='openrouter';teamRows[0].privacy.value='zdr';teamRows[0].model.value='one';teamRows[0].key.value='fixture-one';teamRows[1].provider.value='deepseek';teamRows[1].privacy.value='standard';teamRows[1].model.value='two';teamRows[1].key.value='fixture-two'");
const newSession = () => run("session={role:'administrator',csrf:'fresh'};agentSnapshot={sessions:{},agents:[],team:null};renderTeam(null)");
(async()=>{
  get('action').value='resource.probe'; vm.createContext(ctx); run(fs.readFileSync(process.argv[2],'utf8'));
  reply(requests.shift(),401); await new Promise(r=>setImmediate(r)); newSession(); setRows();
  // Accidental addition is reversible without clearing the other keys.
  assert.equal(run('teamRows.length'),2); get('team-add').listeners.click();
  assert.equal(run('teamRows.length'),3); run("teamRows[2].key.value='fixture-third'");
  get('team-remove').listeners.click(); assert.equal(run('teamRows.length'),2);
  assert.equal(run('teamRows[0].key.value'),'fixture-one');
  assert(get('team-remove').disabled);
  // Polling unchanged results must not replace the DOM being selected/copied.
  run("agentSnapshot.team={instance_id:'old-team',phase:'done',summary:'summary',assignments:[{provider:'openrouter',model:'one',privacy:'zdr',phase:'done',task:'task',result:'result'}]};renderTeam(agentSnapshot.team)");
  const existingResult = get('team-results').children[0];
  assert(existingResult); run('renderTeam(agentSnapshot.team)');
  assert.strictEqual(get('team-results').children[0],existingResult);
  // Existing completed result does not mask a rejected new request.
  run("agentSnapshot.team={instance_id:'old-team',phase:'done',assignments:[],summary:''};renderTeam(agentSnapshot.team)");
  get('team-task').value='fixture task';
  const failedStart = get('team-start').listeners.click(); const failedReq = requests.shift();
  assert.equal(failedReq.path,'/api/team/start');
  assert(get('team-add').disabled && get('team-remove').disabled && get('team-start').disabled);
  assert(run('teamRows.every(r=>r.provider.disabled && r.model.disabled && r.key.disabled)'));
  get('team-add').listeners.click(); assert.equal(run('teamRows.length'),2);
  reply(failedReq,400); await failedStart;
  assert(get('team-status').textContent.includes('拒絕'));
  run('renderTeam(agentSnapshot.team)'); assert(get('team-status').textContent.includes('拒絕'));
  // Failed stop stays visible rather than reporting the previous running state.
  run("agentSnapshot.team={instance_id:'old-team',phase:'running',assignments:[],summary:''};renderTeam(agentSnapshot.team)");
  const failedStop = get('team-stop').listeners.click(); const stopReq = requests.shift();
  assert.equal(stopReq.path,'/api/team/stop'); assert(get('team-stop').disabled);
  reply(stopReq,409); await failedStop; assert(get('team-status').textContent.includes('拒絕'));
  run('renderTeam(agentSnapshot.team)'); assert(get('team-status').textContent.includes('拒絕'));
  // A late start response from a previous login cannot clear the next user's
  // keys, overwrite their task, or unlock their own pending request.
  run("agentSnapshot.team={instance_id:'old-team',phase:'done',assignments:[],summary:''};renderTeam(agentSnapshot.team)");
  const oldStart=get('team-start').listeners.click(), oldReq=requests.shift();
  run('signedOut()'); newSession(); setRows(); get('team-task').value='new task';
  const newStart=get('team-start').listeners.click(), newReq=requests.shift();
  reply(oldReq,200,fixtureTeam('planning','old secret')); await oldStart;
  assert.equal(run('teamRows[0].key.value'),'fixture-one'); assert.equal(run('teamRows[1].key.value'),'fixture-two');
  assert.equal(run('agentSnapshot.team'),null); assert.equal(run('teamBusy'),true);
  assert(get('team-start').disabled);
  reply(newReq,400); await newStart;
  // A late stop response must not expose the previous account's output.
  run("agentSnapshot.team={instance_id:'old-team',phase:'running',assignments:[],summary:'private old'};renderTeam(agentSnapshot.team)");
  const oldStop=get('team-stop').listeners.click(), oldStopReq=requests.shift();
  run('signedOut()'); newSession(); setRows();
  reply(oldStopReq,200,fixtureTeam('stopped','private old')); await oldStop;
  assert.equal(run('agentSnapshot.team'),null); assert.equal(get('team-summary').textContent,'');
  assert.equal(run('teamRows[0].key.value'),'fixture-one');
  console.log('independent team UI checks passed');
})().catch(error=>{console.error(error);process.exitCode=1});
''', encoding='utf-8')
    job = JobProcess([binary, str(script), str(ROOT / 'web/static/app.js')], cwd=tmp_path, capture_output=True)
    try:
        job.resume()
        code = job.wait(10)
        assert job.wait_empty(3)
        stdout = job.stdout.read()
        assert code == 0
        assert b'independent team UI checks passed' in stdout
    finally:
        job.close()
