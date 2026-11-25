'use strict';
const $ = id => document.getElementById(id);
const pages = {
  overview: ['工作總覽', '從任務到證據，掌握目前進度。'],
  board: ['任務看板', '正式任務生命週期，以儲存庫中的任務卡為準。'],
  monitor: ['Agent 監控', 'Runtime 租約與已記錄的程序收據；需要時再做即時檢查。'],
  agents: ['Agent 操控', '在各 Agent 的可用清單中選擇提供者與模型，手動啟動及監控。'],
  workspaces: ['工作區', '已登記的隔離工作區與固定基底，保留候選成果。'],
  reviews: ['審查中心', '正式審查紀錄與 SHA 收據；執行操作時仍需重新核對。'],
  events: ['事件紀錄', '依序列增量讀取，每次最多 50 筆，畫面保留最近 100 筆。'],
  handoff: ['跨機交接', 'GitHub 證據與派發收據快照；自動接單由對方的前景 watch 執行。'],
  settings: ['設定與操作', '查看目前設定，透過 Controller 預覽及確認受控操作。']
};
let session = null, view = 'overview', offset = 0, cursor = 0, eventRows = [];
let handoffSnapshot = null, handoffSignature = '';
let agentSnapshot = null, agentSignature = '', permissionSignature = '', agentBusy = false, agentActionError = '', agentActionMessage = '';
let agentPromptSent = {}, directCatalogGeneration = 0, directRenderedInstance = '';
let teamRows = [], teamBusy = false, teamActionError = '', teamResultsSignature = '', teamActionGeneration = 0, teamWorkspace = null;
let timer = null, pending = null, generation = 0, plan = null, actionBusy = false, revision = 0, authGeneration = 0;
const staleWorkspaceMessage = '專案版本已改變；請重新確認來源專案及版本。';
function node(tag, content, cls) { const n = document.createElement(tag); if (content !== undefined) n.textContent = content; if (cls) n.className = cls; return n; }
function showError(message) { $('error').textContent = message; }
function showPrivacyNote() {
  if (($('direct-provider').value || 'openrouter') !== 'openrouter') {
    $('direct-privacy-note').textContent = '此供應商的資料保留政策由供應商決定；主控台不提供或驗證零資料保留路由。'; return;
  }
  $('direct-privacy-note').textContent = $('direct-privacy').value === 'standard'
    ? '一般模式不要求零資料保留或拒絕資料收集；內容可能依供應商政策被保存或用於訓練。'
    : '零資料保留模式只使用符合條件的端點。';
}
async function api(path, body, signal) {
  const requestSession = session;
  const headers = {}; if (body !== undefined) { headers['Content-Type'] = 'application/json'; if (session) headers['X-CSRF-Token'] = session.csrf; }
  const response = await fetch(path, {method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body), signal, credentials: 'same-origin', cache: 'no-store'});
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401 && requestSession && session === requestSession) signedOut();
    if (path === '/api/login' && response.status === 429) throw new Error('登入次數過多或工作階段已滿；請稍後再試，或勾選結束此帳號其他工作階段。');
    if (path === '/api/agent/report' && response.status === 503) throw new Error('回報結果未確認；請先在 Codex 檢查佇列，避免重送。');
    if (path === '/api/agent/report' && response.status === 409) throw new Error('回覆已變更、尚未完成，或本輪已送出；請先檢查 Codex 佇列。');
    if (path === '/api/team/start' && response.status === 503) throw new Error('先前模型程序停止狀態未確認；請檢查並重新啟動主控台。');
    if (path === '/api/team/start' && response.status === 409 && data?.error === '此 Hermes 版本的共享後端尚未通過主控台防護驗證。') throw new Error(data.error);
    if (path === '/api/team/start' && response.status === 409 && data?.error === staleWorkspaceMessage) throw new Error(staleWorkspaceMessage);
    if ((path === '/api/team/start' || path === '/api/agent/start') && response.status === 409 && data?.error === '找不到此供應商及網址的已保存金鑰。') throw new Error(data.error);
    if (path.startsWith('/api/keys/') && response.status === 503) throw new Error('本機 Windows 憑證管理員無法使用；可改用手動輸入。');
    if (path === '/api/agent/prompt' && body?.agent === 'direct' && response.status === 409) throw new Error('送出已拒絕：工作階段可能已變更或尚未就緒；請更新畫面並確認模型與隱私模式。');
    if (path.startsWith('/api/agent/') && response.status === 413) throw new Error('指示超過可傳送大小，請縮短內容。');
    if (path.startsWith('/api/agent/') && response.status === 409) throw new Error('操作被拒絕；請確認 Agent 已連線並選好模型。');
    throw new Error(response.status === 401 ? '登入資料不正確或登入已結束。' : response.status === 403 ? '權限或來源檢查未通過。' : response.status === 429 ? '要求過於頻繁，請稍後再試。' : '要求被拒絕，請更新狀態後重新預覽。');
  }
  return data;
}
function signedOut() {
  authGeneration++; session = null; generation++; clearTimeout(timer); if (pending) pending.abort(); pending = null;
  handoffSnapshot = null; handoffSignature = '';
  agentSnapshot = null; agentSignature = ''; permissionSignature = ''; agentActionError = ''; agentActionMessage = ''; agentPromptSent = {}; directRenderedInstance = '';
  for (const id of ['agent-prompt','agent-response','agent-activity','agent-permission-title','agent-permission-details','agent-error','agent-current']) $(id).textContent = '';
  $('agent-prompt').value = ''; $('agent-permission').hidden = true; $('agent-permission-options').replaceChildren(); $('agent-model').replaceChildren();
  $('direct-key').value = ''; $('direct-model').value = ''; $('direct-provider').value = 'openrouter'; $('direct-base-url').value = ''; $('direct-base-field').hidden = true; resetDirectModels();
  $('direct-privacy').value = 'zdr'; $('direct-privacy-note').textContent = '零資料保留模式只使用符合條件的端點。';
  directCredentials.reset();
  for (const row of teamRows) row.key.value = '';
  teamRows = []; teamBusy = false; teamActionError = ''; teamResultsSignature = ''; teamActionGeneration++; $('team-workers').replaceChildren();
  $('team-results').replaceChildren(); $('team-summary').textContent = ''; $('team-task').value = ''; $('team-workspace-ack').checked = false;
  teamWorkspace = null; $('team-workspace-source').textContent = '使用原生 Agent 前請確認來源專案與版本。';
  $('close-other-sessions').checked = false;
  $('direct-model-status').textContent = '也可以直接輸入 OpenRouter 模型 ID。';
  clearPlan(); $('console').hidden = true; $('login').hidden = false; $('token').value = '';
  $('action-result').textContent = ''; $('action-result').hidden = true; $('confirm').hidden = true;
  $('content').replaceChildren(); eventRows = []; cursor = 0; $('username').focus();
}
function signedIn(data) {
  authGeneration++; session = data; $('login').hidden = true; $('console').hidden = false;
  $('identity').textContent = data.username; $('role').textContent = {viewer:'Viewer · 檢視',operator:'Operator · 操作',administrator:'Administrator · 管理'}[data.role];
  $('token').value = ''; $('login-error').textContent = ''; navigate('overview');
}
function schedule() { clearTimeout(timer); if (session) timer = setTimeout(refresh, document.hidden ? 60000 : view === 'agents' ? 2000 : 5000); }
function navigate(name) {
  generation++; if (pending) pending.abort(); pending = null; clearTimeout(timer);
  view = name; offset = 0; cursor = 0; eventRows = []; clearPlan();
  $('title').textContent = pages[name][0]; $('subtitle').textContent = pages[name][1];
  for (const button of document.querySelectorAll('nav button')) { if (button.dataset.view === name) button.setAttribute('aria-current','page'); else button.removeAttribute('aria-current'); }
  $('operations').hidden = !['settings','handoff'].includes(name) || session.role === 'viewer';
  $('action-form').hidden = name !== 'settings'; $('inspect-form').hidden = name !== 'settings';
  $('handoff-controls').hidden = name !== 'handoff';
  $('agent-panel').hidden = name !== 'agents'; $('content').hidden = name === 'agents';
  if (name === 'agents') { agentSignature = ''; $('previous').hidden = true; $('next').hidden = true; $('page-info').textContent = ''; }
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
  if (!session || pending || teamBusy) return;
  const current = generation, controller = new AbortController(); pending = controller;
  $('refresh').disabled = true;
  $('previous').disabled = true; $('next').disabled = true;
  try {
    const data = await api(view === 'agents' ? '/api/agents' : `/api/view?name=${view}&offset=${offset}&after=${cursor}&limit=50`, undefined, controller.signal);
    if (current === generation && session) { showError(''); if (view === 'agents') renderAgents(data); else render(data); }
  } catch (error) { if (error.name !== 'AbortError' && current === generation && session) { showError(error.message); $('connection').textContent = '更新失敗 · 保留上次資料'; } }
  finally { if (pending === controller) { pending = null; $('refresh').disabled = false; $('previous').disabled = false; $('next').disabled = false; schedule(); } }
}
function pauseTeamRefresh() {
  generation++; clearTimeout(timer); if (pending) pending.abort(); pending = null;
}
function renderAgents(data) {
  agentSnapshot = data;
  renderTeam(data.team);
  if (!$('codex-thread').value && data.codex_thread) $('codex-thread').value = data.codex_thread;
  const name = $('agent-kind').value, found = (data.agents || []).find(a => a.id === name), state = (data.sessions || {})[name];
  $('direct-config').hidden = name !== 'direct'; $('agent-model-field').hidden = name === 'direct';
  $('agent-prompt').maxLength = name === 'direct' ? 50000 : 8000;
  const phase = state ? state.phase : 'offline', admin = session.role === 'administrator';
  if (name === 'direct' && state?.privacy && !['failed','stopped'].includes(phase)) {
    const provider = state.provider || 'openrouter';
    if (state.instance_id && state.instance_id !== directRenderedInstance) {
      directRenderedInstance = state.instance_id;
      $('direct-model').value = state.model || ''; $('direct-key').value = ''; resetDirectModels();
      $('direct-model-status').textContent = '工作階段已變更，請確認供應商及模型。';
    }
    if (($('direct-provider').value || 'openrouter') !== provider) {
      $('direct-provider').value = provider; $('direct-key').value = ''; resetDirectModels();
    }
    if (provider === 'custom') $('direct-base-url').value = state.base_url || '';
    $('direct-base-field').hidden = provider !== 'custom';
    if ($('direct-privacy').value !== state.privacy) {
      resetDirectModels();
      $('direct-model-status').textContent = '隱私模式已變更，請重新取得模型清單或手動輸入 ID。';
    }
    $('direct-privacy').value = state.privacy; showPrivacyNote();
  }
  const directProvider = $('direct-provider').value || 'openrouter';
  $('direct-provider').disabled = !admin || agentBusy || !['offline','failed','stopped'].includes(phase);
  $('direct-base-url').disabled = $('direct-provider').disabled;
  $('direct-privacy').disabled = directProvider !== 'openrouter' || !admin || agentBusy || !['offline','failed','stopped'].includes(phase);
  if (name === 'direct' && state?.model && !$('direct-model').value) $('direct-model').value = state.model;
  $('direct-model-load').disabled = !admin || directProvider !== 'openrouter';
  $('connection').textContent = '本機 Agent 工作階段'; $('updated').textContent = '更新於 ' + new Date().toLocaleTimeString('zh-TW');
  $('agent-inventory').textContent = (data.agents || []).map(a => `${a.name}：${(data.sessions || {})[a.id]?.phase || (a.id === 'direct' ? (a.installed ? '已設定' : '未設定') : (a.installed ? '已安裝' : '未安裝'))}`).join(' · ');
  $('agent-role-note').hidden = admin;
  const emptyReply = phase === 'ready' && agentPromptSent[name] && !state?.response && !state?.error;
  $('agent-state').textContent = agentActionMessage || (emptyReply ? 'Agent 已回報結束，目前沒有文字回覆。' : ({offline:'尚未連線',starting:'連線中…',ready:'已連線',switching:'切換模型中…',running:'執行中，等待 Agent 回覆或操作授權…',failed:'連線失敗',stopped:'已停止'})[phase]) || phase;
  $('agent-error').textContent = agentActionError || state?.error || '';
  $('agent-current').textContent = '目前模型：' + (state?.model || '尚未選擇');
  const signature = JSON.stringify([name,state?.models || []]);
  if (signature !== agentSignature) {
    agentSignature = signature; $('agent-model').replaceChildren();
    for (const item of state?.models || []) { const opt = node('option',item.name); opt.value = item.id; $('agent-model').append(opt); }
    if ((state?.models || []).some(x => x.id === state?.model)) $('agent-model').value = state.model;
  }
  const directReady = name !== 'direct' || ((!!$('direct-key').value || directCredentials.use.checked) && !!$('direct-model').value.trim() && (directProvider !== 'custom' || !!$('direct-base-url').value.trim())) || (directProvider === 'openrouter' && found?.configured);
  for (const control of [directCredentials.use,directCredentials.save,directCredentials.remove]) control.disabled = !admin || agentBusy;
  $('agent-start').disabled = !admin || agentBusy || !found?.installed || !directReady || !['offline','failed','stopped'].includes(phase);
  $('agent-apply').disabled = !admin || agentBusy || phase !== 'ready' || !(state?.models || []).length;
  $('agent-send').disabled = !admin || agentBusy || phase !== 'ready' || !state?.model;
  $('agent-report').disabled = !admin || agentBusy || phase !== 'ready' || !state?.response || !!state?.error;
  $('agent-stop').disabled = !admin || agentBusy || ['offline','failed','stopped'].includes(phase);
  $('agent-response').textContent = state?.response || ''; $('agent-activity').textContent = (state?.activity || []).map(x => `${x.title} · ${x.status}`).join('\n');
  $('agent-permission').hidden = !state?.permission;
  if (state?.permission) {
    $('agent-permission-title').textContent = state.permission.title; $('agent-permission-details').textContent = state.permission.details;
    const signature = JSON.stringify([name,state.permission,admin]);
    if (signature !== permissionSignature) {
      permissionSignature = signature; $('agent-permission-options').replaceChildren();
      for (const choice of state.permission.options) {
        const button = node('button', choice.kind === 'allow_once' ? '允許這一次' : '拒絕', choice.kind === 'allow_once' ? 'primary' : 'secondary');
        button.type = 'button';
        button.addEventListener('click', () => agentAction('permission',{choice:choice.id})); $('agent-permission-options').append(button);
      }
    }
    for (const button of $('agent-permission-options').children) button.disabled = !admin || agentBusy;
  } else {
    permissionSignature = ''; $('agent-permission-options').replaceChildren();
    $('agent-permission-title').textContent = ''; $('agent-permission-details').textContent = '';
  }
}
async function agentAction(action, extra = {}) {
  if (agentBusy) return false;
  const selected = $('agent-kind').value, current = session; agentBusy = true;
  agentActionError = ''; agentActionMessage = action === 'prompt' ? '正在送出指示…' : '處理中…';
  generation++; clearTimeout(timer); if (pending) pending.abort(); pending = null;
  if (agentSnapshot) renderAgents(agentSnapshot);
  try {
    const state = await api('/api/agent/' + action, {agent:selected,...extra});
    if (current === session && agentSnapshot) {
      agentSnapshot.sessions[selected] = state;
      if (action === 'prompt') agentPromptSent[selected] = true;
      if (action === 'start' || action === 'stop') delete agentPromptSent[selected];
    }
    return true;
  } catch (error) { agentActionError = error.message; return false; }
  finally {
    agentBusy = false; agentActionMessage = '';
    if (agentSnapshot && current === session) { renderAgents(agentSnapshot); refresh(); }
  }
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
function addTeamWorker() {
  if (teamRows.length >= 4) return;
  const index = teamRows.length + 1, box = node('fieldset');
  box.append(node('legend', index === 1 ? '模型 1 · 規劃與彙整' : `模型 ${index}`));
  let fieldIndex = 0;
  function field(label, control) { const title = node('label', label); control.id = `team-worker-${index}-${++fieldIndex}`; title.htmlFor = control.id; box.append(title, control); }
  const kind = node('select');
  for (const [value, label] of (index === 1 ? [['direct','直接模型（規劃）']] : [['direct','直接模型'],['opencode','OpenCode'],['hermes','Hermes']])) {
    const option = node('option',label); option.value = value; kind.append(option);
  }
  const provider = node('select');
  for (const [value, label] of [['openrouter','OpenRouter'],['deepseek','DeepSeek'],['agnes','Agnes AI'],['custom','自訂 OpenAI 相容 API']]) {
    const option = node('option',label); option.value = value; provider.append(option);
  }
  const base = node('input'); base.type = 'url'; base.placeholder = '自訂 HTTPS API 基底網址';
  const model = node('input'); model.placeholder = '模型 ID'; model.maxLength = 200;
  const key = node('input'); key.type = 'password'; key.autocomplete = 'off'; key.maxLength = 512;
  const privacy = node('select');
  for (const [value,label] of [['zdr','零資料保留（OpenRouter）'],['standard','一般模式']]) { const option=node('option',label); option.value=value; privacy.append(option); }
  field('工作者類型', kind); field('供應商', provider); field('自訂 API 基底網址（僅自訂供應商）', base); field('模型 ID（原生 Agent 留空使用預設）', model); field('API Key', key); field('隱私模式', privacy);
  const credentials = credentialControls(box, provider, base, key);
  kind.addEventListener('change', () => { key.value = ''; model.value = ''; credentials.reset(); if (agentSnapshot) renderTeam(agentSnapshot.team); });
  provider.addEventListener('change', () => { key.value = ''; privacy.disabled = provider.value !== 'openrouter'; if (privacy.disabled) privacy.value = 'standard'; });
  teamRows.push({box,kind,provider,base,model,key,privacy,credentials}); $('team-workers').append(box);
}
function credentialControls(container, provider, base, key) {
  const save=node('button','保存金鑰'), remove=node('button','刪除已保存金鑰');
  save.type='button'; remove.type='button';
  const use=node('input'); use.type='checkbox'; const label=node('label'); label.append(use,node('span','使用已保存的金鑰'));
  const status=node('span',''); container.append(save,remove,label,status);
  let generation=0;
  const reset=()=>{ generation++; use.checked=false; status.textContent=''; };
  provider.addEventListener('change', reset); base.addEventListener('input', reset);
  key.addEventListener('input',()=>{ if (key.value) use.checked=false; });
  use.addEventListener('change',()=>{ if (agentSnapshot) renderAgents(agentSnapshot); });
  async function operate(action) {
    if (!session) return;
    const current=session, version=++generation, value=key.value;
    const body={provider:provider.value || 'openrouter',base_url:provider.value==='custom' ? base.value.trim() : ''};
    if (action==='save') { if (!value) { status.textContent='請先輸入 API Key。'; return; } body.api_key=value; }
    save.disabled=true; remove.disabled=true;
    try {
      await api('/api/keys/'+action,body);
      if (current!==session || generation!==version) return;
      if (action==='save') { if (key.value===value) key.value=''; use.checked=true; status.textContent='已保存在此 Windows 帳號。'; }
      else { use.checked=false; status.textContent='已刪除保存的金鑰。'; }
    } catch (error) { if (current===session && generation===version) status.textContent=error.message; }
    finally { if (current===session) { save.disabled=false; remove.disabled=false; if (agentSnapshot) renderAgents(agentSnapshot); } }
  }
  save.addEventListener('click',()=>operate('save')); remove.addEventListener('click',()=>operate('delete'));
  return {use,save,remove,reset};
}
const directCredentials=credentialControls($('direct-key-controls'), $('direct-provider'), $('direct-base-url'), $('direct-key'));
function renderTeam(team) {
  if (!teamRows.length) { addTeamWorker(); addTeamWorker(); }
  const active = team && ['starting','planning','running','summarizing','cleaning','stopping','cleanup_failed'].includes(team.phase);
  $('team-start').disabled = session.role !== 'administrator' || teamBusy || active;
  $('team-add').disabled = session.role !== 'administrator' || teamBusy || active || teamRows.length >= 4;
  $('team-remove').disabled = session.role !== 'administrator' || teamBusy || active || teamRows.length <= 2;
  $('team-stop').disabled = session.role !== 'administrator' || teamBusy || !active || ['cleaning','stopping','cleanup_failed'].includes(team?.phase);
  $('team-workspace-ack').disabled = session.role !== 'administrator' || teamBusy || active;
  $('team-workspace-check').disabled = session.role !== 'administrator' || teamBusy || active;
  for (const row of teamRows) {
    const locked = session.role !== 'administrator' || teamBusy || active;
    const direct = !row.kind.value || row.kind.value === 'direct';
    for (const control of [row.kind,row.model]) control.disabled = locked;
    for (const control of [row.provider,row.base,row.key]) control.disabled = locked || !direct;
    for (const control of [row.credentials.use,row.credentials.save,row.credentials.remove]) control.disabled = locked || !direct;
    row.privacy.disabled = locked || !direct || row.provider.value !== 'openrouter';
  }
  $('team-status').textContent = teamActionError || (team ? ({starting:'正在連線模型',planning:'正在拆分任務',running:'各模型執行中',summarizing:'正在彙整',cleaning:'正在清理模型程序',stopping:'正在停止模型程序',cleanup_failed:'程序停止狀態未確認',done:'已完成',failed:'任務未完全成功',stopped:'已停止'})[team.phase] + (team.error ? '：' + team.error : '') : '尚未執行');
  const signature = JSON.stringify([team?.assignments || [], team?.summary || '']);
  if (signature === teamResultsSignature) return;
  teamResultsSignature = signature;
  $('team-results').replaceChildren(); $('team-summary').textContent = team?.summary || '';
  for (const [i,row] of (team?.assignments || []).entries()) {
    const box=node('section'); box.append(node('h4', `工作者 ${i+1} · ${row.provider} · ${row.model} · ${row.phase}`), node('p', `隱私模式：${row.privacy || '依原生設定'}${row.base_url ? ' · 端點：' + row.base_url : ''}${row.workspace ? ' · 工作目錄：' + row.workspace : ''}`), node('p',row.task || '等待分工'),node('pre',row.result || row.error || ''));
    if (row.workspace) box.append(node('p', `基底提交：${team.base_sha || '未知'}；已追蹤與未忽略的變更：`), node('pre', (row.changes || []).join('\n') || '尚無可列出的變更'));
    if (row.activity?.length) box.append(node('pre',row.activity.map(item => `${item.title} · ${item.status}`).join('\n')));
    if (row.permission) {
      box.append(node('p', row.permission.title), node('pre', row.permission.details));
      for (const option of row.permission.options) {
        const button = node('button', option.kind === 'allow_once' ? '允許這一次' : '拒絕');
        button.type = 'button'; button.disabled = teamBusy || session.role !== 'administrator';
        button.addEventListener('click', () => answerTeam(team.instance_id, i, row.permission.token, option.id)); box.append(button);
      }
    }
    $('team-results').append(box);
  }
}
$('team-add').addEventListener('click', () => { if (!teamBusy && !$('team-add').disabled) addTeamWorker(); if (agentSnapshot) renderTeam(agentSnapshot.team); });
$('team-workspace-check').addEventListener('click', async () => {
  if (!session || teamBusy || $('team-workspace-check').disabled) return;
  const current = session; teamBusy = true; teamWorkspace = null; $('team-workspace-ack').checked = false;
  pauseTeamRefresh(); renderTeam(agentSnapshot?.team);
  try {
    const data = await api('/api/team/workspace');
    if (current !== session) return;
    teamWorkspace = data; $('team-workspace-source').textContent = `來源專案：${data.repository}；基底提交：${data.base_sha}`;
  } catch (error) { if (current === session) $('team-workspace-source').textContent = error.message; }
  finally { if (current === session) { teamBusy = false; if (agentSnapshot) renderTeam(agentSnapshot.team); refresh(); } }
});
$('team-remove').addEventListener('click', () => {
  if (teamBusy || $('team-remove').disabled || teamRows.length <= 2) return;
  const row = teamRows.pop(); row.key.value = ''; $('team-workers').replaceChildren(...teamRows.map(item => item.box));
  if (agentSnapshot) renderTeam(agentSnapshot.team);
});
async function answerTeam(instance_id, index, token, choice) {
  if (teamBusy || !session) return;
  teamBusy = true; teamActionError = ''; const current = session, requestGeneration = ++teamActionGeneration;
  pauseTeamRefresh();
  try {
    const result = await api('/api/team/permission', {instance_id, index, token, choice});
    if (current !== session || requestGeneration !== teamActionGeneration) return;
    if (agentSnapshot) agentSnapshot.team = result;
  } catch (error) { if (current === session && requestGeneration === teamActionGeneration) teamActionError = error.message; }
  finally { if (current === session && requestGeneration === teamActionGeneration) { teamBusy = false; if (agentSnapshot) renderTeam(agentSnapshot.team); refresh(); } }
}
$('team-start').addEventListener('click', async () => {
  if (teamBusy || !session || $('team-start').disabled) return;
  const workers = teamRows.map(row => row.kind.value && row.kind.value !== 'direct' ? {kind:row.kind.value, model:row.model.value.trim()} : ({provider:row.provider.value || 'openrouter', base_url:row.provider.value === 'custom' ? row.base.value.trim() : '', model:row.model.value.trim(), api_key:row.credentials.use.checked ? '' : row.key.value, privacy:row.privacy.value || 'zdr', ...(row.credentials.use.checked ? {use_saved:true} : {})}));
  const native = workers.some(row => row.kind);
  if (!workers.every(row => row.kind || (row.model && (row.api_key || row.use_saved) && (row.provider !== 'custom' || row.base_url)))) { teamActionError = '請填寫每個直接模型的供應商、模型 ID 和 API Key。'; renderTeam(agentSnapshot?.team); return; }
  if (native && [...$('team-task').value.trim()].length > 3000) { teamActionError = '含原生 Agent 時，總任務最多 3000 字。'; renderTeam(agentSnapshot?.team); return; }
  if (native && (!teamWorkspace || !$('team-workspace-ack').checked)) { teamActionError = '請先確認來源專案、版本與工具權限說明。'; renderTeam(agentSnapshot?.team); return; }
  teamBusy = true; teamActionError = ''; const current = session, requestGeneration = ++teamActionGeneration, submittedRows = [...teamRows];
  pauseTeamRefresh();
  renderTeam(agentSnapshot?.team);
  try {
    const payload = {task:$('team-task').value, workers}; if (native) { payload.workspace_ack = true; payload.workspace_base = teamWorkspace.base_sha; }
    const result = await api('/api/team/start', payload);
    if (current !== session || requestGeneration !== teamActionGeneration) return;
    for (const row of submittedRows) row.key.value = '';
    if (agentSnapshot) agentSnapshot.team = result;
    renderTeam(result);
  } catch (error) { if (current === session && requestGeneration === teamActionGeneration) {
    teamActionError = error.message;
    if (error.message === staleWorkspaceMessage) { teamWorkspace = null; $('team-workspace-ack').checked = false; $('team-workspace-source').textContent = staleWorkspaceMessage; }
  } }
  finally { if (current === session && requestGeneration === teamActionGeneration) { teamBusy = false; if (agentSnapshot) renderTeam(agentSnapshot.team); refresh(); } }
});
$('team-stop').addEventListener('click', async () => {
  if (teamBusy || !session || $('team-stop').disabled) return;
  teamBusy = true; teamActionError = ''; const current = session, requestGeneration = ++teamActionGeneration;
  pauseTeamRefresh();
  renderTeam(agentSnapshot?.team);
  try { const result = await api('/api/team/stop', {instance_id:agentSnapshot?.team?.instance_id}); if (current !== session || requestGeneration !== teamActionGeneration) return; if (agentSnapshot) agentSnapshot.team = result; renderTeam(result); }
  catch (error) { if (current === session && requestGeneration === teamActionGeneration) teamActionError = error.message; }
  finally { if (current === session && requestGeneration === teamActionGeneration) { teamBusy = false; if (agentSnapshot) renderTeam(agentSnapshot.team); refresh(); } }
});
$('login-form').addEventListener('submit', async event => { event.preventDefault(); const attempt = ++authGeneration, button = event.submitter; button.disabled = true; try { const data = await api('/api/login',{username:$('username').value,token:$('token').value,close_other_sessions:$('close-other-sessions').checked}); if (attempt === authGeneration) signedIn(data); } catch(error) { if (attempt === authGeneration) $('login-error').textContent = error.message; } finally { button.disabled = false; } });
$('logout').addEventListener('click', async () => { try { await api('/api/logout',{}); signedOut(); } catch(error) { showError(error.message); } });
$('agent-kind').addEventListener('change', () => { agentSignature = ''; agentActionError = ''; if (agentSnapshot) renderAgents(agentSnapshot); });
$('agent-start').addEventListener('click', async () => {
  if ($('agent-kind').value !== 'direct' || (!$('direct-key').value && !directCredentials.use.checked && !$('direct-model').value.trim())) { await agentAction('start'); return; }
  const api_key = directCredentials.use.checked ? '' : $('direct-key').value, model = $('direct-model').value.trim(), privacy = $('direct-privacy').value || 'zdr';
  const provider = $('direct-provider').value || 'openrouter';
  const extra = {api_key, model, privacy, provider};
  if (provider === 'custom' || directCredentials.use.checked) extra.base_url = provider === 'custom' ? $('direct-base-url').value.trim() : '';
  if (directCredentials.use.checked) extra.use_saved = true;
  $('direct-key').value = '';
  await agentAction('start', extra);
});
$('direct-provider').addEventListener('change', () => {
  const provider = $('direct-provider').value;
  $('direct-key').value = ''; $('direct-model').value = ''; $('direct-base-url').value = '';
  $('direct-base-field').hidden = provider !== 'custom';
  $('direct-privacy').value = provider === 'openrouter' ? 'zdr' : 'standard';
  resetDirectModels();
  const examples = {deepseek:['deepseek-flash', 'deepseek-v4-pro'], agnes:['agnes-2.5-flash']};
  for (const model of examples[provider] || []) { const opt = node('option', model); opt.value = model; $('direct-model-options').append(opt); }
  if (examples[provider]) { $('direct-model-options').disabled = false; $('direct-model-options').children[0].textContent = '請選擇範例或輸入模型 ID'; }
  if (provider === 'custom') $('direct-model-options').children[0].textContent = '自訂供應商請手動輸入模型 ID';
  $('direct-model-status').textContent = provider === 'openrouter' ? '請取得 OpenRouter 模型清單。' : provider === 'custom' ? '請手動輸入供應商提供的模型 ID。' : '請選擇範例或輸入供應商提供的模型 ID。';
  showPrivacyNote(); if (agentSnapshot) renderAgents(agentSnapshot);
});
$('direct-base-url').addEventListener('input', () => { if (agentSnapshot) renderAgents(agentSnapshot); });
$('direct-key').addEventListener('input', () => { if (agentSnapshot) renderAgents(agentSnapshot); });
$('direct-model').addEventListener('input', () => {
  if ($('direct-model-options').value !== $('direct-model').value) $('direct-model-options').value = '';
  if (agentSnapshot) renderAgents(agentSnapshot);
});
function resetDirectModels() {
  directCatalogGeneration++;
  const select = $('direct-model-options'), placeholder = node('option', '請先取得模型清單');
  placeholder.value = ''; select.replaceChildren(placeholder); select.value = ''; select.disabled = true;
  $('direct-model-load').disabled = false;
}
$('direct-model-options').addEventListener('change', () => {
  if ($('direct-model-options').value) $('direct-model').value = $('direct-model-options').value;
  if (agentSnapshot) renderAgents(agentSnapshot);
});
$('direct-privacy').addEventListener('change', () => {
  resetDirectModels();
  $('direct-model-status').textContent = '隱私模式已變更，請重新取得模型清單或手動輸入 ID。';
  showPrivacyNote();
});
$('direct-model-load').addEventListener('click', async () => {
  if (($('direct-provider').value || 'openrouter') !== 'openrouter') return;
  const button = $('direct-model-load'), current = ++directCatalogGeneration; button.disabled = true;
  $('direct-model-status').textContent = '正在取得模型清單…';
  try {
    const privacy = $('direct-privacy').value || 'zdr';
    const data = await api('/api/direct/models?privacy=' + encodeURIComponent(privacy));
    if (current !== directCatalogGeneration || ($('direct-provider').value || 'openrouter') !== 'openrouter' || ($('direct-privacy').value || 'zdr') !== privacy) return;
    const select = $('direct-model-options'), placeholder = node('option', '請選擇模型');
    placeholder.value = ''; select.replaceChildren(placeholder);
    for (const item of data.models) { const opt = node('option', `${item.id}（${item.free ? '免費模型' : '可能收費'}）`); opt.value = item.id; select.append(opt); }
    select.value = ''; select.disabled = !data.models.length;
    $('direct-model-status').textContent = `已取得 ${data.models.length} 個模型，請選擇或輸入 ID；實際可用性與價格以供應商為準。`;
  } catch (error) { if (current === directCatalogGeneration) $('direct-model-status').textContent = '無法取得清單，仍可手動輸入模型 ID。'; }
  finally { if (current === directCatalogGeneration || !session) button.disabled = false; }
});
$('agent-report').addEventListener('click', async () => {
  const name = $('agent-kind').value, state = agentSnapshot?.sessions?.[name], thread = $('codex-thread').value.trim();
  if (!state?.response || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(thread)) {
    $('report-status').textContent = '請輸入完整的 Codex 對話 ID，並確認已有回覆。'; return;
  }
  if (!window.confirm(`確認將目前 ${name} 的回覆送到 Codex 對話 ${thread}？回覆可能包含敏感內容。`)) return;
  agentBusy = true; if (agentSnapshot) renderAgents(agentSnapshot);
  try {
    const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(state.response));
    const response_sha256 = [...new Uint8Array(bytes)].map(x => x.toString(16).padStart(2,'0')).join('');
    await api('/api/agent/report', {agent:name, thread, response_sha256});
    $('report-status').textContent = '回覆已加入指定對話的佇列；請確認 Codex 已處理。';
  } catch (error) { $('report-status').textContent = `${error.message} 若連線中斷，請先檢查 Codex 佇列，避免重送。`; }
  finally { agentBusy = false; if (agentSnapshot) renderAgents(agentSnapshot); }
});
$('agent-stop').addEventListener('click', () => {
  if ($('agent-kind').value !== 'direct') { agentAction('stop'); return; }
  const state = agentSnapshot?.sessions?.direct;
  if (!state?.instance_id || !state.provider || typeof state.base_url !== 'string') {
    agentActionError = '請更新畫面並確認目前工作階段與供應商。';
    if (agentSnapshot) renderAgents(agentSnapshot);
    return;
  }
  agentAction('stop', {instance_id:state.instance_id, provider:state.provider, base_url:state.base_url});
});
$('agent-apply').addEventListener('click', () => {
  if ($('agent-kind').value !== 'direct') { agentAction('model', {model:$('agent-model').value}); return; }
  const state = agentSnapshot?.sessions?.direct;
  if (!state?.instance_id || !state.model || !['zdr','standard'].includes(state.privacy) || !state.provider || typeof state.base_url !== 'string') {
    agentActionError = '請更新畫面並確認目前工作階段、供應商與模型。';
    if (agentSnapshot) renderAgents(agentSnapshot);
    return;
  }
  agentAction('model', {model:$('direct-model').value.trim(), instance_id:state.instance_id, privacy:state.privacy,
                        provider:state.provider, base_url:state.base_url, current_model:state.model});
});
$('agent-prompt-form').addEventListener('submit', async event => {
  event.preventDefault();
  const extra = {text:$('agent-prompt').value};
  if ($('agent-kind').value === 'direct') {
    const state = agentSnapshot?.sessions?.direct;
    if (!state?.instance_id || !state.model || !['zdr','standard'].includes(state.privacy) || !state.provider || typeof state.base_url !== 'string') {
      agentActionError = '請更新畫面並確認目前工作階段、模型與隱私模式。';
      if (agentSnapshot) renderAgents(agentSnapshot);
      return;
    }
    extra.instance_id = state.instance_id; extra.privacy = state.privacy; extra.model = state.model;
    extra.provider = state.provider; extra.base_url = state.base_url;
  }
  if (await agentAction('prompt', extra)) $('agent-prompt').value = '';
});
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
