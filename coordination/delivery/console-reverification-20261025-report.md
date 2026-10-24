# Console 修復版原始環境重驗通過

日期：2026-10-25（Asia/Taipei）。

受測提交：`92e1248b63dee44a607296b3d63f61207b61f09a`。
依據[該提交的下載指南](https://github.com/cch0919542639-gif/agent-coordination-system/blob/92e1248b63dee44a607296b3d63f61207b61f09a/docs/operations/console-download-guide.md)，
從 GitHub 全新下載，detached checkout 至指定提交，選用原有 Python 3.13.15，
建立全新且互不包含的 repository、workspace、private state 路徑。
未複用舊帳號、資料庫、token 或 ACK，也未修改受測產品。

**結果：原始環境重驗 PASS；131 tests passed，native exit 0。**
前次 c7f7dee 的 CP950 初始化阻擋，本次在相同執行主機與一般環境下不再重現。
本報告是技術驗證證據，不變更正式任務狀態、不自行核准 P1 或合併發布分支。

## 環境與繞過排除

| 條件 | 實測 |
| --- | --- |
| OS / interpreter | Windows 11 / Python 3.13.15 |
| locale.getpreferredencoding(False) | cp950 |
| sys.flags.utf8_mode | 0 |
| PYTHONUTF8 / PYTHONIOENCODING | 均未設定 |
| 驗收啟動方式 | 原有 interpreter，無 `-X utf8`、無環境編碼繞過 |
| private state | 全新本機初始化；舊成功 state 與失敗 staging 均保留 |

既有回歸測試內有一個刻意設定 PYTHONUTF8 的合成案例，但其子程序使用
`-I -X utf8=0` 並斷言 UTF-8 mode 關閉，目的是驗證忽略環境變數時仍能取得
SID；這不是本次驗收程序的繞過。驗收父程序與實際 init/serve 子程序沒有設定
PYTHONUTF8，也沒有修改控制台 code page 或全域編碼設定。

## 結果

| 項目 | 結果 |
| --- | --- |
| HEAD | 完全相符於 92e1248b63dee44a607296b3d63f61207b61f09a |
| 清單來源 | 29 source/test/doc/static + 18 accepted board snapshot，共 47 個 Git blob SHA256 相符；checkout 換行正規化後相符 |
| 全新初始化 | exit 0、created=true、Viewer、disabled |
| 相同命令重播 | exit 0、created=false；4 個 private 檔案 SHA256 不變 |
| 不同 username | exit 2 拒絕；private 檔案不變 |
| 兩次登入與七個 API 視圖 | 均 200、runtime_available=true |
| 看板 | 107 張任務卡，與本版 manifest 相符 |
| 靜態頁面與資產 | `/`、`/app.css`、`/app.js` 均 200 |
| 未登入 API | 401 |
| Viewer preview / execute | 均 403 |
| Cookie | HttpOnly、SameSite=Strict |
| 停止與重啟 | 同一個 loopback 連接埠，兩次各 10 秒，到期 exit 0，沿用同一憑證 |
| 執行後資料 | schema4、parallel disabled、runs=0；private 檔案位元組不變 |
| 相關回歸 | 131 passed、0 failures、0 errors、0 skipped；native exit 0 |
| 受測 checkout | 實測後 git status 為空；發布步驟才新增報告與證據 |

回歸範圍與前次相同的四個測試檔，包含新版增加的 SID 測試，以及前次失敗的
`test_cli_new_directory_login_seven_views_viewer_refusal_and_finite_exit`。

```text
python -B -m pytest -q -p no:cacheprovider tests/scripts/test_console_setup.py tests/scripts/test_web_console.py tests/scripts/test_state_controller.py tests/scripts/test_board_projection.py --junitxml=<EXTERNAL_EVIDENCE>/junit.xml
```

## Exact Blocker

本次指定技術驗證範圍沒有阻擋。前次 CP950 解碼失敗保留於
[PR #7](https://github.com/cch0919542639-gif/agent-coordination-system/pull/7)，
受測舊提交 c7f7dee；其 114 passed / 1 failed 結果不被本報告覆寫。

## Scope / Risk Impact

沒有產品原碼變更、worker 啟動、常駐服務、排程、遠端執行或正式任務核准。
兩次服務已到期停止。原始失敗主機上的功能/API 技術重驗已通過；未進行
瀏覽器視覺/互動驗收、Ctrl+C 手動停止、整倉測試或其他 Python 版本驗證。
本次也沒有核對來源電腦硬體身分，不能據此宣告已證明兩台實體電腦不同。
是否解除 P1 HOLD 由有權限的維護者依完整驗收條件判定。

## 證據

[證據目錄](../evidence/console-reverification-20261025/)包含：

- `results.json`：環境、指定提交、47 個來源 pin 核對與逐項驗收結果。
- `init*.log`：全新初始化、相同命令重播與設定衝突拒絕。
- `serve-0.log`、`serve-1.log`：同連接埠、不同 PID、有限生命週期。
- `focused-tests.log`、`junit.xml`：131 項通過的原始測試結果。
- `head.log`、`git-status.log`：版本與產品 checkout 未更動證據。
- `publication-manifest.json`：去識別檔案 SHA256 與處理規則。

發布副本移除主機名、Windows 使用者名稱、本機根路徑及行尾空白；XML
重新序列化。測試數量、錯誤、exit code 與時間保留。原始證據、含本機路徑
的驗證腳本、private state 與 token 均留在本機；憑證洩漏檢查通過。
