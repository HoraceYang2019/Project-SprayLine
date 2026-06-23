# API SQL DB 完整串接教學

## 0. 本教學定位

本教學說明 `0617ver_1` 如何從 API、SQL、PostgreSQL、Database/versionB 一路串起來。

完整流程：

```text
UI
-> FastAPI
-> TimeSeries UI 線 / Service Orchestration 線
-> 少榆 IntegratedSprayLineService / FutureService / MonitoringWorker
-> Database/versionB
-> PostgreSQL
-> SQL 查驗結果
```

本教學只針對 **噴塗線 SprayLine**，不包含 CNC 範例。

---

## 1. 資料夾放置位置

建議放置：

```text
Project-SprayLine-main/
├─ Database/
│  └─ versionB/
└─ SprayLine_3/
   └─ 少榆0617ver_1/
```

注意：`少榆0617ver_1` 要放在 `SprayLine_3` 裡面。  
`Database/versionB` 要在專案根目錄的 `Database` 裡面。

---

## 2. PowerShell 切換到少榆資料夾

```powershell
cd "C:\你的路徑\Project-SprayLine-main\SprayLine_3\少榆0617ver_1"
```

---

## 3. 設定 PostgreSQL / Database/versionB 環境變數

請依余宇承電腦上的實際設定修改：

```powershell
$env:SPRAYLINE_PROJECT_ROOT="C:\你的路徑\Project-SprayLine-main"

$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_USER="postgres"
$env:DB_PASSWORD="你的PostgreSQL密碼"
$env:DB_NAME="sprayline"

$env:SPRAYLINE_MONITOR_STATIONS="Station_1"
$env:SPRAYLINE_MONITOR_LOOKBACK_MINUTES="10"
$env:SPRAYLINE_DUPLICATE_ALERT_SUPPRESSION_MINUTES="5"
```

如果要手動指定正式 `Database/versionB` 路徑，也可以加：

```powershell
$env:VERSIONB_PATH="C:\你的路徑\Project-SprayLine-main\Database\versionB"
```

建議優先設定：

```text
SPRAYLINE_PROJECT_ROOT
```

這樣 `0617ver_1` 的 `versionb_loader.py` 會優先找到正式 DB function。

---

## 4. 安裝 Python 套件

```powershell
pip install -r webservices\requirements.txt
pip install fastapi uvicorn psycopg2-binary
```

如果已經裝過，可略過。

---

## 5. 確認 DB function loader 是否找到正式 Database/versionB

執行：

```powershell
python -c "from webservices.time_series_api.src.versionb_loader import get_versionb_status; import json; print(json.dumps(get_versionb_status(), ensure_ascii=False, indent=2))"
```

或啟動 API 後打：

```text
GET /api/versionb/status
```

期望看到：

```text
available: true
path: ...Project-SprayLine-main\Database\versionB
```

若 path 跑到：

```text
webservices/time_series_api/external/versionB
```

代表目前吃到 fallback，請檢查：

```text
SPRAYLINE_PROJECT_ROOT
VERSIONB_PATH
```

---

## 6. 啟動 API Server

方式 A：

```powershell
python scripts\run_api_server.py
```

方式 B：

```powershell
uvicorn webservices.api_server:app --host 0.0.0.0 --port 8001 --reload
```

開瀏覽器：

```text
http://127.0.0.1:8001/docs
```

如果看到 Swagger UI，代表 API Server 啟動成功。

---

## 7. API 基本檢查

### 7-1. 健康檢查

```text
GET /health
GET /api/health
GET /
```

### 7-2. 路由檢查

```text
GET /api/routes
```

確認裡面有：

```text
/api/time-series
/api/time-series/ui/summary
/api/time-series/ui/station-detail
/api/time-series/ui/component-detail
/api/service-orchestration/integrated/query
/api/service-orchestration/future/save
/api/service-orchestration/monitoring/run
```

---

## 8. UI 查詢線測試：不寫 DB

### 8-1. TimeSeries UI 查詢

Endpoint：

```text
POST /api/time-series
```

範例 body：

```json
{
  "schema_version": "v1.0",
  "request_id": "REQ_UI_CURRENT_TEST",
  "mode": "time",
  "window_type": "time_slider",
  "slider_value": 0,
  "window_minutes": 30,
  "station_scope": ["Station_1"],
  "requested_metrics": [
    "film_thickness_um",
    "paint_flow_ml_min",
    "air_pressure_bar",
    "spray_width_mm"
  ]
}
```

用途：

```text
UI 拖 time slider 時使用。
預設只查詢，不應寫 DB。
```

---

### 8-2. UI summary

Endpoint：

```text
POST /api/time-series/ui/summary
```

用途：

```text
Manager UI 首頁 summary 或 station cards。
```

---

### 8-3. Station detail

Endpoint：

```text
POST /api/time-series/ui/station-detail
```

用途：

```text
點某一站後，看該站 time-series 和 current snapshot。
```

---

### 8-4. Component detail

Endpoint：

```text
POST /api/time-series/ui/component-detail
```

用途：

```text
點某一元件，例如 nozzle、filter、robot_arm。
```

---

## 9. Service Orchestration 查詢線測試：少榆正式整合 service

Endpoint：

```text
POST /api/service-orchestration/integrated/query
```

範例 body：

```json
{
  "schema_version": "v1.0",
  "request_id": "REQ_SHAOYU_INTEGRATED_QUERY",
  "mode": "time",
  "window_type": "time_slider",
  "slider_value": 0,
  "window_minutes": 30,
  "station_scope": ["Station_1"],
  "requested_metrics": [
    "film_thickness_um",
    "paint_flow_ml_min",
    "air_pressure_bar",
    "spray_width_mm",
    "filter_diff_pressure_bar"
  ],
  "write_back": false
}
```

用途：

```text
UI 或後端查少榆 IntegratedSprayLineService 的整合結果。
write_back=false 表示只查詢，不寫 DB。
```

---

## 10. DB 回寫測試

### 10-1. Future payload，只產生不寫 DB

Endpoint：

```text
POST /api/service-orchestration/future/payload
```

用途：

```text
檢查 future_prediction_result payload 欄位是否正確。
```

---

### 10-2. Future save，寫回 DB

Endpoint：

```text
POST /api/service-orchestration/future/save
```

用途：

```text
寫入 future_prediction_result。
```

執行後用 SQL 查：

```sql
SELECT prediction_id, batch_id, station_id, predicted_ok_rate, predicted_ng_count, risk_level, created_at
FROM future_prediction_result
ORDER BY created_at DESC
LIMIT 10;
```

---

### 10-3. Monitoring run，寫 alert_event / batch_station_status

Endpoint：

```text
POST /api/service-orchestration/monitoring/run
```

範例 body：

```json
{
  "station": "Station_1",
  "lookback_minutes": 10
}
```

執行後用 SQL 查：

```sql
SELECT event_id, batch_id, station_id, sensor_name, measured_value, state, cause, ts, message
FROM alert_event
ORDER BY ts DESC
LIMIT 10;
```

```sql
SELECT acl.alert_id, acl.cause_id, acl.is_primary
FROM alert_cause_link acl
JOIN alert_event ae ON ae.event_id = acl.alert_id
ORDER BY ae.ts DESC
LIMIT 10;
```

```sql
SELECT arl.alert_id, arl.response_id, arl.executed_at, arl.operator_id
FROM alert_response_link arl
JOIN alert_event ae ON ae.event_id = arl.alert_id
ORDER BY ae.ts DESC
LIMIT 10;
```

```sql
SELECT batch_id, station_id,
       robot_arm_state, nozzle_state, filter_state,
       compressor_state, spray_width_state, quality_state,
       write_time
FROM batch_station_status
ORDER BY write_time DESC
LIMIT 10;
```

---

## 11. Integrated run-once：整合查詢 + 可選回寫

Endpoint：

```text
POST /api/service-orchestration/integrated/run-once
```

建議測試時先用：

```json
{
  "slider_value": 0,
  "station_scope": ["Station_1"],
  "window_minutes": 30,
  "write_back": false
}
```

確認 response 正常後，才測：

```json
{
  "slider_value": 30,
  "station_scope": ["Station_1"],
  "window_minutes": 30,
  "write_back": true
}
```

注意：

```text
UI 拖 slider 不應該使用 write_back=true。
write_back=true 應該只由後端定時任務、測試腳本或明確按鈕觸發。
```

---

## 12. API smoke test

執行：

```powershell
python scripts\run_api_smoke_test.py
```

用途：

```text
檢查核心 API endpoint 是否存在、是否能回 JSON、是否沒有名稱跑掉。
```

如果 PostgreSQL 未連線，有些正式 DB route 可能回傳 DB error，但 API Server 不應直接 crash。

---

## 13. 常見問題

### 問題 1：Swagger 打不開

確認 API server 是否啟動：

```powershell
python scripts\run_api_server.py
```

或確認 port：

```text
http://127.0.0.1:8001/docs
```

---

### 問題 2：versionB status 顯示 fallback

代表沒有找到正式 `Database/versionB`。  
請重新設定：

```powershell
$env:SPRAYLINE_PROJECT_ROOT="C:\你的路徑\Project-SprayLine-main"
$env:VERSIONB_PATH="C:\你的路徑\Project-SprayLine-main\Database\versionB"
```

---

### 問題 3：UI 查詢時產生太多 DB 寫入

確認 UI 使用的是：

```text
POST /api/time-series
POST /api/time-series/ui/summary
POST /api/time-series/ui/station-detail
POST /api/service-orchestration/integrated/query
```

不要讓 UI 拖 slider 使用：

```text
integrated/run-once write_back=true
future/save
monitoring/run
```

---

## 14. 最終驗收清單

```text
1. /docs 可以打開
2. /api/routes 有列出 endpoint
3. /api/versionb/status 找到正式 Database/versionB
4. /api/time-series 可回 UI time-series JSON
5. /api/service-orchestration/integrated/query 可回少榆整合結果
6. /api/service-orchestration/future/save 可寫 future_prediction_result
7. /api/service-orchestration/monitoring/run 可寫 alert_event / batch_station_status
8. SQL 查得到回寫資料
9. UI 拖 slider 不會自動大量寫 DB
10. 全流程只處理 SprayLine，不包含 CNC 範例
```
