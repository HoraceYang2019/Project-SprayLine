# 0616ver_3 Check Report

## 已檢查

```text
Python syntax：OK
JSON parse：OK
adapter demo：OK
FutureService demo：OK
```

## 未檢查

```text
MonitoringWorker PostgreSQL 端到端測試
```

原因：目前環境未提供 DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME，不能假裝完成 DB 實測。

## 主要資料流

```text
sensor_1min / sensor_3min
-> MonitoringWorker
-> threshold_evaluator
-> detection_mapping
-> alert_event_writer
-> batch_station_status_writer
-> Database/versionB functions
-> Manager UI / Engineer UI
```
