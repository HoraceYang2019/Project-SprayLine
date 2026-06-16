# Batch summary 定位說明（少榆0616ver_4）

## 結論

目前少榆0616ver_4 不新增 `batch_summary` table，也不新增 `BatchSummaryService` 主動寫入 summary event。

目前定位採用：

```text
少榆端寫入 alert_event / batch_station_status / future_prediction_result
Manager UI 透過 Database/versionB 的 query function 即時計算或查詢 summary
```

## 原因

老師 0610 逐字稿明確要求：

```text
Alert event 要由 service / timer 產生，並回寫資料庫。
```

這一點少榆端已在 MonitoringWorker 中處理：

```text
threshold warning/fault
-> db_alert.insert_alert_event
-> db_alert.link_alert_cause
-> db_alert.link_alert_response
-> db_status.upsert_batch_station_status
```

但 Database/versionB 目前沒有明確提供：

```text
insert_batch_summary_event()
batch_summary table
```

已存在的是：

```text
get_manager_summary()
get_batch_detail()
get_future_prediction_summary()
batch_station_status
future_prediction_result
alert_event
```

因此 0616ver_4 暫時不擅自新增 DB schema，也不自行設計新的 summary table。

## 若老師後續要求 A 選項

若老師明確要求「少榆端要主動產生 batch_summary event 並回寫 DB」，再新增：

```text
webservices/batch_summary_service/
```

並先跟余宇承確認 DB schema / insert function。

## 目前對外說法

```text
少榆端目前負責產生可被 Manager summary 查到的資料來源：alert_event、batch_station_status、future_prediction_result。
Manager summary 暫由 Database/versionB 的 get_manager_summary() / get_batch_detail() / get_future_prediction_summary() 提供，不另建 batch_summary table。
```
