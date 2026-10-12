# 收工交接 — 2026-10-12

## 目標與狀態

Codex 主控、OpenCode／Hermes 執行的有限任務閉環已完成：交辦 → 執行 →
回報 → 獨立驗收 → 修正或續派 → 全部完成後停止。已用真實 worker 跑通，
並驗證完成後重跑不會再啟動 worker。

- [PR #3](https://github.com/cch0919542639-gif/agent-coordination-system/pull/3)
  已合併到 `main`；程式與整合驗證基準為 `8a531eded627d955783a44d556358b02df582030`。
  本次另提交收工文件；最新 HEAD 以 `git fetch origin main` 後查詢為準。
- PR #1／#2 的內容均已包含在 `main`，已關閉為被取代的 PR；分支保留。
- `phase14-local-loop-01`、`phase14-loop-publication-01`、
  `phase14-main-integration-01` 與對應獨立審查均為 accepted DONE。
- 本次前景 worker 已結束。兩個 Windows worker 排程均為 Disabled；
  Hermes 舊 cron `3cffd3c69ae7`／`d215f82b3e50` 均為 enabled=false。

## 本次完成範圍

- `scripts/local_agent_loop.py`：明確計畫、依賴順序、收據與範圍核對、
  有界修正、續跑、完成停止；已消費的 needs_fix 通知會正確確認。
- `scripts/submit_task.py`：由摘要、產物與 ACK 生成標準報告，驗證後提交。
- 兩個 controlled-worker launcher 與 Hermes SDK runner：身分核對、
  保留原任務、限制請求與輸出、真正 REVIEW 收據才算提交成功。
- `scripts/resolve-python.ps1`／`run_python.ps1` 與
  `prepare_local_loop.py`：可攜 Python 尋找、新下載目錄初始化與新任務計畫。
- 與 `main` 的六處衝突已解決，原有 status、launcher-dry-run 及安全驗證保留。

完整證據：`coordination/evidence/github-download-check-01/`、
`coordination/evidence/main-loop-integration-01/` 與對應 delivery／review 檔案。
操作入口為[下載與初始化指南](https://github.com/cch0919542639-gif/agent-coordination-system/blob/main/docs/operations/github-download-verification.md)。

## 驗證

以下完整 scripts 測試在整合工作目錄執行：

```powershell
& 'D:/codex work/.venv/Scripts/python.exe' -m pytest tests/scripts -q --basetemp 'C:/Users/angel/AppData/Local/Temp/codex-main-loop-tests-02'
```

- 412 passed、2 skipped，221.05 秒。兩項略過為歷史 phase6 測試卡已不在 ready/。
- 首輪非 Git 目錄測試因暫存放在 Git 倉庫內而失敗；改用系統暫存後全套通過，
  沒有修改程式或測試來避開失敗。不要把該負向測試的 basetemp 放在倉庫內。
- OpenCode 獨立審查無阻擋問題，exit0、範圍違規為空；另有 29 項 focused tests 通過。
- 編譯、協調資料驗證與 Git diff 檢查通過。乾淨下載最新 `main` 後，
  資料驗證、初始化與計畫預覽通過；執行程式／測試與已驗證整合版本相同。
- 真實閉環包含 OpenCode 自動修正，以及 Hermes 供應商 HTTP400 後的
  明確同收據續跑成功。既有 API 額度與工具生成錯誤仍可能令流程安全停止。

本次建立收工文件時重新執行：`scripts/orchestrate.py validate`、
`git -c core.safecrlf=false diff --check`，均通過；未重跑全套或額外呼叫模型。

## 工作目錄與 Git 狀態

| 位置 | 狀態 |
| --- | --- |
| `D:\codex work` | 原始目錄；分支 `codex/phase14-runtime-adapter-01-source`，HEAD `6fc6e3f`，保留大量既有修改／未追蹤內容。不是 `main` 的乾淨 checkout。 |
| `C:\Users\angel\.codex\worktrees\hermes-launcher-publication\codex work` | 乾淨整合目錄；分支 `codex/main-local-agent-loop-integration`，HEAD `8a531ed`，已推送。 |
| `coordination/monitor/runtime/github-main-verification-01` | 實際 GitHub `main` 驗證下載，HEAD `8a531ed`；含本機測試初始化資料，不是待發布內容。 |

原始目錄的 diff 同時包含本次已由獨立工作目錄發布的成果，以及原有未整合工作。
不要將全部 dirty 檔案當成本次待推送內容，勿整批 add、reset、clean 或直接覆蓋 pull。
AGENTS／protocol 調整、research、其他產品 checkout 等既有工作沒有混入本次 main 合併。

## 下次接續

尚未指定下一個實作任務。先從乾淨整合目錄核對，再由使用者的新目標建立新計畫：

```powershell
Set-Location 'C:\Users\angel\.codex\worktrees\hermes-launcher-publication\codex work'
git status --short --branch
git fetch origin main
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_python.ps1 scripts/orchestrate.py validate
```

新任務須有新 task／run ID 與明確驗收條件；不要重設舊 ACK 或搬用另一部電腦的
inbox、runtime state 或憑證。另一部 Windows 電腦仍需 Python3.11+、Git、
PowerShell、OpenCode、Hermes 與本機供應商設定；本次未實測第二台實體電腦。
跨機任務傳輸與持續排程仍未實作，未授權的排程不要啟用。

獨立架構分支 `codex/phase14.5-architecture-01` 本機 ref 為 `516bdd5`，
此次未處理；其工作、審查、遠端與 dirty 狀態須另行核對，不能沿用舊交接的假設。
目前 merge 權限依 main 的 `DECISIONS.md` clean-gate 政策與當次任務授權判定，
不可把上一份交接的「所有操作均需另問」套用成全域限制；worker 本身仍無合併權限。

## 收工紀錄

- 更新者：Codex；電腦：ANGELINE；時區：Asia/Taipei。
- 核心程式、整合與驗證證據已推送到 `main`，收工文件發布前基準為 `8a531ed`。
- 使用者已明確指示提交推送；僅發布 `handoff.md` 與 `PROGRESS.md` 的收工更新，
  原始目錄其餘既有修改保留。文件發布採用上述乾淨整合工作目錄。
- 提交訊息：`docs: record October 12 local agent loop handoff`。
  文件所屬 commit／推送結果以 Git 歷史與本次交付回報查詢，避免把自身 SHA 寫進自身。
