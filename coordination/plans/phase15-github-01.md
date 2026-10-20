# Phase15：透過 GitHub 分工的雙機協作

2026-10-20 使用者選擇兩台電腦各自執行任務，透過 GitHub 任務包、分支與 PR
交接，取代 A 遠端控制 B 的試跑。8443、mTLS、SSH、遠端啟動與遠端程序停止
證明不是本流程的前置條件。既有遠端執行設計留作歷史，沒有宣稱已實作。

## 共同基準與權限

- Repository: https://github.com/cch0919542639-gif/agent-coordination-system
- 發布候選分支：`codex/phase15-github-handoff-01`，以遠端 main
  `bfc5163af6dca4b9b7dec6b599563e3cbf984cac` 為基礎。
- 原本整合基準 `265a926` 比遠端 main 多出 1,204 個變動檔案，不整批發布。
  精簡候選僅選入本波需要的 inbox 模組、既有測試、合約與協作文件。
- `coordination/evidence/phase15-github-01/source-pins.json` 固定五個輸入的 SHA256；
  正式 dispatch 另記實際發布 commit 的完整 SHA，不把可移動的分支名當作基準。
- 每台使用既有本機 GitHub 身分與 HTTPS，不交換 token、私鑰、憑證或 SQLite。
  不啟用 Actions、webhook、新排程、新輪詢服務或模型工作。
- lead 是唯一指派及整合者。worker 卡目前 BLOCKED，等待發布及明確 assignment。
  發布授權後，lead 將兩張卡改成 READY，驗證並提交，再固定最終 release SHA。
  不可領取 BLOCKED 卡；發布依賴不等於 TLS 依賴。

## 第一波：兩個可以平行的任務

| 機器／owner | 任務／分支 | 唯一測試檔案 |
| --- | --- | --- |
| angeline／phase15-angeline-worker | phase15-github-validation-01／codex/phase15-github-validation-01 | tests/scripts/test_phase15_github_validation.py |
| 技嘉202509／phase15-gigabyte-worker | phase15-github-durability-01／codex/phase15-github-durability-01 | tests/scripts/test_phase15_github_durability.py |

StateController 額外原樣帶入，僅供兩個既有測試 initialize／monkeypatch apply。
未打包其 lazy parallel/resource 功能依賴，不支援其他 Controller API／CLI 使用，
更不啟用排程或 runtime 整合；這是測試 fixture 子集，並非完整 runtime 發行。

兩者對同一個固定的既有 inbox API 補獨立測試，不修改 production module，
不依賴對方的未完成介面；各自寫自己的 progress、delivery、evidence 與卡片。
全域 PLAN/TASKS/PROGRESS 在整合後由 lead 更新，避免 worker 爭寫。
B 的實際 hostname、OS/version、Python/pytest 版本由 B 自己的證據回報；
目前只有使用者指定的機器標籤，尚無第二台完成證據。

A 至少六個具區別的拒絕案例：malformed/duplicate-key JSON、boolean 當 integer、
錯誤目的地、錯誤基準雜湊、簽章失敗及驗證器例外。檢查具體錯誤類別與拒絕時
沒有 DB/receipt 副作用。先讀既有 88 測試，新增不同邊界，不能只複製改名。

B 至少五個持久化／故障案例：close/reopen 後相同訊息回傳同一 ACK 且筆數不增、
同 request 改內容被拒、重開後 sequence floor 保留、持有 SQLite write lock 時
有限拒絕且解鎖後恢復、commit 前失敗後無部分紀錄。先查既有覆蓋，加入不同
邊界或持久化觀察。只使用暫存 DB；synthetic HMAC 不代表正式驗證方案。

## 預算與驗證證據

每台一任務、一分支、一 PR、最多一個 top-level pytest invocation；兩台可以同時執行。
使用既有 Python/pytest/PyYAML；缺依賴就回報，不自動安裝。baseline 固定測試可啟動最多六個同時／十二個總計的 synthetic 子程序；每台三次
invocation 最多三十六個子程序，新測試不得再啟動程序。每個 pytest invocation
上限 180 秒，每台最多三次（初次加兩次有記錄的修復重跑），每台 active work
window 30 分鐘；等待發布／審查時間另外記錄。零新增模型/API 工作、零付費
服務、零遠端工作程序；不把既有對話或訂閱成本宣稱為零。

既有 baseline：`python -m pytest tests/scripts/test_offline_inbox.py -q`。
可同一次 invocation 加上自己的新 test file；每次都保存真實成功／失敗歷史。
每台證據上限 1 MiB、單檔 256 KiB，不提交 DB、全 terminal log、環境變數或私密對話。
交付包含必要 JUnit、精簡 findings、execution.json。execution.json 記錄 task_id、
assigned_machine_label、observed_hostname/OS、Python/pytest 版本、完整 release/base
與 tested candidate SHA、test file digest、source pins、命令、UTC 起訖、exit code、
passed/failed/skipped、attempt。報告 commit 可晚於 tested candidate，但之後任何
程式變更都要重測。主機自述是合作開發證據，不是抗惡意主機的身分證明。

## 停止、回復與整合

wrong release/hash、未知或重複 assignment、範圍衝突、缺依賴、失敗、超時或額度
用盡時停止，保留原失敗和分支。只在同任務、明確修復範圍和剩餘額度內重跑，
不重建任務繞過額度。B 的執行中程序由 B 的本地操作者停止；GitHub 撤單、
斷線或 PR 關閉都不是程序停止證明。lead 停止新指派和整合即可阻止後續發布。

GitHub 不可用時保留 local commit，不無限重試、不換帳號或繞過驗證。恢復後先
核對原 task/owner/release 仍有效。重複通知不得重跑已交付任務；同 task/candidate
只審查一次，更新 candidate 要重新審查。沒有自動重複任務或遠端程序監控保證。

回復方式是保留兩機分支／證據、撤回未合併 PR；已合併則另備 revert PR 經授權
處理，不 force-push、不 reset 共享歷史、不刪證據。worker 不自行接受或合併。
lead 路由獨立 review，核對 release/source pins、scope、candidate、JUnit、主機證據；
審查者不能接受自己實作的測試。通過後在獨立 integration branch 依序整合兩份
reviewed candidate，跑原 88 及兩份新測試與 coordination validator。衝突處理、
rebase 或任何測試／來源 bytes 改動後都要重跑受影響驗證。

只有兩台各自的實際交付及整合驗證均通過，才稱本波雙機協作完成。

## 本次交付與發布界線

目前是本機可審查的精簡發布候選和兩個任務包；尚未 push、建立 PR、通知 B、
執行第二機任務或完成雙機驗收。依 Agent Working Agreement 的未授權 push
規則，最後固定 exact branch/SHA、allowlist、審查結果，再由操作者確認發布。
GitHub 存取是交接通道，不是直接連線 B。
