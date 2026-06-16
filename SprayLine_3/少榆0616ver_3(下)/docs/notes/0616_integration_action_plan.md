# 0616 Integration Action Plan（0616ver_3）

## 已完成對齊

```text
future_prediction_result 已由 Database/versionB 提供
少榆端直接 import Database/versionB function
不走 HTTP 對外路由
threshold 先使用 rules/sensor_thresholds.json
新增 sensor_event_mapping.json 補 issue_state / cause_id / response_id mapping
```

## 少榆端 Monitoring 流程

```text
MonitoringWorker
-> db_sensor.query_sensor_1min / query_sensor_3min
-> threshold_evaluator + rules/sensor_thresholds.json
-> detection_mapping + rules/sensor_event_mapping.json
-> db_alert.insert_alert_event
-> db_alert.link_alert_cause
-> db_alert.link_alert_response
-> db_status.get_batch_station_status
-> db_status.upsert_batch_station_status
```

## 少榆端 Future 流程

```text
FutureService
-> build_future_prediction_payload
-> db_future.insert_future_prediction_result
-> Manager UI future_prediction_summary
```

## 文件判斷

`Database/versionB/setup_db.sql` 目前存在 `sensor_threshold` table，
但依 0615 對話，threshold 先以 JSON config 保存，不進入少榆端正式流程。  
因此 0616ver_3 仍以 `rules/sensor_thresholds.json` 作為正式判斷來源，
DB table 暫視為備用或 DB 端保留內容。

`rules/sensor_event_mapping.json` 目前是少榆端草案 mapping，目的只是讓 0616ver_3 能把 alert / status payload 補完整。`cause_id` / `response_id` 是否就是正式欄位語意，仍待余宇承確認。

## 已修掉的舊說法

```text
Future 表尚未提供的舊說法
等待余宇承 DB API 的舊說法
等待新增資料表的舊說法
少榆端自行包 Web route 的舊說法
少榆端自行新增 API server 檔案的舊說法
Database 舊路徑
```

## 下一步

1. 等余宇承確認 `data_quality_flag` 是否保留 `outlier`。
2. 等余宇承確認 `sensor_threshold` table 是否保留備用。
3. 等余宇承確認 `alert_event.cause` 是否固定放 `cause_catalog.cause_id`。
4. 等余宇承確認是否用 `sprayline_db_queries.py` 當唯一整合入口。
5. 若 DB 可連線，執行 MonitoringWorker 做端到端測試。
6. 依實測結果決定是否加入 duplicate alert suppression。
