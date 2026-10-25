'use strict';
const $ = id => document.getElementById(id);
const pages = {
  overview: ['工作總覽', '從任務到證據，掌握目前進度。'],
  board: ['任務看板', '正式任務生命週期，以儲存庫中的任務卡為準。'],
  monitor: ['Agent 監控', 'Runtime 租約與已記錄的程序收據；需要時再做即時檢查。'],
  workspaces: ['工作區', '已登記的隔離工作區與固定基底，保留候選成果。'],
  reviews: ['審查中心', '正式審查紀錄與 SHA 收據；執行操作時仍需重新核對。'],
  events: ['事件紀錄', '依序列增量讀取，每次最多 50 筆，畫面保留最近 100 筆。'],
  handoff: ['跨機交接', 'GitHub 證據與派發收據快照；自動接單由對方的前景 watch 執行。'],
  settings: ['設定與操作', '查看目前設定，透過 Controller 預覽及確認受控操作。']
};
let session = null, view = 'overview', offset = 0, cursor = 0, eventRows = [];
let handoffSnapshot = null, handoffSignature = '';
let timer = null, pending = null, generation = 0, plan = null, actionBusy = false, revision = 0, authGeneration = 0;
function node(tag, content, cls) { const n = document.createElement(tag); if (content !== undefined) n.textContent = content; if (cls) n.className = cls; return n; }
function showError(message) { $('error').textContent = message; }
async function api(path, body, signal) {
  const requestSession = session;
  const headers = {}; if (body !== undefined) { headers['Content-Type'] = 'application/json'; if (session) headers['X-CSRF-Token'] = session.csrf; }
  const response = await fetch(path, {method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body), signal, credentials: 'same-origin', cache: 'no-store'});
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401 && requestSession && session === requestSession) signedOut();
    throw new Error(response.status === 401 ? '登入資料不正確或登入已逾時。' : response.status === 403 ? '權限或來源檢查未通過。' : response.status === 429 ? '要求過於頻繁，請稍後再試。' : '要求被拒絕，請更新狀態後重新預覽。');
  }
  return data;
}
function signedOut() {
  authGeneration++; session = null; generation++; clearTimeout(timer); if (pending) pending.abort(); pending = null;
  handoffSnapshot = null; handoffSignature = '';
  clearPlan(); $('console').hidden = true; $('login').hidden = false; $('token').value = '';
  $('action-result').textContent = ''; $('action-result').hidden = true; $('confirm').hidden = true;
  $('content').replaceChildren(); eventRows = []; cursor = 0; $('username').focus();
}
function signedIn(data) {
  authGeneration++; session = data; $('login').hidden = true; $('console').hidden = false;
  $('identity').textContent = data.username; $('role').textContent = {viewer:'Viewer · 檢視',operator:'Operator · 操作',administrator:'Administrator · 管理'}[data.role];
  $('token').value = ''; $('login-error').textContent = ''; navigate('overview');
}
function schedule() { clearTimeout(timer); if (session) timer = setTimeout(refresh, document.hidden ? 60000 : 5000); }
function navigate(name) {
  generation++; if (pending) pending.abort(); pending = null; clearTimeout(timer);
  view = name; offset = 0; cursor = 0; eventRows = []; clearPlan();
  $('title').textContent = pages[name][0]; $('subtitle').textContent = pages[name][1];
  for (const button of document.querySelectorAll('nav button')) { if (button.dataset.view === name) button.setAttribute('aria-current','page'); else button.removeAttribute('aria-current'); }
  $('operations').hidden = !['settings','handoff'].includes(name) || session.role === 'viewer';
  $('action-form').hidden = name !== 'settings'; $('inspect-form').hidden = name !== 'settings';
  $('handoff-controls').hidden = name !== 'handoff';
  if (name === 'handoff') { handoffSnapshot = null; handoffSignature = ''; $('handoff-controls').hidden = true; }
  $('confirm').hidden = true; $('action-result').hidden = true; $('action-message').textContent = '';
  $('content').replaceChildren(node('p', '讀取實際狀態中…', 'note'));
  refresh();
}
function panel(title) { const p = node('section', undefined, 'panel'); p.append(node('h2', title)); $('content').append(p); return p; }
function table(title, rows, fields) {
  const p = panel(title);
  if (!rows.length) { p.append(node('p', '此頁沒有紀錄。', 'empty')); return; }
  const wrap = node('div', undefined, 'table-wrap'); const t = node('table'); const head = node('thead'); const h = node('tr');
  for (const [,label] of fields) h.append(node('th', label)); head.append(h); t.append(head);
  const body = node('tbody');
  for (const row of rows) { const tr = node('tr'); for (const [key] of fields) { let v = row[key]; if (v === null || v === undefined || v === '') v = '—'; else if (typeof v === 'object') v = JSON.stringify(v); tr.append(node('td', String(v))); } body.append(tr); }
  t.append(body); wrap.append(t); p.append(wrap);
}
function render(data) {
  $('content').replaceChildren(); $('project').textContent = data.project_id;
  $('connection').textContent = data.runtime_available ? '已連線 · 實際後端資料' : 'Runtime 未啟用 · 僅任務板資料';
  $('updated').textContent = '更新於 ' + new Date(data.sampled_ms).toLocaleTimeString('zh-TW');
  $('previous').hidden = view === 'events' || offset === 0; $('next').hidden = !data.more;
  $('page-info').textContent = data.total === undefined ? '' : `第 ${Math.floor(offset / 100) + 1} 頁 · 共 ${data.total} 筆`;
  if (view !== 'handoff' && !data.runtime_available) $('content').append(node('p', '找不到指定的 runtime 資料庫。尚未啟用的資料不會顯示為零或健康。', 'note'));
  if (view === 'overview') {
    const stats = node('div', undefined, 'stats');
    for (const [label,value,hint] of [['任務總數',data.board_total,'正式任務卡'],['進行中',(data.board_counts || {}).IN_PROGRESS || 0,'任務板狀態'],['待審查',(data.board_counts || {}).REVIEW || 0,'等待正式審查'],['Runtime 登記執行',data.active_runs ?? '—','含待恢復；須即時核對']]) { const box = node('div', undefined, 'stat'); box.append(node('div',label,'stat-label'),node('div',String(value),'stat-value'),node('div',hint,'stat-hint')); stats.append(box); }
    $('content').append(stats);
    table('任務生命週期', Object.entries(data.board_counts || {}).map(([status,count]) => ({status,count})), [['status','狀態'],['count','任務數']]);
    const p = panel('目前執行邊界'); p.append(node('p', `模式：${data.mode || '尚未啟用'} · 資源保護：${data.breaker ? data.breaker.state : '無資料'}。權限與 Controller 安全檢查同時生效；提供者啟動與正式發布另有階段門檻。`));
  } else if (view === 'board') table('任務清單', data.rows || [], [['task_id','任務 ID'],['status','狀態'],['owner','負責人'],['phase','階段'],['dependencies','相依任務']]);
  else if (view === 'monitor') table('租約與歷史程序收據', data.rows || [], [['run_id','執行 ID'],['owner','負責人'],['phase','Runtime 階段'],['fence','Fence'],['lease_until_ms','租約期限 ms'],['heartbeat_ms','心跳 ms'],['receipt','已記錄 PID／退出／程序樹']]);
  else if (view === 'workspaces') table('已登記工作區（不代表即時 Git 驗證）', data.rows || [], [['run_id','執行 ID'],['task_id','任務'],['status','狀態'],['base_sha','固定基底 SHA'],['path_digest','路徑摘要']]);
  else if (view === 'reviews') {
    table('正式審查紀錄（歷史）', data.reviews || [], [['task_id','任務'],['decision','已記錄決定'],['sha256','紀錄摘要']]);
    table('證據 SHA 收據（歷史）', (data.evidence || {}).rows || [], [['evidence_id','證據'],['status','狀態'],['candidate_sha','Candidate'],['tested_sha','Tested'],['reviewed_sha','Reviewed']]);
    table('發布收據（歷史）', (data.publications || {}).rows || [], [['evidence_id','證據'],['status','狀態'],['integrated_sha','Integrated']]);
    $('next').hidden = !data.more && !(data.evidence || {}).more && !(data.publications || {}).more;
  } else if (view === 'events') {
    const seen = new Set(eventRows.map(r => r.sequence)); eventRows.push(...(data.rows || []).filter(r => !seen.has(r.sequence))); eventRows = eventRows.slice(-100); cursor = data.cursor ?? cursor;
    table('Controller 事件', eventRows, [['sequence','序列'],['event_type','事件'],['task_id','任務'],['run_id','執行'],['agent_id','來源'],['timestamp_ms','時間 ms']]);
    $('next').textContent = '讀取後續事件'; $('page-info').textContent = `游標 ${cursor} · 顯示 ${eventRows.length} 筆`;
  } else if (view === 'handoff') {
    renderHandoff(data.handoff);
  } else if (view === 'settings') {
    const keys = [['mode','執行模式'],['capacity','容量'],['schema_version','Runtime schema'],['breaker','資源保護'],['minimum_disk_bytes','最低磁碟 bytes'],['minimum_memory_bytes','最低可用記憶體 bytes'],['maximum_memory_load','最高記憶體負載 %'],['visible_poll_seconds','前景輪詢秒'],['hidden_poll_seconds','背景輪詢秒']];
    table('目前設定（唯讀）', data.runtime_available ? keys.map(([key,label]) => ({label,value:data[key]})) : [], [['label','設定'],['value','目前值']]);
    if (session.role === 'viewer') $('content').append(node('p', 'Viewer 僅有檢視權限。操作與執行權限會由伺服器再次檢查。', 'note'));
  }
  if (view !== 'events') $('next').textContent = '下一頁';
}
function dispatchArgs() {
  if (!handoffSnapshot) return null;
  const task = (handoffSnapshot.ready_tasks || []).find(t => t.task_id === $('handoff-task').value);
  const peer = (handoffSnapshot.peers || []).find(p => p.machine_id === $('handoff-peer').value);
  if (!task || !peer || task.owner !== peer.owner || !handoffSnapshot.code_revision || !handoffSnapshot.queue_head) return null;
  return {task_id:task.task_id,machine_id:peer.machine_id,expected_card_sha256:task.card_sha256,
    expected_revision:handoffSnapshot.code_revision,expected_queue_head:handoffSnapshot.queue_head};
}
function handoffBinding() {
  const args = dispatchArgs(); $('handoff-binding').textContent = args ? JSON.stringify(args,null,2) : '尚無可派發且負責人相符的任務／目標。先完成外部設定並明確同步。';
  $('handoff-preview').disabled = !args;
}
function handoffPeers() {
  const selected = $('handoff-peer').value;
  const task = (handoffSnapshot.ready_tasks || []).find(t => t.task_id === $('handoff-task').value);
  $('handoff-peer').replaceChildren();
  for (const peer of handoffSnapshot.peers || []) if (task && peer.owner === task.owner) {
    const option = node('option', `${peer.machine_id} · ${peer.owner}`); option.value = peer.machine_id; $('handoff-peer').append(option);
  }
  if ([...$('handoff-peer').options].some(o => o.value === selected)) $('handoff-peer').value = selected;
  handoffBinding();
}
function renderHandoff(h) {
  handoffSnapshot = h;
  $('connection').textContent = h.configured ? '本機快照 · 非即時在線狀態' : '跨機交接尚未設定';
  const synced = h.last_sync_ms ? new Date(h.last_sync_ms).toLocaleString('zh-TW') : '尚未成功同步';
  const age = h.last_sync_ms ? `${Math.max(0, Math.floor((Date.now()-h.last_sync_ms)/1000))} 秒前` : '未知';
  const p = panel('同步狀態與版本');
  p.append(node('p', `最近成功同步：${synced}（${age}）`), node('p', `程式版本：${h.code_revision || '未知'} · 佇列版本：${h.queue_head || '未知'}`));
  if (h.last_error) p.append(node('p', `最近錯誤：${h.last_error}。保留的快照不代表目前可連線。`, 'error'));
  if (!h.configured || !h.initialized) p.append(node('p','尚未完成外部 handoff 設定／初始化。依 GitHub handoff 操作指南準備自己的設定，明確執行 CLI init；控制台不會建立憑證或自動啟動。','note'));
  p.append(node('p', '瀏覽與每 5 秒更新只讀取本機快照，不會 fetch、派工或啟動 Agent。週期同步／接單由獨立前景 watch 負責。'));
  table('驗收證據（依版本保留 PASS／FAIL／INVALID／STALE）', h.acceptance || [], [['ref','證據分支'],['tested_commit','測試版本'],['evidence_commit','證據版本'],['status','驗證狀態'],['test_count','測試數'],['verified_ms','驗證時間 ms']]);
  table('派發與執行收據（不是正式 DONE）', h.dispatches || [], [['task_id','任務'],['machine_id','電腦'],['owner','負責人'],['status','RECEIVED／RUNNING／FINISHED／FAILED／UNKNOWN'],['exit_code','退出碼'],['dispatch_id','派發 ID']]);
  table('既有 READY 卡片', h.ready_tasks || [], [['task_id','任務'],['owner','負責人'],['card_sha256','卡片 SHA256']]);
  if (session.role === 'viewer') p.append(node('p','Viewer 僅能檢視快照；Operator 可預覽，Administrator 才能自行確認一次執行。','note'));
  $('handoff-controls').hidden = !h.configured || !h.initialized || session.role === 'viewer';
  const signature = JSON.stringify([h.configured,h.initialized,h.code_revision,h.queue_head,h.ready_tasks,h.peers]);
  if (signature !== handoffSignature) {
    handoffSignature = signature; clearPlan();
    const selected = $('handoff-task').value; $('handoff-task').replaceChildren();
    for (const task of h.ready_tasks || []) { const option = node('option',`${task.task_id} · ${task.owner}`); option.value = task.task_id; $('handoff-task').append(option); }
    if ([...$('handoff-task').options].some(o => o.value === selected)) $('handoff-task').value = selected;
    handoffPeers();
  }
}
async function refresh() {
  if (!session || pending) return;
  const current = generation, controller = new AbortController(); pending = controller;
  $('refresh').disabled = true;
  $('previous').disabled = true; $('next').disabled = true;
  try {
    const data = await api(`/api/view?name=${view}&offset=${offset}&after=${cursor}&limit=50`, undefined, controller.signal);
    if (current === generation && session) { showError(''); render(data); }
  } catch (error) { if (error.name !== 'AbortError' && current === generation && session) { showError(error.message); $('connection').textContent = '更新失敗 · 保留上次資料'; } }
  finally { if (pending === controller) { pending = null; $('refresh').disabled = false; $('previous').disabled = false; $('next').disabled = false; schedule(); } }
}
const actionFields = {'resource.probe':[], 'resource.reset':['expected_sequence'], 'recovery.reconcile':['run_id','request_id','expected_version','expected_fence','reason'], 'board.reconcile':['request_id'], 'board.cancel':['request_id'], 'parallel.disable':[]};
function clearPlan() { revision++; plan = null; $('confirm').hidden = true; }
function fields() {
  clearPlan(); $('action-fields').replaceChildren();
  for (const name of actionFields[$('action').value]) {
    const container = node('div'); const label = node('label', name); label.htmlFor = 'arg-' + name;
    const input = node('input'); input.id = 'arg-' + name; input.name = name; input.required = true;
    input.type = name.startsWith('expected_') ? 'number' : 'text'; input.maxLength = 100;
    if (input.type === 'number') { input.min = name === 'expected_fence' ? '1' : '0'; input.max = String(Number.MAX_SAFE_INTEGER); input.step = '1'; }
    if (name === 'reason') { input.placeholder = 'expired 或 interrupted'; input.pattern = 'expired|interrupted'; }
    container.append(label,input); $('action-fields').append(container);
  }
}
async function operation(path, body) {
  if (actionBusy) return;
  const currentRevision = revision, currentSession = session;
  actionBusy = true; $('action-message').textContent = '檢查中…';
  try {
    const result = await api(path, body);
    if (currentRevision !== revision || currentSession !== session) return;
    $('action-result').textContent = JSON.stringify(result,null,2); $('action-result').hidden = false;
    if (path === '/api/preview') { plan = result.plan; $('confirm').hidden = session.role !== 'administrator'; $('action-message').textContent = `預覽有效 60 秒。${session.role === 'administrator' ? '核對內容後可確認執行。' : '此帳號可預覽；執行需 Administrator 自行預覽確認。'}`; }
    else { clearPlan(); $('action-message').textContent = path === '/api/execute' ? 'Controller 已完成此操作。' : '即時檢查完成；結果僅代表檢查當時。'; refresh(); }
  } catch (error) { if (currentRevision === revision && currentSession === session) { clearPlan(); $('action-message').textContent = error.message; } }
  finally { actionBusy = false; }
}
$('login-form').addEventListener('submit', async event => { event.preventDefault(); const attempt = ++authGeneration, button = event.submitter; button.disabled = true; try { const data = await api('/api/login',{username:$('username').value,token:$('token').value}); if (attempt === authGeneration) signedIn(data); } catch(error) { if (attempt === authGeneration) $('login-error').textContent = error.message; } finally { button.disabled = false; } });
$('logout').addEventListener('click', async () => { try { await api('/api/logout',{}); signedOut(); } catch(error) { showError(error.message); } });
for (const button of document.querySelectorAll('nav button')) button.addEventListener('click', () => navigate(button.dataset.view));
$('refresh').addEventListener('click', refresh);
$('next').addEventListener('click', () => { if (pending) return; if (view !== 'events') offset += 100; refresh(); });
$('previous').addEventListener('click', () => { if (pending) return; offset = Math.max(0, offset - 100); refresh(); });
$('handoff-task').addEventListener('change', () => { clearPlan(); handoffPeers(); });
$('handoff-peer').addEventListener('change', () => { clearPlan(); handoffBinding(); });
$('handoff-sync').addEventListener('click', () => { clearPlan(); operation('/api/preview',{action:'handoff.sync',args:{}}); });
$('handoff-form').addEventListener('submit', event => { event.preventDefault(); clearPlan(); const args = dispatchArgs(); if (args) operation('/api/preview',{action:'handoff.dispatch',args}); });
$('action').addEventListener('change', fields); $('action-fields').addEventListener('input', clearPlan);
$('action-form').addEventListener('submit', event => { event.preventDefault(); clearPlan(); const args = {}; for (const name of actionFields[$('action').value]) args[name] = name.startsWith('expected_') ? Number($('arg-' + name).value) : $('arg-' + name).value; operation('/api/preview',{action:$('action').value,args}); });
$('inspect-form').addEventListener('submit', event => { event.preventDefault(); clearPlan(); operation('/api/inspect',{run_id:$('run-id').value}); });
$('confirm').addEventListener('click', () => { if (plan) { const token = plan; clearPlan(); operation('/api/execute',{plan:token}); } });
document.addEventListener('visibilitychange', () => { if (session) { if (document.hidden) schedule(); else { clearTimeout(timer); refresh(); } } });
fields();
const restoreGeneration = authGeneration;
api('/api/session').then(data => { if (authGeneration === restoreGeneration && !session) signedIn(data); }).catch(() => { if (authGeneration === restoreGeneration && !session) $('username').focus(); });
