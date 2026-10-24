# Console 下載驗證：原始初始化受 Windows 編碼問題阻擋

驗證日期：2026-10-24（Asia/Taipei）；證據發布日期：2026-10-25。

受測版本：`c7f7dee2c356009f51fbe63434ecf0c5400e7571`，依據該提交的
[下載指南](../../docs/operations/console-download-guide.md)，從 GitHub 全新 clone
並 detached checkout，使用 Windows 11、Python 3.13.15、全新 private state 與
獨立 workspace 路徑。沒有複用其他電腦的帳號、資料庫、token 或 ACK。

**驗收結論：未通過原始指南的直接初始化；相關回歸 114 passed、1 failed。**
明確啟用 UTF-8 後的功能結果不取代原始失敗，也不代表正式發布或 P1 完成。
這份證據來自目前執行主機；未核對來源主機硬體身分，因此無法證明兩台硬體
不同，亦未操作其他未連線電腦。

## 驗證結果

| 項目 | 結果 |
| --- | --- |
| 指定提交與來源清單 | HEAD 相符；29 source/test/doc/static + 12 accepted board snapshot，共 41 個 Git blob SHA256 相符；checkout 換行正規化後相符 |
| 原始初始化 | FAIL，exit 1，CP950 解碼失敗；最終 state 未建立，失敗 staging 保留 |
| `PYTHONUTF8=1` 初始化 | PASS，Viewer、schema4、parallel disabled、runs=0 |
| 重複初始化 | PASS，created=false；4 個 private 檔案位元組不變 |
| username 設定衝突 | PASS，exit 2 拒絕且 private 檔案不變 |
| 登入及七個 API 視圖 | PASS，兩次獨立 serve/login，全部 200，runtime_available=true |
| 看板 | 105 張任務卡 |
| 靜態頁面 | `/`、`/app.css`、`/app.js` 均 200 |
| 未登入 API / Viewer 寫入 | 分別 401 / 403；preview 與 execute 均拒絕 Viewer |
| Cookie | HttpOnly、SameSite=Strict |
| 有限啟動與重啟 | 兩次各 10 秒，到期 exit 0，沿用同一組本機憑證 |
| 執行後私有資料 | 位元組不變，disabled、runs=0 |
| 相關測試 | 115 cases：114 passed、1 failed、0 skipped、0 errors；native exit 1，24.50 秒 |
| 產品原碼 | 未修改；發布前受測 checkout 的 Git status 為空 |

## Exact Blocker

`scripts/console_setup.py` 的 `current_sid()` 用 `subprocess.run(..., text=True)`
讀取 `whoami /user /fo csv /nh`。本機預設文字編碼為 CP950，但原始輸出可用
UTF-8 解碼、不能用 CP950 解碼。讀取執行緒先拋出 `UnicodeDecodeError`，
`result.stdout` 變成 None，再於 `.strip()` 發生 `AttributeError`，初始化 exit 1。

後續只對子程序環境設定 `PYTHONUTF8=1`，沒有修改全域設定或產品原碼。
失敗測試是
`tests/scripts/test_console_setup.py::test_cli_new_directory_login_seven_views_viewer_refusal_and_finite_exit`。
它以 `python -I -B` 啟動子程序，`-I` 忽略環境中的 `PYTHONUTF8`，因此重現同一問題。

可在新的、互不包含的 canonical 路徑上重現：

```powershell
py -3.13 scripts/console_setup.py init --repo "<CHECKOUT>" --workspaces "<WORKSPACES>" --project-id console-verification --state-dir "<NEW_PRIVATE_STATE>"
```

上述尖括號必須替換為本機實際路徑；不可複用別人的 private state。

相關回歸（本次父程序環境為 `PYTHONUTF8=1`）：

```text
python -B -m pytest -q -p no:cacheprovider tests/scripts/test_console_setup.py tests/scripts/test_web_console.py tests/scripts/test_state_controller.py tests/scripts/test_board_projection.py --junitxml=<EXTERNAL_EVIDENCE>/junit.xml
```

建議維護者修正 SID 取得方式或明確處理 Windows 輸出編碼，補測非 ASCII
帳號及 `-I` 子程序，再提供新的固定提交。不能假定所有 Windows 都輸出 UTF-8。

## Scope / Risk Impact

本 PR 僅發布報告與去識別證據；不修補程式、不建立帳號、不更動正式任務狀態、
不啟用 worker、排程、常駐服務或 remote execution。實測服務已到期停止。
原始指令仍失敗，不應將替代條件的成功標為正式驗收通過。

未做瀏覽器視覺/互動、Ctrl+C 手動停止、整倉測試、其他 Python 版本或其他硬體驗證。
本 PR 的核對限於發布內容、JSON/XML 可讀性、雜湊、憑證掃描及 diff；未重跑
產品測試，因為發布內容沒有改動受測產品。

## 證據與隱私

證據目錄：[console-download-verification-20261024](../evidence/console-download-verification-20261024/)。

- `results.json`、`init.log`：原始指令失敗與 traceback。
- `encoding-diagnosis.json`：編碼檢查，沒有 whoami 帳號內容。
- `utf8-workaround/results.json`：替代執行條件及逐項功能結果。
- `utf8-workaround/focused-tests.log`、`utf8-workaround/junit.xml`：完整測試結果及失敗。
- `utf8-workaround/init*.log`、`utf8-workaround/serve-*.log`：初始化、拒絕與有限啟動。
- `attempt1-results.json`：最早驗證器只對 checkout 正規化換行，誤判原本含 CRLF
  的 Git blob；之後修正為兩側正規化比較，原始 blob SHA256 另外獨立核對。
  這是驗證器問題，未改動受測產品，也沒有隱藏該次失敗。
- `publication-manifest.json`：本次去識別檔案 SHA256 與處理規則。

發布副本移除 Windows 使用者名稱、主機名及本機 checkout/private/workspace
絕對根路徑；XML 重新序列化。測試數量、原始錯誤、exit code 與時間保留。
原始證據、含本機路徑的驗證腳本、private state、失敗 staging 只留在本機。
未發布 login token、auth 設定、runtime DB、cookies 或任何憑證內容。
