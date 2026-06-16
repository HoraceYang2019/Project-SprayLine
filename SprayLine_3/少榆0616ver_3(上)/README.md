# 少榆0616ver_3

本版以 GitHub `Project-SprayLine-main_0616_1400pm` 為 base，參考 `少榆0616ver_1` 的候選 patch 後整理成新版資料夾：

```text
Project-SprayLine-main/SprayLine_3/少榆0616ver_3/
```

本版延續 0614 版的 README / Markdown 快速上手習慣，另新增：

```text
README_快速上手.md
0616ver_3_修改報告.md
docs/使用說明_開啟檔案與執行流程.md
docs/notes/0616_integration_action_plan.md
```

## 本版主軸

```text
少榆端直接 import Database/versionB 的 Python DB function，不走 HTTP 對外路由。
少榆端不負責正式 API Server，也不新增 FastAPI / API server 檔案。
```

少榆端負責：

```text
FutureService
MonitoringWorker / Timer
EventRule
Alert / Prediction payload
TroubleshootingService
Ontology / Knowledge 對應
與 Database/versionB 的直接 function 整合
```

不負責：

```text
正式 FastAPI Server
正式 HTTP API endpoint
DB schema 最終維護
Manager / Engineer UI 前端大改
```

## 0616ver_3 已處理

1. 合併 `少榆0614ver_3(上)` / `少榆0614ver_3(下)`，不再拆上下包。
2. `future_prediction_result` 改為已由 `Database/versionB` 提供。
3. `FutureService` 移除 `舊 persistence 欄位`。
4. `FutureService` 新增 `save_future_prediction_result()`，呼叫 `db_future.insert_future_prediction_result()`。
5. `MonitoringWorker` 改成透過 adapter 呼叫 `db_sensor.query_sensor_1min()` / `query_sensor_3min()`。
6. `alert_event` 寫入改成呼叫 `db_alert.insert_alert_event()`，並可依 mapping 呼叫 `link_alert_cause()` / `link_alert_response()`。
7. `batch_station_status` 更新改成呼叫 `db_status.get_batch_station_status()` + `db_status.upsert_batch_station_status()`，避免只送單一 component state 覆蓋其他欄位。
8. Threshold 保留 JSON config：`rules/sensor_thresholds.json`。
9. 文件補上：`sensor_threshold` DB table 目前存在，但少榆端依討論先使用 JSON config。
10. 新增 / 補強 `webservices/integration_adapter/`，集中處理 `Database/versionB` import path。
11. 文件更新為：少榆端直接 import DB function，不走 HTTP 對外路由。
12. 使用說明更新 `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` 設定方式。
13. 新增 `rules/sensor_event_mapping.json`，先將 sensor 對應到 issue_state / cause_id / response_id / batch_station_status 欄位；此 mapping 仍待余宇承確認。
14. 修正 `external/Database/versionB/SETUP_GUIDE.md`：路徑統一為 `Database/versionB`，不再寫舊 DB 資料夾；也移除不存在的 demo data script 執行指令。

## 建議先看

```text
README_快速上手.md
0616ver_3_修改報告.md
docs/使用說明_開啟檔案與執行流程.md
docs/notes/0616_integration_action_plan.md
webservices/integration_adapter/database_versionb_adapter.py
webservices/future_service/future_service.py
webservices/monitoring_worker/monitoring_worker.py
webservices/monitoring_worker/detection_mapping.py
rules/sensor_thresholds.json
rules/sensor_event_mapping.json
external/Database/versionB/
```

## 快速測試

```bash
cd 少榆0616ver_3
pip install -r webservices/requirements.txt
python -m webservices.integration_adapter.database_versionb_adapter
python -m webservices.future_service.future_service
```

`MonitoringWorker` 需要 PostgreSQL DB 可連線後才能完整執行：

```bash
python -m webservices.monitoring_worker.monitoring_worker
```

## 目前仍待余宇承確認

```text
1. data_quality_flag 最終是否只保留 normal / interpolated，或保留 outlier。
2. sensor_threshold table 是保留備用，還是未來會移除。
3. alert_event.cause 是否正式固定放 cause_catalog.cause_id。
4. 少榆端是否可改以 Database/versionB/sprayline_db_queries.py 作為唯一整合入口。
5. MonitoringWorker 是否要做 duplicate alert suppression，避免同一異常每分鐘重複寫入。
```

0616ver_3 先做「安全整合版」：已知方向先完成，未確認事項不刪 schema、不寫死結論，只在文件與 mapping 中標註待確認。
