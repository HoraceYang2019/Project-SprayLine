# 少榆0616ver_4

本版是 `少榆0616ver_3` 的安全補強版，對照 GitHub `Project-SprayLine-main0616_2000pm` 檢查後整理。

本版仍維持少榆端定位：

```text
FutureService
MonitoringWorker / Timer
EventRule
Alert / Prediction payload
TroubleshootingService
與 Database/versionB 的直接 function 整合
```

本版不負責：

```text
正式 FastAPI Server
正式 HTTP endpoint
Manager / Engineer UI 前端修改
Database/versionB schema 最終維護
WebServices/time_series_service_B 的 demo API 改寫
```

## 0616ver_4 新增重點

相較 `0616ver_3`，本版新增：

```text
1. duplicate alert suppression：避免同一異常在 Timer 每分鐘執行時重複寫入 alert_event。
2. DB connection check script：scripts/check_db_connection.py。
3. DB smoke test script：scripts/run_db_smoke_test.py。
4. AnyDesk / PostgreSQL 實測流程文件。
5. Manager / Engineer UI 可用 DB function 對照表。
6. Batch summary 定位說明。
7. 0610 老師逐字稿要求對照表。
8. GitHub 0616 20:00 WebServices 更新檢查說明。
```

## 本版主流程

```text
DataPreprocess / 聖堯假資料
-> Database/versionB 寫入 sensor_1min / sensor_3min
-> 少榆 MonitoringWorker import db_sensor.query_sensor_1min / query_sensor_3min
-> rules/sensor_thresholds.json 判斷 warning / fault
-> rules/sensor_event_mapping.json 對應 cause_id / response_id / component state
-> duplicate_alert_guard 避免短時間內同一異常重複寫入
-> db_alert.insert_alert_event
-> db_alert.link_alert_cause / link_alert_response
-> db_status.upsert_batch_station_status
-> FutureService 產生 future_prediction_result
-> db_future.insert_future_prediction_result
-> Manager / Engineer UI 後續透過 Database/versionB function 查詢
```

## 快速上手先看

```text
README_快速上手.md
0616ver_4_修改報告.md
docs/validation/0616ver_4_AnyDesk_PostgreSQL_DB實測流程.md
docs/contracts/manager_engineer_ui_db_function_map.md
docs/notes/batch_summary_positioning_0616ver_4.md
docs/validation/0610老師逐字稿要求對照表.md
```

## 不需要 DB 的檢查

```bash
cd 少榆0616ver_4
pip install -r webservices/requirements.txt
python -m webservices.integration_adapter.database_versionb_adapter
python -m webservices.future_service.future_service
```

## 需要 PostgreSQL 的檢查

先設定：

```text
SPRAYLINE_PROJECT_ROOT
DB_HOST
DB_PORT
DB_USER
DB_PASSWORD
DB_NAME
```

然後執行：

```bash
python scripts/check_db_connection.py
python scripts/run_db_smoke_test.py
```

若余宇承同意可寫測試資料：

```bash
python scripts/run_db_smoke_test.py --write-test-data --station Station_1
```

詳細步驟看：

```text
docs/validation/0616ver_4_AnyDesk_PostgreSQL_DB實測流程.md
```

## 目前仍待確認

```text
1. data_quality_flag 最終是否只保留 normal / interpolated，或保留 outlier。
2. sensor_threshold table 是保留備用，還是未來會移除。
3. 少榆端是否可改以 Database/versionB/sprayline_db_queries.py 作為唯一整合入口。
```

目前 `alert_event.cause` 依 `Database/versionB/db_alert.py` 現有註解與函式設計，先放 `cause_catalog.cause_id`，例如 `FILTER_CLOG`。

## 注意

```text
不要把 AnyDesk 密碼、DB 密碼、IP 寫進 GitHub 或報告。
不要未經 DB 負責人同意就執行 setup_db.py，因為它會重建資料表。
不要修改 UI 同學資料夾，少榆端只提供 DB function 對照與資料寫回。
```
