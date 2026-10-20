# Phase15 GitHub 任務領取與交接

以 [本波計畫](../../coordination/plans/phase15-github-01.md) 與各自卡片為準。
本流程不執行 Downloads 的 TLS 檢查檔或 start_agent_tracker.ps1，無須開 8443、
安裝根憑證、啟用 SSH 或交換 client.key。

## 發布者

先審查精簡候選和 source-pins.json，取得 publication approval。lead 將兩張
BLOCKED 卡移到 ready 並改為 READY，保留 owner/branch/scope，重跑 validator
並提交，固定最終完整 release SHA，再推送 `codex/phase15-github-handoff-01`。
不得 force；目的地只能是既有 origin。分別提供 task_id、owner、release SHA、
worker branch 的明確 assignment。已在本機準備不等於另一台已領取。

## 各機操作

使用既有 GitHub 權限，另建乾淨 clone，保留原工作區。以下 `<RELEASE_SHA>`
須替換為 lead 已發布並審查的完整 40 字元 SHA，`<WORKER_BRANCH>` 須替換成
本卡指定分支；不要照抄角括號文字執行。

```powershell
git fetch origin codex/phase15-github-handoff-01
git switch --create <WORKER_BRANCH> <RELEASE_SHA>
git status --short
python -c "import pytest, yaml; print(pytest.__version__)"
```

核對 fetch 的發布分支包含 release SHA、工作樹乾淨、卡片 READY、owner 與
本機 assignment 相符，再核對 source-pins.json 的五檔 SHA256。分支已存在時
先核對進度，不 reset 或再次執行已提交任務。這是人工協作，不假設自動去重。

只移動自己的卡片（ready -> in_progress -> review）、寫自己的 progress、delivery
和 evidence。各分支的卡片是 worker 提出的狀態，lead 整合時決定 canonical board。
不改另一張卡、中央 PLAN/TASKS/PROGRESS 或共享 runtime DB。

A 新增 `tests/scripts/test_phase15_github_validation.py`；B 新增
`tests/scripts/test_phase15_github_durability.py`。用暫存目錄與既有工具完成本卡
驗證，保留命令、時間、SHA、JUnit 與失敗歷史。不得啟動服務或 production worker。
缺少 branch push 的明確授權時，準備本機 commit 和可貼上的交接文字即可。

PR 標題使用 `[task_id] 實際完成結果`，body 寫 release、candidate、範圍、驗證、
風險。不提交 DB、金鑰、token 或私密對話。worker 不自行接受、合併或改派。

## 停止與整合

錯誤先保留證據，按計畫有限修復；不能安全修復即寫 incident 後停止。
lead 撤單只停止後續交付／整合，執行中程序由本地操作者停止並回報。
兩份 PR 經獨立 review 與整合測試後，lead 才更新中央完成狀態。
