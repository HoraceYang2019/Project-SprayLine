# WebServices 說明（少榆0616ver_3）

本資料夾是少榆端 service 層，0616ver_3 的原則是：

```text
直接 import Database/versionB Python function
不自寫 DB SQL
不包 HTTP 對外路由
不新增 FastAPI / API server 檔案
```

## 主要資料夾

```text
integration_adapter/
future_service/
monitoring_worker/
event_rule_service/
troubleshooting_service/
```

## integration_adapter

```text
webservices/integration_adapter/database_versionb_adapter.py
```

集中處理 `Database/versionB` import path，並包裝少榆端會用到的 DB function：

```text
db_sensor.query_sensor_1min / query_sensor_3min
db_alert.insert_alert_event / link_alert_cause / link_alert_response
db_status.get_batch_station_status / upsert_batch_station_status
db_future.insert_future_prediction_result / get_future_prediction_summary
```

## future_service

產生並寫入 `future_prediction_result` payload。欄位已對齊 `Database/versionB`。

## monitoring_worker

主流程：

```text
查 sensor_1min / sensor_3min
-> 判斷 threshold
-> 補 issue_state / cause_id / response_id
-> 寫 alert_event + cause/response link
-> 更新 batch_station_status 完整快照
```

重要檔案：

```text
monitoring_worker.py
threshold_evaluator.py
detection_mapping.py
alert_event_writer.py
batch_station_status_writer.py
```

## 待確認

```text
data_quality_flag 是否保留 outlier
sensor_threshold table 是否保留備用
alert_event.cause 是否固定放 cause_id
是否改用 sprayline_db_queries.py 當唯一整合入口
duplicate alert suppression 是否要做
```
