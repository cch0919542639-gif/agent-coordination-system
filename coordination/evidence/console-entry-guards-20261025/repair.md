# 入口防護修補 — 2026-10-25

已完成使用者指定的 local loop／worker activation 防護修補，原三個失敗案例全部通過。

## 變更

以 PR6 確切版本 `92e1248b63dee44a607296b3d63f61207b61f09a` 建立獨立工作樹：
`C:/Users/angel/.codex/worktrees/console-entry-guards/codex work`。

- `scripts/local_agent_loop.py`：匯入既有 require_serial；run_loop 在讀取計畫／預覽／鎖定／dispatch 前檢查 ROOT；launch_worker 在建構啟動命令前再檢查 ROOT，避免直接呼叫繞過入口。
- `scripts/worker_poller.py`：在共享的 task-card 解析路徑中，registered project local_path 成功解析成實際 root 後執行 require_serial。既有 activation 錯誤處理會回傳拒絕，不會先寫 inbox 或 ACK；不以中央目錄或 cwd 取代目標專案 root。
- 無新增機制、依賴或測試；沿用原本能重現缺陷的測試。兩個來源檔共 6 added / 2 removed（其中兩處為匯入更新）。

## 驗證

Windows Python3.12，單次300秒上限，四組測試 **110 passed / 0 failed / 0 skipped，native exit0**；pytest98.97秒，外層99.938秒：

`python -B -m pytest tests/scripts/test_parallel_runtime.py tests/scripts/test_worker_activation.py tests/scripts/test_worker_poller.py tests/scripts/test_local_agent_loop.py -q --basetemp <system-temp> --junitxml <evidence>/regression.xml`

原本失敗的 test_mode_preview_guards_and_quiescent_disable、activation[enabled]、activation[corrupt] 均通過。正常 activation[absent] 也通過，包含 inbox 建立、ACK 以及任務卡保留；enabled/corrupt 拒絕案例確認 delivery 位元組不變且沒有 inbox。

協調資料 validator 返回0；git diff --check 返回0。既有47個發布釘選檔案全數維持原 SHA256。修改的兩個 legacy script 原本不在該47個釘選清單中，其最終 SHA256 另記於 regression-result.json；不將此工作樹冒稱已更新的正式發布版本。

本輪未重跑前輪核心131項，也不把兩次執行相加宣稱整套成功。先前154pass/3fail原始紀錄保留於 pr6-readiness-review-20261025；本次僅針對入口修補及相鄰回歸。這是既有 marker gate 的入口補齊，不宣稱新增跨程序啟用/派工原子鎖定或全面消除競爭條件。

## 產物與發布狀態

本目錄保留 regression.log、regression.xml、regression-result.json、test-summary.json、checks.json、coordination-validation.log、diff-check.log 及可套用的 entry-guards.patch。

修補仍是獨立工作樹的本機未提交變更；未commit/push/merge，PR6/PR9、原發布候選與main未變，未啟動真實worker/provider/watch或排程。後續若發布修正版，需重新綁定精確來源與釘選／發布證據，並處理PR9的相容性整合；本次不重寫歷史accepted DONE卡或自行接受GitHub review。

## 提交推送授權

使用者於修補驗證後授權完整時提交及推送。本層新增REVIEW任務卡及交付紀錄，準備發布codex/console-entry-guards-01並建立以codex/console-bootstrap-01為base的草稿PR。上方未提交文字為測試交付時快照；實際發布結果以Git／PR為準。未宣稱獨立接受或合併授權。

發布檢查：publication-checks.json記錄受測CRLF與Git儲存LF之正規化對應；來源邏輯未再修改。entry-guards.patch為零context diff，套用時使用git apply --unidiff-zero。原測試log及validator log明確納入版本，避免既有*.log忽略規則漏收。
