# 手動啟動的唯讀監控

需要派發任務時，先開啟監控終端，結束後明確停止。Windows / Python3.12+，
只綁定本機127.0.0.1；沒有背景服務、開機自啟或排程。

使用已明確初始化的 console state 與其相符的 handoff config；不會自動初始化、
搬移或升級既有設定。命令中的路徑是範例，須改成自己的絕對 canonical 路徑。
原始雙機 pilot 的 config/store/claim 應保留，不要為此改成可執行。

```powershell
python -B scripts/console_monitor.py start --state-dir C:/Private/console-state --handoff-config C:/Private/handoff.json
```

保持這個前景終端開啟，開啟 http://127.0.0.1:8766，以既有帳號登入。
所有帳號在此工作階段皆只有Viewer檢視權限，原auth.json不會更改。
任務派發仍由既有獨立派發流程進行；監控工作階段不提供派發或執行操作。
每個 console state 同時只能有一個監控管理程序；已占用的連接埠不會被接管。
可用 `--port 8767` 選其他埠，`--interval 120` 調整同步間隔（60..3600秒）。

監控網頁和登入工作階段沒有自動到期；登出或關閉主控台會結束工作階段。
關閉整個瀏覽器後可能需要重新登入。
關閉網頁不會停止監控，關閉監控終端或Ctrl+C會結束本次工作階段。

## 停止與查詢

在原監控終端按Ctrl+C，或從另一個終端使用：

```powershell
python -B scripts/console_monitor.py stop --state-dir C:/Private/console-state
python -B scripts/console_monitor.py status --state-dir C:/Private/console-state
```

`stop_requested=true`表示已送出要求；隨後查詢到 `running=false`、`phase=stopped`
才代表管理程序已結束並確認其子程序清理。`failed`表示監控因錯誤終止，需檢查
`failure`分類並手動重新啟動；`cleanup_unconfirmed`需要人工檢查，
不要將它當成成功停止。`interrupted`表示先前管理程序非正常離開，狀態檔是歷史資料。
管理程序只停止自己持有的Windows Job，不會根據紀錄中的PID停止其他程序。
殘留的舊停止要求綁定舊run_id，不會停止下次新工作階段。

## 同步與異常重啟

每次同步完成後等待60秒再同步；一次同步最多150秒，超時會停止該次擁有的程序樹，
然後按間隔重試。同步只執行 `github_handoff.py sync`：更新本機Git快取與摘要，
不會向遠端寫入queue、不會receive/claim/dispatch，也不會啟動runner/provider。

HTTP子程序離開，或連續三次10秒健康探測失敗後，清理它再延遲重啟。
重啟等待5、10、20、40、60秒，成功探測後恢復5秒；避免快速失敗空轉。
網頁重啟後需重新登入。同步失敗不會清除前次成功快照，也不表示資料仍是最新。

`status`提供 `phase`、`server_restarts`、`sync_attempts`、`last_sync_exit`、
`last_sync_ms`、`sync_error`及終止錯誤的`failure`分類。啟動子程序時若發生
`OSError`或`GuardError`，會清理已擁有的子程序、記錄啟動失敗並退出；不會
把它記成正常停止或在程序歸屬未確認時盲目重試。若健康金鑰檔案無法建立或
替換，會記錄 `HEALTH_SETUP_FAILED`，且不啟動子程序。網頁跨機交接另有實際快照的同步時間及錯誤分類。
HTTP可用只表示本機網頁有回應；遠端最新狀態仍須核對最後同步時間與錯誤。

管理程序本身被關閉或主機重新啟動後，必須手動再次start；它只自動恢復其HTTP及同步
子程序。Windows Job在管理程序退出時清理子程序。沒有外部常駐程序來重啟管理程序本身。
本機session檔放在state-dir旁的 `<state-dir>.monitor` 私人目錄，不加入既有state檔案集合。
不保存登入token、HTTP內容、Git原始輸出或模型對話。
健康檢查以監控私有目錄中的工作階段金鑰、隨機挑戰與子程序 PID 核對唯讀
HTTP 回覆；普通其他服務的 HTTP 200 不會被當作健康。工作階段金鑰保存在
此私人目錄的 `health.json`，每次啟動重新產生，不是登入憑證或供應商金鑰。
Windows狀態查詢造成的短暫檔案共享衝突會在一秒內有限重試，讀者只會看到完整的
前一版或新版JSON；持續的權限／共享拒絕仍會回報失敗，不會覆寫成半份狀態。

## 既有入口與回復

既有 `console_setup.py serve --duration 300` 保持原有時限與角色權限。
一般 `console_setup.py serve` 預設持續執行；`--read-only --duration 0` 開啟唯讀HTTP。
使用監控start入口才能同時取得同步、子程序恢復與stop入口。
此開發變更尚未更新凍結的下載manifest及接受快照，不代表已發布新版本或再次通過雙機驗收。
