# TimeSeriesService_B

本版本是 `time_series_service` 方案整合版，基於前版已通過的 component 補齊與 EventRule 驗證，再加入少榆同學負責的 Monitoring / Future / Troubleshooting / EventRule payload 相關輸出。

## 本版定位

```text
TimeSeriesService v3
  + 8 個 component metrics
  + Shaoyu EventRule threshold
  + Monitoring payload
  + alert_event payload
  + batch_station_status payload
  + Future prediction payload
  + Troubleshooting payload
```

本版仍屬 prototype / demo JSON 整合版：

- EventRule 已經會依照 `config/rules/sensor_thresholds.json` 判斷 normal / warning / fault。
- Troubleshooting 先使用 `config/knowledge/troubleshooting_matrix_reference.csv` 做本機查表。
- Future prediction 使用少榆的討論版規則產生 `risk_level`。
- DB 寫入先輸出到 `data/runtime/*.json`，正式 DB API 可後續替換。

## 資料夾結構

```text
time_series_service_v3_D_integrated_clean_layout/
├─ README.md
├─ src/
│  ├─ api_server.py
│  ├─ time_series_service.py
│  ├─ random_data_provider.py
│  ├─ event_rule_adapter.py
│  ├─ d_integration_adapter.py
│  └─ ui_adapter.py
├─ config/
│  ├─ rules/
│  │  └─ sensor_thresholds.json
│  └─ knowledge/
│     └─ troubleshooting_matrix_reference.csv
├─ data/
│  └─ runtime/
├─ examples/
│  ├─ requests/
│  └─ responses/
├─ docs/
│  ├─ 01_integration/
│  ├─ 02_validation/
│  └─ archive/
└─ report/
```

## 啟動方式

```bash
cd time_series_service_v3_D_integrated_clean_layout/src
uvicorn api_server:app --reload --port 8001
```

Swagger：

```text
http://127.0.0.1:8001/docs
```

## 主要 API

核心 API：

```text
POST /api/time-series
```

UI Adapter API：

```text
POST /api/time-series/ui/summary
POST /api/time-series/ui/station-detail
POST /api/time-series/ui/component-detail
```

D 方案 payload 查詢 API：

```text
GET  /api/time-series/d/latest
GET  /api/time-series/d/alert-events
GET  /api/time-series/d/future-predictions
GET  /api/time-series/d/troubleshooting
POST /api/time-series/d/alert-acknowledge
```

## D 方案新增輸出

每一站 station 會新增：

```text
d_payloads.monitoring
d_payloads.event_rule.alert_events
d_payloads.event_rule.batch_station_status
d_payloads.future_prediction
d_payloads.troubleshooting
```

整體 output 會新增：

```text
d_integration.alert_events
d_integration.batch_station_status
d_integration.future_prediction_results
d_integration.troubleshooting_results
d_integration.monitoring_results
```

## Sample Method

| time_type | sample_method | 說明 |
|---|---|---|
| past | mean | 過去時間窗取平均 |
| current | recent_average | 目前狀態取最近 5 筆平均 |
| future | latest_valid | 未來狀態取最後有效值 |

response 的 `viewer_state.sample_method` 會直接顯示目前使用的方法。

## 驗證重點

1. `viewer_state.sample_method` 是否正確。
2. `summary.d_integration_enabled = true`。
3. `d_integration.alert_events` 是否會根據 warning / fault 產生。
4. future 模式是否產生 `future_prediction_results`。
5. 有 fault / warning 時是否產生 `troubleshooting_results`。
6. `data/runtime/` 是否產生 D 方案 demo JSON。
