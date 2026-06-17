# D 方案整合說明

本版在 B 方案基礎上加入少榆同學 Future / Monitoring / EventRule / Troubleshooting 的 payload 整合。

## 整合範圍

| 模組 | 本版做法 |
|---|---|
| Monitoring | 檢查 sensor_1min / sensor_3min 必要欄位與 data_quality_flag |
| EventRule | 沿用 B 方案 threshold 判斷，並產生 alert_event / batch_station_status payload |
| Future | 當 `slider_value > 0` 時產生 future_prediction_result payload |
| Troubleshooting | 根據 `fault_detail` 查 `troubleshooting_matrix_reference.csv` 產生原因與對策 |
| DB | 先輸出 demo JSON，正式 DB API 後續替換 |

## 資料流

```text
HandleTimeSeriesQuery()
  ↓
ApplySampleMethods()
  ↓
CalculateComponentMetrics()
  ↓
EvaluateEventRules()
  ↓
BuildDIntegrationPayloads()
  ├─ BuildMonitoringPayload()
  ├─ BuildAlertEventPayload()
  ├─ BuildBatchStationStatusPayload()
  ├─ BuildFuturePredictionPayload()
  └─ BuildTroubleshootingPayload()
  ↓
BuildOutput()
```

## Runtime Demo JSON

每次呼叫 service 會在 `data/runtime/` 產生：

```text
alert_event_demo.json
batch_station_status_demo.json
future_prediction_result_demo.json
troubleshooting_result_demo.json
monitoring_result_demo.json
```

這些檔案對應正式 DB/API 要接的 payload。
