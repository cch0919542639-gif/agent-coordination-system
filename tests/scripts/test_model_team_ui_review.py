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
const take = path => { const i=requests.findIndex(r=>r.path===path); assert(i>=0, path); return requests.splice(i,1)[0]; };
const posts = () => requests.filter(r=>r.opts?.method==='POST').length;
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
  const failedStart = get('team-start').listeners.click(); const failedReq = take('/api/team/start');
  assert.equal(failedReq.path,'/api/team/start');
  assert(get('team-add').disabled && get('team-remove').disabled && get('team-start').disabled);
  assert(run('teamRows.every(r=>r.provider.disabled && r.model.disabled && r.key.disabled)'));
  get('team-add').listeners.click(); assert.equal(run('teamRows.length'),2);
  reply(failedReq,400); await failedStart;
  assert(requests.some(r=>r.path.startsWith('/api/view?')));
  assert(get('team-status').textContent.includes('拒絕'));
  run('renderTeam(agentSnapshot.team)'); assert(get('team-status').textContent.includes('拒絕'));
  // Failed stop stays visible rather than reporting the previous running state.
  run("agentSnapshot.team={instance_id:'old-team',phase:'running',assignments:[],summary:''};renderTeam(agentSnapshot.team)");
  const failedStop = get('team-stop').listeners.click(); const stopReq = take('/api/team/stop');
  assert.equal(stopReq.path,'/api/team/stop'); assert(get('team-stop').disabled);
  reply(stopReq,409); await failedStop; assert(get('team-status').textContent.includes('拒絕'));
  run('renderTeam(agentSnapshot.team)'); assert(get('team-status').textContent.includes('拒絕'));
  // A late start response from a previous login cannot clear the next user's
  // keys, overwrite their task, or unlock their own pending request.
  run("agentSnapshot.team={instance_id:'old-team',phase:'done',assignments:[],summary:''};renderTeam(agentSnapshot.team)");
  const oldStart=get('team-start').listeners.click(), oldReq=take('/api/team/start');
  run('signedOut()'); newSession(); setRows(); get('team-task').value='new task';
  const newStart=get('team-start').listeners.click(), newReq=take('/api/team/start');
  reply(oldReq,200,fixtureTeam('planning','old secret')); await oldStart;
  assert.equal(run('teamRows[0].key.value'),'fixture-one'); assert.equal(run('teamRows[1].key.value'),'fixture-two');
  assert.equal(run('agentSnapshot.team'),null); assert.equal(run('teamBusy'),true);
  assert(get('team-start').disabled);
  reply(newReq,400); await newStart;
  // A late stop response must not expose the previous account's output.
  run("agentSnapshot.team={instance_id:'old-team',phase:'running',assignments:[],summary:'private old'};renderTeam(agentSnapshot.team)");
  const oldStop=get('team-stop').listeners.click(), oldStopReq=take('/api/team/stop');
  run('signedOut()'); newSession(); setRows();
  reply(oldStopReq,200,fixtureTeam('stopped','private old')); await oldStop;
  assert.equal(run('agentSnapshot.team'),null); assert.equal(get('team-summary').textContent,'');
  assert.equal(run('teamRows[0].key.value'),'fixture-one');
  // Native agents require explicit workspace acknowledgement; their row does not send an API key.
  run("teamRows[1].kind.value='opencode';teamRows[1].kind.listeners.change();renderTeam(null)");
  assert.equal(run('teamRows[1].model.value'),'');
  run("teamRows[1].model.value='native/model';teamRows[1].kind.value='direct';teamRows[1].kind.listeners.change()");
  assert.equal(run('teamRows[1].model.value'),'');
  run("teamRows[1].kind.value='opencode';teamRows[1].kind.listeners.change()");
  assert(run('teamRows[1].key.disabled && teamRows[1].provider.disabled'));
  get('team-task').value='fixture task'; get('team-workspace-ack').checked=false;
  await get('team-start').listeners.click(); assert.equal(posts(),0);
  const checkSource=get('team-workspace-check').listeners.click(), sourceReq=take('/api/team/workspace');
  reply(sourceReq,200,{repository:'C:/fixture',base_sha:'fixture-sha'}); await checkSource;
  assert(get('team-workspace-source').textContent.includes('C:/fixture'));
  get('team-workspace-ack').checked=true;
  get('team-task').value='a'.repeat(3001);
  await get('team-start').listeners.click(); assert.equal(posts(),0);
  assert(get('team-status').textContent.includes('3000'));
  get('team-task').value='fixture task';
  const staleStart=get('team-start').listeners.click(), staleStartReply=take('/api/team/start');
  reply(staleStartReply,409,{error:'專案版本已改變；請重新確認來源專案及版本。'}); await staleStart;
  assert.equal(run('teamWorkspace'),null); assert.equal(get('team-workspace-ack').checked,false);
  assert(get('team-workspace-source').textContent.includes('版本已改變'));
  const recheck=get('team-workspace-check').listeners.click(), recheckReq=take('/api/team/workspace');
  reply(recheckReq,200,{repository:'C:/fixture',base_sha:'fixture-sha'}); await recheck;
  get('team-workspace-ack').checked=true;
  run("if (pending) pending.abort();pending=null;view='agents'"); requests.length=0;
  const staleStartPoll=run('refresh()'), staleStartReq=take('/api/agents');
  const nativeStart=get('team-start').listeners.click(), nativeReq=take('/api/team/start');
  await run('refresh()'); assert(!requests.some(r=>r.path==='/api/agents'));
  const nativeBody=JSON.parse(nativeReq.opts.body);
  assert.deepEqual(nativeBody.workers[1],{kind:'opencode',model:''});
  assert.equal(nativeBody.workspace_ack,true);
  assert.equal(nativeBody.workspace_base,'fixture-sha');
  reply(nativeReq,200,{instance_id:'team-native',phase:'running',summary:'',assignments:[]});
  await nativeStart;
  assert(requests.some(r=>r.path==='/api/agents'));
  reply(staleStartReq,200,{sessions:{},agents:[],team:null}); await staleStartPoll;
  assert.equal(run('agentSnapshot.team.instance_id'),'team-native');
  // Each visible approval is bound to its team, worker, and request token.
  run("agentSnapshot.team={instance_id:'team-native',phase:'running',summary:'',assignments:[{provider:'hermes',model:'fixture',phase:'running',task:'edit',workspace:'C:/fixture',changes:[],permission:{token:'permission-token',title:'Approve edit',details:'fixture',options:[{id:'deny',kind:'reject_once'}]}}]};renderTeam(agentSnapshot.team)");
  run('if (pending) pending.abort();pending=null'); requests.length=0;
  const stalePermissionPoll=run('refresh()'), stalePermissionReq=take('/api/agents');
  const row=get('team-results').children[0], approval=row.children.find(item=>item.listeners.click);
  assert(approval); const answer=approval.listeners.click(), answerReq=take('/api/team/permission');
  assert.equal(answerReq.path,'/api/team/permission');
  assert.deepEqual(JSON.parse(answerReq.opts.body),{instance_id:'team-native',index:0,token:'permission-token',choice:'deny'});
  reply(answerReq,200,{instance_id:'team-native',phase:'running',summary:'',assignments:[]});await answer;
  assert(requests.some(r=>r.path==='/api/agents'));
  reply(stalePermissionReq,200,{sessions:{},agents:[],team:null}); await stalePermissionPoll;
  assert.equal(run('agentSnapshot.team.instance_id'),'team-native');
  run('if (pending) pending.abort();pending=null'); requests.length=0;
  const staleStopPoll=run('refresh()'), staleStopReq=take('/api/agents');
  const stop=get('team-stop').listeners.click(), goodStop=take('/api/team/stop');
  reply(goodStop,200,{instance_id:'team-native',phase:'stopped',summary:'',assignments:[]}); await stop;
  assert(requests.some(r=>r.path==='/api/agents'));
  reply(staleStopReq,200,{sessions:{},agents:[],team:{instance_id:'team-native',phase:'running'}}); await staleStopPoll;
  assert.equal(run('agentSnapshot.team.phase'),'stopped');
  // Saving never returns the key; later team calls refer to the saved credential.
  run("if (pending) pending.abort();pending=null;teamRows[1].kind.value='direct';teamRows[1].kind.listeners.change();teamRows[1].provider.value='deepseek';teamRows[1].key.value='synthetic-key';teamRows[1].model.value='model-two';teamRows[0].key.value='synthetic-first';teamRows[0].model.value='model-one';renderTeam(agentSnapshot.team)");
  requests.length=0;
  const save=run('teamRows[1].credentials.save.listeners.click()'), saveReq=take('/api/keys/save');
  assert.equal(JSON.parse(saveReq.opts.body).api_key,'synthetic-key');
  run("teamRows[1].key.value='synthetic-new';teamRows[1].key.listeners.input();renderAgents(agentSnapshot)");
  assert(run('teamRows[1].credentials.save.disabled && teamRows[0].credentials.remove.disabled'));
  assert(get('team-start').disabled);
  await run('teamRows[0].credentials.remove.listeners.click()');
  assert(!requests.some(r=>r.path==='/api/keys/delete'));
  reply(saveReq,200,{saved:true}); await save;
  assert.equal(run('teamRows[1].key.value'),'synthetic-new'); assert(!run('teamRows[1].credentials.use.checked'));
  const saveNew=run('teamRows[1].credentials.save.listeners.click()'), saveNewReq=take('/api/keys/save');
  assert.equal(JSON.parse(saveNewReq.opts.body).api_key,'synthetic-new');
  reply(saveNewReq,200,{saved:true}); await saveNew;
  assert.equal(run('teamRows[1].key.value'),''); assert(run('teamRows[1].credentials.use.checked'));
  const storedStart=get('team-start').listeners.click(), storedReq=take('/api/team/start');
  const stored=JSON.parse(storedReq.opts.body).workers[1];
  assert.equal(stored.use_saved,true); assert.equal(stored.api_key,'');
  reply(storedReq,400,{}); await storedStart;
  // A hung credential request releases controls and never reports success.
  ctx.setTimeout=fn=>{ctx.credentialTimeout=fn;return 1};
  ctx.fetch=(path,opts)=>new Promise((resolve,reject)=>{
    requests.push({path,opts,resolve});
    if(opts.signal) opts.signal.addEventListener('abort',()=>reject(Object.assign(new Error('abort'),{name:'AbortError'})));
  });
  run("teamRows[1].key.value='synthetic-timeout';teamRows[1].credentials.use.checked=false");
  const hungSave=run('teamRows[1].credentials.save.listeners.click()'); take('/api/keys/save');
  assert(run('credentialBusy')); ctx.credentialTimeout(); await hungSave;
  assert(!run('credentialBusy')); assert(run("teamRows[1].credentials.status.textContent.includes('結果未確認')"));
  const check=run('teamRows[1].credentials.check.listeners.click()'), checkReq=take('/api/keys/status');
  reply(checkReq,200,{saved:true}); await check;
  assert(run("teamRows[1].credentials.status.textContent.includes('無法檢查其內容')"));
  // Logout and a fresh login cannot inherit a permanently blocked operation.
  const hungAgain=run('teamRows[1].credentials.save.listeners.click()'); take('/api/keys/save');
  run('signedOut()'); newSession(); ctx.credentialTimeout(); await hungAgain;
  assert(!run('credentialBusy'));
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
