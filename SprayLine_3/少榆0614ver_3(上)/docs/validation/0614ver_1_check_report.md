# 0614ver_3 Check Report

## 檢查項目

```text
舊秒級表名檢查：僅在說明文字中標示已取消；正式 schema / API / service 不使用
JSON parse：OK
Python syntax：OK
CSV format：UTF-8 BOM + sep=,
主要新增 service：MonitoringWorker、FutureService
```

## 主要資料流

```text
sensor_1min / sensor_3min
→ MonitoringWorker
→ EventRuleService
→ alert_event / batch_station_status
→ API
→ Manager UI / Engineer UI
```
