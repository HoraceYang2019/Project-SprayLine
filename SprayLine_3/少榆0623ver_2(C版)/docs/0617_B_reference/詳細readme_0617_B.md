# 詳細 README：少榆0617ver_1 SprayLine API 整合版

## 1. 版本定位

`少榆0617ver_1` 是以 `少榆0616_B版 / 0616ver_5` 為基礎整理出的新版本。  
本版重點是讓 UI 可以透過 FastAPI 呼叫少榆端功能，同時保留余宇承 `Database/versionB` 的正式 DB 回寫流程。

本版只處理：

```text
噴塗線 SprayLine
```

不放入老師給的 CNC 範例。

---

## 2. 相對於 0609ver_3 的更新路線

```text
0609ver_3
-> 0616ver_4
-> 0616_B版 / 0616ver_5
-> 0617ver_1
```

### 0609ver_3

主要偏：

```text
template
schema
API requirements
service contract
```

尚未形成完整 DB 回寫與 UI API 串接。

### 0616ver_4

完成少榆端 DB 回寫主線：

```text
sensor_1min / sensor_3min
-> MonitoringWorker
-> threshold
-> alert_event
-> alert_cause_link / alert_response_link
-> batch_station_status
-> future_prediction_result
```

### 0616_B版 / 0616ver_5

補入：

```text
past / current 資料取得
time slider 概念
current snapshot
past window
UI time-series format
```

### 0617ver_1

新增自己的 FastAPI API 入口，整合兩條線：

```text
第一條：TimeSeriesService 的 past/current/future UI 查詢線
第二條：Service orchestration 的少榆正式整合線
```

---

## 3. 本版核心架構

```text
UI
-> FastAPI
-> TimeSeries UI 線 / Service Orchestration 線
-> IntegratedSprayLineService / FutureService / MonitoringWorker / TroubleshootingService
-> Database/versionB
-> PostgreSQL
```

---

## 4. 重要檔案

### 4-1. API 入口

```text
webservices/api_server.py
```

用途：

```text
對外唯一 FastAPI 入口。
UI 組或測試者只需要知道這個入口。
```

實際 routes 實作：

```text
webservices/time_series_api/src/api_server.py
```

---

### 4-2. API 啟動腳本

```text
scripts/run_api_server.py
```

啟動：

```powershell
python scripts\run_api_server.py
```

或：

```powershell
uvicorn webservices.api_server:app --host 0.0.0.0 --port 8001 --reload
```

Swagger：

```text
http://127.0.0.1:8001/docs
```

---

### 4-3. UI bridge

```text
webservices/time_series_api/src/shaoyu_ui_bridge.py
```

用途：

```text
把 UI request 轉成少榆 IntegratedSprayLineService 可用格式。
把少榆 service output 轉成 UI summary / station detail / component detail。
```

---

### 4-4. Service orchestration adapter

```text
webservices/time_series_api/src/service_orchestration_adapter.py
```

用途：

```text
FastAPI route 不直接碰少榆內部 function。
由這支檔案集中呼叫：

IntegratedSprayLineService
FutureService
MonitoringWorker
TroubleshootingService
database_versionb_adapter
```

---

### 4-5. versionB loader

```text
webservices/time_series_api/src/versionb_loader.py
```

用途：

```text
尋找正式 Database/versionB。
避免 API 優先吃到 packaged fallback。
```

搜尋順序：

```text
1. VERSIONB_PATH / SPRAYLINE_DB_FUNCTION_PATH
2. SPRAYLINE_PROJECT_ROOT/Database/versionB
3. Project-SprayLine-main/Database/versionB
4. 少榆 external/Database/versionB
5. time_series_api/external/versionB fallback
```

---

### 4-6. 少榆 Integrated Service

```text
webservices/integrated_service/sprayline_integrated_service.py
```

用途：

```text
past window
current snapshot
future prediction
UI time-series response
optional DB write-back
```

---

### 4-7. DB 回寫相關

```text
webservices/monitoring_worker/alert_event_writer.py
webservices/monitoring_worker/batch_station_status_writer.py
webservices/future_service/future_service.py
webservices/integration_adapter/database_versionb_adapter.py
```

用途：

```text
alert_event 寫回
alert_cause_link / alert_response_link 建立
batch_station_status 更新
future_prediction_result 寫回
```

---

## 5. 兩條 API 線

## 5-1. 第一條：TimeSeriesService UI 查詢線

用途：

```text
給 UI 畫 past/current/future time slider、summary、station detail、component detail。
```

主要 API：

```text
POST /api/time-series
POST /api/time-series/ui/summary
POST /api/time-series/ui/station-detail
POST /api/time-series/ui/component-detail
GET  /api/time-series/demo/current
GET  /api/time-series/demo/past
GET  /api/time-series/demo/future
```

注意：

```text
這條線主要是 UI 查詢線，預設不應寫 DB。
```

---

## 5-2. 第二條：Service orchestration 正式整合線

用途：

```text
讓 UI 或後端可以呼叫少榆正式整合功能。
```

主要 API：

```text
GET  /api/service-orchestration/status
POST /api/service-orchestration/integrated/query
POST /api/service-orchestration/integrated/run-once
GET  /api/service-orchestration/integrated/demo/{time_type}
POST /api/service-orchestration/future/payload
POST /api/service-orchestration/future/save
POST /api/service-orchestration/monitoring/run
GET  /api/service-orchestration/troubleshooting/matrix
GET  /api/service-orchestration/troubleshooting/states/{state}/recommendations
```

注意：

```text
正式 DB 回寫應走這條線。
```

---

## 6. UI 建議使用方式

### 6-1. UI 拖 slider / 查畫面

使用：

```text
POST /api/time-series
POST /api/time-series/ui/summary
POST /api/time-series/ui/station-detail
POST /api/time-series/ui/component-detail
POST /api/service-orchestration/integrated/query
```

這些應以查詢為主，不要造成大量 DB 寫入。

### 6-2. 真的要寫 DB

使用：

```text
POST /api/service-orchestration/future/save
POST /api/service-orchestration/monitoring/run
POST /api/service-orchestration/integrated/run-once
```

其中 `integrated/run-once` 若有 `write_back=true`，才會觸發 DB 回寫。

---

## 7. 環境變數

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

可選：

```powershell
$env:VERSIONB_PATH="C:\你的路徑\Project-SprayLine-main\Database\versionB"
```

---

## 8. 啟動方式

```powershell
cd "C:\你的路徑\Project-SprayLine-main\SprayLine_3\少榆0617ver_1"
python scripts\run_api_server.py
```

打開：

```text
http://127.0.0.1:8001/docs
```

---

## 9. 測試方式

### 9-1. API route smoke test

```powershell
python scripts\run_api_smoke_test.py
```

### 9-2. DB 連線測試

```powershell
python scripts\check_db_connection.py
```

### 9-3. DB smoke test

```powershell
python scripts\run_db_smoke_test.py --write-test-data --station Station_1
```

### 9-4. Past/current/future integrated service 測試

```powershell
python scripts\run_past_current_integrated_demo.py --slider 0 --station Station_1
python scripts\run_past_current_integrated_demo.py --slider -60 --window 30 --station Station_1
python scripts\run_past_current_integrated_demo.py --slider 30 --station Station_1
```

---

## 10. SQL 查驗表

### alert_event

```sql
SELECT event_id, batch_id, station_id, sensor_name, measured_value, state, cause, ts, message
FROM alert_event
ORDER BY ts DESC
LIMIT 10;
```

### alert_cause_link

```sql
SELECT acl.alert_id, acl.cause_id, acl.is_primary
FROM alert_cause_link acl
JOIN alert_event ae ON ae.event_id = acl.alert_id
ORDER BY ae.ts DESC
LIMIT 10;
```

### alert_response_link

```sql
SELECT arl.alert_id, arl.response_id, arl.executed_at, arl.operator_id
FROM alert_response_link arl
JOIN alert_event ae ON ae.event_id = arl.alert_id
ORDER BY ae.ts DESC
LIMIT 10;
```

### batch_station_status

```sql
SELECT batch_id, station_id,
       robot_arm_state, nozzle_state, filter_state,
       compressor_state, spray_width_state, quality_state,
       write_time
FROM batch_station_status
ORDER BY write_time DESC
LIMIT 10;
```

### future_prediction_result

```sql
SELECT prediction_id, batch_id, station_id, predicted_ok_rate, predicted_ng_count, risk_level, created_at
FROM future_prediction_result
ORDER BY created_at DESC
LIMIT 10;
```

---

## 11. 本版完成事項

```text
1. 統一 FastAPI 入口。
2. 讓 UI 可以透過 HTTP call 少榆 function。
3. 整合 TimeSeriesService UI 查詢線。
4. 整合 Service Orchestration 正式整合線。
5. 保留 Database/versionB 正式 DB 回寫流程。
6. 修正 versionB loader 優先順序。
7. UI 查詢預設不寫 DB。
8. 加入 API smoke test。
9. 加入 PostgreSQL / SQL / API 串接教學。
10. 報告 Notebook 依照 0616ver_4、past/current、0617 API 整合順序整理。
```

---

## 12. 尚未完成 / 需實測

```text
1. PostgreSQL 端到端實測需在有 DB 的電腦上跑。
2. UI 前端實際畫面是否完全接上，需要 UI 組測。
3. 若老師要求 batch_summary event 主動寫回 DB，需再確認 schema。
4. 若正式模型取代 demo future rule，FutureService 內部可再替換模型，但 payload 欄位已對齊。
```

---

## 13. 明天報告最短講法

```text
老師，0617ver_1 是把前面少榆端的 DB 回寫主線和 past/current/future 整合，再包成 UI 可以呼叫的 FastAPI。

第一階段 0616ver_4 完成 DB 回寫：
MonitoringWorker、alert_event、batch_station_status、future_prediction_result。

第二階段 0616_B版補 past/current：
past window、current snapshot、time slider 和 UI time-series format。

第三階段 0617ver_1 補 API：
整合 TimeSeriesService UI 查詢線和 Service Orchestration 正式整合線。

UI 現在可以透過 API 呼叫少榆 function，正式 DB 回寫仍然走余宇承 Database/versionB。
```
