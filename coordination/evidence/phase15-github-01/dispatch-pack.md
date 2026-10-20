# Phase15：兩台電腦各自領取任務

## Current status (2026-10-21)

A/angeline is DONE:current Codex session executed the assignment,102 tests pass
and independent review accepted. Do not redispatch A. B/second-machine task is
still READY;use only its section below. Older A instructions are retained history.


2026-10-21。發布已獲使用者同意；這是領取指示，不是已開始執行的回報。
兩台電腦只需要各自連 GitHub，不需要彼此連線、8443、TLS 私鑰或遠端控制。
請在各機既有代理中提供對應任務；不由本文件自動啟動模型、排程或程序。

共同 worker base：`910cb9175870fd6f3df6e699b632f85cb0a97bf4`。
本發布分支在這個基準之後增加 assignment 文件，所以分支 HEAD 可以較新；
領取時必須使用上述完整 SHA。任務卡與測試輸入在這個 SHA 都已固定。

## angeline

請領取 `phase15-github-validation-01`，owner `phase15-angeline-worker`。
只實作訊息驗證的獨立測試與自己的交接證據。至少六個不同的有效邊界／拒絕案例，
不得只複製既有測試改名。遵守卡片範圍；不要改 production source。

在乾淨 clone 中執行以下指令，任何一步失敗即停止，不 reset 原有工作：

```powershell
git fetch origin codex/phase15-github-handoff-01
git merge-base --is-ancestor 910cb9175870fd6f3df6e699b632f85cb0a97bf4 FETCH_HEAD
git switch --create codex/phase15-github-validation-01 910cb9175870fd6f3df6e699b632f85cb0a97bf4
```

任務卡：`coordination/task-board/ready/2026-10-20_phase15-github-validation-01_validation-tests.md`。

## 技嘉202509

請領取 `phase15-github-durability-01`，owner `phase15-gigabyte-worker`。
只實作持久化去重與故障測試，以及自己的交接證據。至少五個不同的持久化／故障
觀察；使用暫存 DB，不修改 production source 或另一台的檔案。

在乾淨 clone 中執行以下指令，任何一步失敗即停止，不 reset 原有工作：

```powershell
git fetch origin codex/phase15-github-handoff-01
git merge-base --is-ancestor 910cb9175870fd6f3df6e699b632f85cb0a97bf4 FETCH_HEAD
git switch --create codex/phase15-github-durability-01 910cb9175870fd6f3df6e699b632f85cb0a97bf4
```

任務卡：`coordination/task-board/ready/2026-10-20_phase15-github-durability-01_durability-tests.md`。
回報該機實際 hostname、OS、Python/pytest 版本；目前只有指派標籤，尚無該機執行證據。

## 共用執行要求

先讀 PLAN.md、PROGRESS.md、TASKS.md、自己的任務卡與
[交接指南](../../../docs/operations/phase15-github-handoff-guide.md)，再核對
[source pins](source-pins.json) 的五個 SHA256。
將自己的卡移到 in_progress，寫自己的 progress；完成後提交 review 與 delivery。
已有分支、已領取或已交付時先核對進度，不能因重複通知重跑任務。

每台最多三次 pytest invocation，每次180秒，active work30分鐘；既有基準88測試
加上自己的新增測試，保留失敗、JUnit、execution.json 與確切 candidate SHA。
新測試不得啟動子程序；原基準有固定的 synthetic 子程序預算，依計畫執行。
零新增模型/API 工作或付費服務；缺依賴即回報，不自動安裝或啟動模型補救。

可用的新邊界例子（先查現有覆蓋）：A 對已存在 journal 驗證重複 authentication key
不得修改 DB，或檢查尚未參數化的 integer 欄位拒絕 boolean；B 測試持有 SQLite
write lock 後拒絕／解鎖恢復，或 INSERT receipt 的觸發器失敗後無部分紀錄。

完成後依該機操作者的明確授權提交自己的 branch/PR；未取得時保留本機 commit
及候選 SHA，回報 lead 取得限定範圍的發布決定。本次核准只涵蓋 handoff 發布分支。
worker 不自行接受或合併。最後由 lead 路由獨立審查及兩份測試的整合驗證。
GitHub 撤單或 PR 關閉不代表本機程序已停止；停止由各機操作者處理並保留證據。
