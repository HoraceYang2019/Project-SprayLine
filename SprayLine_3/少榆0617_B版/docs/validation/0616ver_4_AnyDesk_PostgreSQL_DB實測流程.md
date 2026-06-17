# 少榆0616ver_4 AnyDesk / PostgreSQL DB 實測流程

本文件給少榆在余宇承的伺服器電腦上實測使用。請不要把 AnyDesk ID、密碼、DB 密碼、IP 寫進 GitHub、README 或報告。

## 0. 實測目標

老師 0610 逐字稿要求的主線是：

```text
Database/versionB 已有 sensor_1min / sensor_3min
-> 少榆 MonitoringWorker 定期查 DB
-> threshold 判斷 warning / fault
-> 寫入 alert_event
-> 建立 alert_cause_link / alert_response_link
-> 更新 batch_station_status
-> FutureService 寫入 future_prediction_result
-> Manager / Engineer UI 後續可由 DB function 查詢
```

本次實測要證明的是「少榆端可以連到正式 Database/versionB 並完成 DB 寫入」，不是測 UI 畫面。

## 1. AnyDesk 連線

1. 開啟 AnyDesk。
2. 輸入組員提供的 AnyDesk ID。
3. 請對方同意連線，或輸入對方另外提供的一次性/臨時密碼。
4. 連線後，所有指令都在遠端電腦上執行。

注意：如果 PostgreSQL 就在遠端電腦本機，則 `DB_HOST` 通常設 `localhost` 或 `127.0.0.1`，不是你自己電腦的 IP。

## 2. 準備資料夾

建議把 `少榆0616ver_4` 放在：

```text
Project-SprayLine-main/
└─ SprayLine_3/
   └─ 少榆0616ver_4/
```

若你是在遠端電腦上直接從 GitHub pull，請先確認最新 repo 內有：

```text
Project-SprayLine-main/Database/versionB/
Project-SprayLine-main/SprayLine_3/少榆0616ver_4/
```

## 3. 開 PowerShell 並設定環境變數

請在遠端電腦開 PowerShell，依實際路徑修改：

```powershell
cd "C:\path\to\Project-SprayLine-main\SprayLine_3\少榆0616ver_4"

$env:SPRAYLINE_PROJECT_ROOT="C:\path\to\Project-SprayLine-main"
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_USER="postgres"
$env:DB_PASSWORD="請填余宇承提供的 PostgreSQL 密碼"
$env:DB_NAME="sprayline"

# 可選：限定只測 Station_1，避免三站全跑造成資訊太多
$env:SPRAYLINE_MONITOR_STATIONS="Station_1"
$env:SPRAYLINE_MONITOR_LOOKBACK_MINUTES="10"
$env:SPRAYLINE_DUPLICATE_ALERT_SUPPRESSION_MINUTES="5"
```

如果余宇承提供的是另一台 DB 主機，才把 `DB_HOST` 改成該主機 IP。

## 4. 安裝 Python 套件

```powershell
pip install -r webservices\requirements.txt
```

如果缺 `psycopg2`：

```powershell
pip install psycopg2-binary
```

## 5. 確認 adapter 會抓正式 Database/versionB

```powershell
python -m webservices.integration_adapter.database_versionb_adapter
```

預期重點：

```text
integration_mode = direct_python_import
http_endpoint_used = false
database_versionB_path = ...\Project-SprayLine-main\Database\versionB
```

如果抓到 `少榆0616ver_4\external\Database\versionB`，代表 `SPRAYLINE_PROJECT_ROOT` 沒設好，但仍可做 reference copy 測試；正式整合建議抓專案根目錄的 `Database/versionB`。

## 6. 只測連線，不寫資料

```powershell
python scripts\check_db_connection.py
```

這支是 read-only，會確認：

```text
adapter 找得到 Database/versionB
DB 連線可開啟
可呼叫 get_latest_batches / get_unacknowledged_alerts / get_future_prediction_summary 等函式
```

## 7. 寫入測試資料並跑一次完整流程

在余宇承同意「可以寫測試資料」後，再執行：

```powershell
python scripts\run_db_smoke_test.py --write-test-data --station Station_1
```

這會新增一個測試批次：

```text
B_SHAOYU_E2E_YYYYMMDD_HHMMSS
```

並寫入一筆 `filter_diff_pressure_bar = 0.95` 的 sensor_1min，依 `rules/sensor_thresholds.json` 會被判定為 `fault`，理論上會觸發：

```text
alert_event
alert_cause_link
alert_response_link
batch_station_status
future_prediction_result
```

## 8. 用 SQL 驗證結果

可用 pgAdmin 或 psql 查詢。PowerShell 範例：

```powershell
psql -h $env:DB_HOST -p $env:DB_PORT -U $env:DB_USER -d $env:DB_NAME
```

進入 psql 後查：

```sql
SELECT event_id, batch_id, station_id, sensor_name, measured_value, state, cause, ts, message
FROM alert_event
WHERE batch_id LIKE 'B_SHAOYU_E2E_%'
ORDER BY ts DESC
LIMIT 5;

SELECT acl.alert_id, acl.cause_id, acl.is_primary
FROM alert_cause_link acl
JOIN alert_event ae ON ae.event_id = acl.alert_id
WHERE ae.batch_id LIKE 'B_SHAOYU_E2E_%'
ORDER BY ae.ts DESC
LIMIT 5;

SELECT arl.alert_id, arl.response_id, arl.executed_at, arl.operator_id
FROM alert_response_link arl
JOIN alert_event ae ON ae.event_id = arl.alert_id
WHERE ae.batch_id LIKE 'B_SHAOYU_E2E_%'
ORDER BY ae.ts DESC
LIMIT 5;

SELECT batch_id, station_id, filter_state, filter_response_id, write_time
FROM batch_station_status
WHERE batch_id LIKE 'B_SHAOYU_E2E_%'
ORDER BY write_time DESC
LIMIT 5;

SELECT prediction_id, batch_id, station_id, predicted_ok_rate, predicted_ng_count, risk_level, created_at
FROM future_prediction_result
WHERE batch_id LIKE 'B_SHAOYU_E2E_%'
ORDER BY created_at DESC
LIMIT 5;
```

## 9. 測 duplicate alert suppression

連續執行兩次：

```powershell
python scripts\run_db_smoke_test.py --write-test-data --station Station_1
```

因為每次 batch_id 不同，所以都會新增 alert。

若要測同一批次 / 同一異常不重複，請先只跑一次 `--write-test-data`，然後在 5 分鐘內再執行：

```powershell
python -m webservices.monitoring_worker.monitoring_worker
```

預期第二次會出現類似：

```text
skipped: true
reason: recent_unacknowledged_alert_exists
```

## 10. 不要做的事

```text
不要把 AnyDesk 密碼、DB 密碼、IP 寫進檔案。
不要未經余宇承同意就跑 Database/versionB/setup_db.py，因為 setup_db.py 會重建表格。
不要改 Database/versionB schema。
不要改 UI 同學的前端資料夾。
```
