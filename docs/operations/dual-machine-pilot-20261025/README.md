# 雙機同步／收件驗收包（尚未啟動）

這一輪只測傳輸：ANGELINE派發、技嘉202509收件、ANGELINE看到回執，再重播一次。
兩台必須是真實不同電腦，由使用者確認；machine_id只是指定路由的代號。
程式版本固定 `1d7b85b60b56299a161aba90a53d0078120d84af`，queue為 `refs/heads/codex/handoff-dual-intake-20261025-01`。
任務 `dual-intake-20261025-01`，card SHA256 `04eafa22a3a8794e7a43d1c36286d4508491d886b2e01102e0fd67f1ead5171a`。
詳細准許／禁止範圍見approval-scope.json。沒有runner，沒有watch，沒有正式任務狀態變更。

## 啟動前關卡

此包只作準備。未取得本輪明確啟動同意前，不執行init/sync/dispatch/receive。
不要把兩個角色在同一電腦跑通當成雙機成功。這個queue在準備時以ls-remote查無分支；
正式啟動前還須重查，若已存在則停止，不刪除或覆蓋。
使用既有Git登入，不另建／修改憑證。兩台各用新的專用clone、設定與state，不能拷貝
另一台的auth、DB、ACK或claim。不要動原本的D槽工作目錄或既有Viewer帳號。

設定的runner及execution_enabled會綁定state，這輪不得之後改成可執行。
未來要驗證runner，另建新task／queue／兩台新store，不能沿用這輪claim。
Evidence discovery刻意關閉，避免把舊92e1248報告當成本版驗收。

## 各自準備專用clone與設定

先將本目錄的文件下載／複製到repository以外的資料夾，記為$packet。
使用USERPROFILE下的新目錄並解析實體路徑；不要依賴可能被MSIX虛擬化的AppData別名。
兩台各執行以下準備段；這段不初始化handoff，也不寫GitHubqueue。
ANGELINE用$role='coordinator'，技嘉202509用$role='worker'。
Python範例用py -3.12，已裝3.13可全程一致改成py -3.13。

```powershell
$ErrorActionPreference = 'Stop'
$role = 'worker' # ANGELINE改為coordinator
$packet = '替換為此驗收包的本機資料夾'
$pilotRoot = Join-Path $env:USERPROFILE 'CodexHandoffPilot\dual-intake-20261025-01'
if (Test-Path -LiteralPath $pilotRoot) { throw '目標已存在；保留內容並停止，勿覆蓋或重設' }
New-Item -ItemType Directory -Path $pilotRoot | Out-Null
$pilotRoot = (py -3.12 -c "import json,pathlib,sys; print(json.dumps(str(pathlib.Path(sys.argv[1]).resolve())))" $pilotRoot | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0) { throw '實體路徑解析失敗，停止' }
$repo = Join-Path $pilotRoot 'repo'
git clone --depth 1 --single-branch --branch codex/console-handoff-sync-01 https://github.com/cch0919542639-gif/agent-coordination-system.git $repo
if ($LASTEXITCODE -ne 0) { throw 'clone失敗，停止' }
$head = (git -C $repo rev-parse HEAD).Trim()
if ($head -ne '1d7b85b60b56299a161aba90a53d0078120d84af') { throw '分支版本已變；停止並重新核定版本' }
git -C $repo checkout --detach $head
if ($LASTEXITCODE -ne 0) { throw 'checkout失敗，停止' }
$config = Get-Content -LiteralPath (Join-Path $packet ($role + '.template.json')) -Raw | ConvertFrom-Json
$config.repository = (Resolve-Path -LiteralPath $repo).Path
$config.state_dir = Join-Path $pilotRoot ($role + '-state')
$configPath = Join-Path $pilotRoot ($role + '.json')
$bytes = [Text.UTF8Encoding]::new($false).GetBytes(($config | ConvertTo-Json -Depth 8))
$stream = [IO.File]::Open($configPath, [IO.FileMode]::CreateNew)
try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
Set-Location -LiteralPath $repo
py -3.12 scripts/github_handoff.py --config $configPath summary
if ($LASTEXITCODE -ne 0) { throw '設定驗證失敗，停止' }
```

summary只讀未初始化狀態；應顯示initialized=false，這不是網路健康檢查。
兩台準備好後回報角色與固定HEAD即可，不分享本機路徑、設定DB或憑證。
下列步驟只在本輪範圍獲同意且兩台就緒後依序執行。每個命令後檢查$LASTEXITCODE，
非0就停止並保留原輸出／state，不接著執行下一步。

## A：ANGELINE初始化、預覽、派發一次

先確認queue不存在，並把payload卡以Copy-Item原樣複製到專用clone的ready/，
不要用編輯器重存或改行尾；此卡保持READY，不做claim_task。

```powershell
$existingQueue = @(git ls-remote --heads origin refs/heads/codex/handoff-dual-intake-20261025-01)
if ($LASTEXITCODE -ne 0 -or $existingQueue.Count -ne 0) { throw 'queue已有內容或查詢失敗；停止' }
if (Test-Path -LiteralPath 'coordination/task-board/ready/2026-10-25_dual-intake-20261025-01_transport-only.md') { throw '卡片已存在，停止' }
Copy-Item -LiteralPath (Join-Path $packet 'pilot-task.md') -Destination 'coordination/task-board/ready/2026-10-25_dual-intake-20261025-01_transport-only.md' -ErrorAction Stop
(Get-FileHash -LiteralPath 'coordination/task-board/ready/2026-10-25_dual-intake-20261025-01_transport-only.md' -Algorithm SHA256).Hash.ToLower()
# 必須等於上列card SHA。
py -3.12 scripts/github_handoff.py --config $configPath init
if ($LASTEXITCODE -ne 0) { throw 'handoff命令失敗；停止並保留state與原輸出' }
py -3.12 scripts/github_handoff.py --config $configPath sync
if ($LASTEXITCODE -ne 0) { throw 'handoff命令失敗；停止並保留state與原輸出' }
# 確認code_revision精確等於固定版本，queue_head為40個0，ready_tasks有本任務及正確owner。
py -3.12 scripts/github_handoff.py --config $configPath dispatch --task-id dual-intake-20261025-01 --machine-id gigabyte-202509 --expected-card-sha256 04eafa22a3a8794e7a43d1c36286d4508491d886b2e01102e0fd67f1ead5171a --expected-revision 1d7b85b60b56299a161aba90a53d0078120d84af --expected-queue-head 0000000000000000000000000000000000000000
if ($LASTEXITCODE -ne 0) { throw 'handoff命令失敗；停止並保留state與原輸出' }
# 核對PREVIEW及allowed_scope/forbidden_scope後，才執行下一行一次。
py -3.12 scripts/github_handoff.py --config $configPath dispatch --task-id dual-intake-20261025-01 --machine-id gigabyte-202509 --expected-card-sha256 04eafa22a3a8794e7a43d1c36286d4508491d886b2e01102e0fd67f1ead5171a --expected-revision 1d7b85b60b56299a161aba90a53d0078120d84af --expected-queue-head 0000000000000000000000000000000000000000 --execute
if ($LASTEXITCODE -ne 0) { throw 'handoff命令失敗；停止並保留state與原輸出' }
```

dispatch --execute只發送卡片，不授權runner。記錄dispatch_id及原卡SHA；告知另一台可收件。
專用sender clone會有這一張預期的untracked READY卡，不得將它當成需要clean的垃圾。

## B：技嘉202509收件一次，再重播一次

```powershell
py -3.12 scripts/github_handoff.py --config $configPath init
if ($LASTEXITCODE -ne 0) { throw 'handoff命令失敗；停止並保留state與原輸出' }
py -3.12 scripts/github_handoff.py --config $configPath receive
if ($LASTEXITCODE -ne 0) { throw 'handoff命令失敗；停止並保留state與原輸出' }
# 觀察本dispatch為RECEIVED；在這個專用handoff.db記錄inbox列數、dispatch_id與run_id。
py -3.12 scripts/github_handoff.py --config $configPath receive
if ($LASTEXITCODE -ne 0) { throw 'handoff命令失敗；停止並保留state與原輸出' }
# 比較仍只有一列、相同dispatch_id/run_id，狀態仍RECEIVED。
```

兩次都不能加--execute。可以唯讀查本輪專用handoff.db，不讀取其他私密DB。
不要上傳整份DB。確認state/workspaces未建立，沒有runner執行payload；repository保持乾淨。
只回報本輪固定HEAD、兩次native exit、RECEIVED、單列／同身分、workspace未建立。
保留config/state/claim原樣，之後不要改runner或execution_enabled。

## A：ANGELINE同步回執並驗收

```powershell
py -3.12 scripts/github_handoff.py --config $configPath sync
if ($LASTEXITCODE -ne 0) { throw 'handoff命令失敗；停止並保留state與原輸出' }
# 同一dispatch_id、正確peer／owner，狀態RECEIVED。
(Get-FileHash -LiteralPath 'coordination/task-board/ready/2026-10-25_dual-intake-20261025-01_transport-only.md' -Algorithm SHA256).Hash.ToLower()
```

驗收需：兩台實際不同、固定同版、一次assignment、單一claim/run/inbox、重播不重複收件、
sender看到RECEIVED、正式卡仍READY且SHA不變、無workspace／runner／provider／排程或權限變更。
收件不等於DONE或FINISHED。先由協調端核對這些回執，通過後再決定PR9的合併；本包不自動合併。
若任一失敗，保存原始失敗及安全摘要，不reset／clean／刪queue／新store搶舊claim。
