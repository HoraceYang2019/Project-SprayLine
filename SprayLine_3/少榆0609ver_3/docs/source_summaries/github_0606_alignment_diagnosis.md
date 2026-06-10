# GitHub 0606 vs 少榆0602ver_5 差異診斷摘要

## 採用

```text
Database Schema v3：station_config / sensor_threshold / batch_run / sensor_1hz / batch_summary / pdm_degradation_log / alert_event
DataPreprocess：By Time / By Batch 欄位收斂
WebServices：time_series_service_630_V2 作為 TimeSeriesService 參考，不當正式資料
Manager UI：作為 Dashboard / API contract 參考，仍標 mock / pending
```

## 不採用

```text
GitHub SprayLine_3 舊版內容不覆蓋少榆0602ver_5
CNC ontology 專有內容不搬入噴塗 ontology
random demo output 不當正式 DB output
舊 filter_threshold / nozzle_threshold / process_threshold 表名不再作為 DB v3 主表
```
