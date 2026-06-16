# TimeSeriesService v3 今日 B / D 方案整合更新報告

## 1. 今日更新目標

今日主要工作是將原本的 `time_series_service_v3` 與少榆同學提供的 `少榆0614ver_3` 邏輯進行整合評估與實作。少榆同學負責的範圍包含 Future、Monitoring、EventRule、Troubleshooting 邏輯與 payload；本次先完成 B 方案，再確認 B 方案可運作後，進一步升級到 D 方案。

本日整合決策如下：

```text
第一階段：B 方案
補齊 component、對齊 sensor 欄位、接入 EventRule threshold，讓 TimeSeriesService 可以產生 station state、component_overview 與 fault_detail。

第二階段：D 方案
在 B 方案基礎上新增 Monitoring、alert_event、batch_station_status、Future prediction、Troubleshooting payload，形成較完整的服務端整合輸出。

第三階段：DB 整合
目前先暫緩，等待 DB schema 完整後再接 PostgreSQL。現階段 D 方案先維持 runtime JSON output。
```

---

## 2. B 方案完成內容

B 方案的目的，是先讓原本 `TimeSeriesService` 的資料計算結果可以和少榆的 EventRule threshold 對齊，並補齊 UI 與後續 rule 判斷需要的 component 資料。

### 2.1 補齊 component_metrics

原本版本主要只有：

```text
nozzle
filter_mesh
spray_width
```

本次 B 方案補齊為 8 個 component：

| component_name | 中文名稱 | 說明 |
|---|---|---|
| `quality_module` | 品質模組 | 膜厚與品質相關指標 |
| `nozzle` | 噴嘴 | 塗料流量、噴嘴角度、堵塞率 |
| `filter_mesh` | 濾網 | 濾網壓差、流量損失、堵塞率 |
| `pump_unit` | 幫浦單元 | 幫浦電流 |
| `air_compressor` | 空壓系統 | 空氣壓力與壓力誤差 |
| `spray_width` | 噴幅 | 噴幅寬度、誤差與覆蓋分數 |
| `robot_arm` | 機械手臂 | 扭矩負載、路徑誤差、震動與 TCP 資訊 |
| `environment` | 環境 | 溫度與濕度 |

補齊後，`station-detail` 與 `component-detail` 都可以取得完整元件資料。

---

### 2.2 對齊少榆 sensor 欄位名稱

為了讓少榆的 EventRule 可以直接判斷 sensor，本次將原本欄位名稱對齊成少榆使用的 sensor 命名。

| 原本概念 | B 方案對齊後欄位 |
|---|---|
| 噴漆流量 | `paint_flow_ml_min` |
| 空氣壓力 | `air_pressure_bar` |
| 濾網入口流量 | `filter_inflow_ml_min` |
| 濾網出口流量 | `filter_outflow_ml_min` |
| 濾網壓差 | `filter_diff_pressure_bar` |
| 噴幅 | `spray_width_mm` |
| 伺服扭矩負載 | `servo_torque_load_pct` |
| 路徑誤差 | `path_error_mm` |
| 震動 | `vibration_g` |
| 溫度 | `temperature_c` |
| 濕度 | `humidity_rh` |
| 膜厚 | `film_thickness_um` |

同時保留部分 UI 相容欄位，例如：

```text
pressure_bar        = air_pressure_bar
flow_rate_ml_min    = paint_flow_ml_min
```

這樣可以避免前端舊欄位失效。

---

### 2.3 修正噴幅範圍

原本 TimeSeriesService 的噴幅範圍約為：

```text
48 ~ 56 mm
```

但少榆的 rule 使用的是：

```text
normal range: 105 ~ 125 mm
```

因此 B 方案已將噴幅目標修正為：

```text
target_spray_width_mm = 115
target_min_mm = 105
target_max_mm = 125
```

避免 EventRule 每次都因噴幅尺度不同而誤判。

---

### 2.4 加入 EventRule adapter

新增：

```text
src/event_rule_adapter.py
config/rules/sensor_thresholds.json
```

整合流程：

```text
sampled sensor data
    ↓
CalculateComponentMetrics()
    ↓
EvaluateEventRules()
    ↓
state / risk_text / component_overview / fault_detail
```

B 方案輸出新增：

```text
station.state
station.risk_text
station.component_overview
station.fault_detail
summary.rule_integrated
```

其中 `component_overview` 會顯示每個 component 的狀態，`fault_detail` 則列出觸發 warning / fault 的 sensor。

---

## 3. Sample Method 更新

本次也補強了 sample method 的說明與 response 顯示。

| time_type | sample_method | 說明 |
|---|---|---|
| `past` | `mean` | 過去時間窗資料取平均 |
| `current` | `recent_average` | 目前狀態取最近 5 筆有效資料平均 |
| `future` | `latest_valid` | 未來資料取最後一筆有效值 |

D 方案後已在 response 的 `viewer_state` 顯示 `sample_method`，方便驗證：

```json
"viewer_state": {
  "time_type": "future",
  "sample_method": "latest_valid"
}
```

---

## 4. B 方案驗證結果

本次已用 Swagger response 驗證 B 方案功能。

### 4.1 Summary 驗證

確認項目：

```text
output_type = ui_summary
stations = 3 筆
summary.rule_integrated = true
```

current 測試結果顯示：

```text
normal_count = 1
warning_count = 2
fault_count = 0
predict_risk_count = 2
```

代表 EventRule 已經套用，而且站點狀態不再是 null。

---

### 4.2 Component 補齊驗證

`station-detail` 回傳中，`component_metrics` 已包含 8 個 component：

```text
quality_module
nozzle
filter_mesh
pump_unit
air_compressor
spray_width
robot_arm
environment
```

`component_overview` 也同樣包含 8 個元件狀態。

---

### 4.3 EventRule 驗證

current summary 中：

```text
M1 = normal
M2 = warning
M3 = warning
```

M2 觸發 3 項警告：

```text
paint_flow_ml_min
spray_width_mm
servo_torque_load_pct
```

M3 觸發 5 項警告：

```text
paint_flow_ml_min
filter_diff_pressure_bar
spray_width_mm
servo_torque_load_pct
path_error_mm
```

代表 `config/rules/sensor_thresholds.json` 已經正確套用到 `fault_detail`。

---

## 5. D 方案完成內容

B 方案確認可運作後，本日進一步升級到 D 方案。D 方案的定位是：在 TimeSeriesService + EventRule 的基礎上，補上少榆負責的 Monitoring、Future、Troubleshooting 與 payload 輸出結構。

新增：

```text
src/d_integration_adapter.py
config/knowledge/troubleshooting_matrix_reference.csv
```

D 方案新增輸出：

```text
monitoring_results
alert_events
batch_station_status
future_prediction_results
troubleshooting_results
```

每站也新增：

```text
d_payloads.monitoring
d_payloads.event_rule
d_payloads.future_prediction
d_payloads.troubleshooting
```

---

## 6. Monitoring 整合

Monitoring payload 用來描述資料接收與資料品質狀態。

檢查項目：

```text
1. sensor_1min_received
2. sensor_3min_received
3. data_quality_flag
4. sample_method
5. missing_required_fields
```

輸出範例：

```json
"monitoring": {
  "status": "normal",
  "sensor_1min_received": true,
  "sensor_3min_received": true,
  "data_quality_flag": "normal",
  "sample_method": "latest_valid"
}
```

---

## 7. EventRule payload 升級

B 方案已產生 `fault_detail`。D 方案進一步把 `fault_detail` 轉成少榆 payload 需要的：

```text
alert_event
batch_station_status
```

### 7.1 alert_event

用來記錄單一 sensor 觸發 warning / fault 的事件。

欄位包含：

```text
event_id
batch_id
station_id
line_id
sensor_name
component_name
measured_value
state
message
rule_source
timestamp
```

### 7.2 batch_station_status

用來記錄每一站的 component 狀態：

```text
robot_arm_state
nozzle_state
filter_state
compressor_state
spray_width_state
quality_state
```

目前狀態仍以 service 內部 `normal / warning / fault` 為主；等 DB 整合時，會再轉成 DB 需要的 `ok / warning / fault`。

---

## 8. Future Prediction 整合

當：

```text
slider_value > 0
```

系統會判定：

```text
time_type = future
sample_method = latest_valid
```

D 方案會產生 `future_prediction_result` payload：

```json
"future_prediction": {
  "batch_id": "BATCH_Station_3_DEMO",
  "station_id": "Station_3",
  "predicted_ok_rate": 79.07,
  "predicted_ng_count": 46,
  "risk_level": "high"
}
```

risk_level 規則：

```text
high   : predicted_ok_rate < 84 或 predicted_ng_count >= 35
medium : predicted_ok_rate < 90 或 predicted_ng_count >= 20
low    : 其他
```

---

## 9. Troubleshooting 整合

目前 Troubleshooting 先使用本機 CSV：

```text
config/knowledge/troubleshooting_matrix_reference.csv
```

流程：

```text
fault_detail
    ↓
sensor_name / component_name
    ↓
查 troubleshooting_matrix_reference.csv
    ↓
輸出 possible cause / countermeasure
```

輸出欄位包含：

```text
state_name
state_description
possible_cause
countermeasure
downtime_estimate_min
skill_required
effectiveness_pct
```

正式 DB 完整後，這一段可以改成查 DB 的 knowledge tables。

---

## 10. D 方案驗證結果

本次已測試 future request：

```json
{
  "schema_version": "v1.0",
  "request_id": "test_D_future",
  "mode": "time",
  "window_type": "2hour",
  "slider_value": 3,
  "line_scope": "all",
  "random_seed": 42
}
```

驗證結果：

```text
viewer_state.time_type = future
viewer_state.sample_method = latest_valid
summary.d_integration_enabled = true
summary.future_prediction_count = 3
alert_event_count = 7
troubleshooting_count = 13
```

Future 模式下，站點結果可產生：

```text
M1 = normal
M2 = warning
M3 = fault
```

其中 M3 因 `paint_flow_ml_min` 過低而判定為 fault，並同步產生 alert_event 與 troubleshooting 建議。

---

## 11. D 方案新增 API

核心 API：

```text
POST /api/time-series
```

UI API：

```text
POST /api/time-series/ui/summary
POST /api/time-series/ui/station-detail
POST /api/time-series/ui/component-detail
```

D 方案查詢 API：

```text
GET  /api/time-series/d/latest
GET  /api/time-series/d/alert-events
GET  /api/time-series/d/future-predictions
GET  /api/time-series/d/troubleshooting
POST /api/time-series/d/alert-acknowledge
```

---

## 12. Runtime JSON 輸出

目前 D 方案暫時不直接寫 PostgreSQL，而是先輸出 runtime JSON，作為後續 DB 整合的 payload 驗證資料。

輸出檔案：

```text
data/runtime/monitoring_result_demo.json
data/runtime/alert_event_demo.json
data/runtime/batch_station_status_demo.json
data/runtime/future_prediction_result_demo.json
data/runtime/troubleshooting_result_demo.json
data/runtime/time_series_latest_output.json
data/runtime/processed_result_database_demo.json
```

---

## 13. DB 整合評估與目前決策

本日也初步檢查 DB 版本 `versionB`。評估結果是：可以整合，但目前先等 DB schema 完整後再做，避免在 DB 欄位尚未完全定案時影響 D 方案穩定性。

目前 DB 需要確認的項目：

```text
1. future_prediction_result 表是否正式加入
2. sensor_threshold 表是否由 DB 管理，或繼續使用 JSON rule
3. sensor_3min 寫入流程是否完整
4. data_quality_flag migration 是否已納入正式 setup
5. normal / ok 狀態命名如何統一
6. alert_event、cause、response 對應方式是否定案
```

目前決策：

```text
D 方案先維持 JSON runtime output。
等 DB schema 完整後，再新增 db_persistence_adapter.py，將 D output 寫入 PostgreSQL。
```

---

## 14. 今日新增與修改檔案整理

### B 方案新增 / 修改

```text
src/event_rule_adapter.py
config/rules/sensor_thresholds.json
src/time_series_service.py
src/random_data_provider.py
src/ui_adapter.py
```

### D 方案新增 / 修改

```text
src/d_integration_adapter.py
config/knowledge/troubleshooting_matrix_reference.csv
src/api_server.py
report/time_series_service_v3_D_integration_report.md
report/time_series_service_v3_D_integration_report.ipynb
examples/requests/request_D_future.json
```

### 文件與資料夾整理

```text
docs/01_integration/B_INTEGRATION_SHAOYU_0614.md
docs/01_integration/D_INTEGRATION_SHAOYU_0614.md
docs/01_integration/FOLDER_LAYOUT_REORGANIZED.md
report/README.md
```

---

## 15. 後續工作規劃

短期維持：

```text
1. D 方案 JSON runtime output
2. UI 使用 D output 顯示 alert / future / troubleshooting
3. EventRule 先使用 config/rules/sensor_thresholds.json
4. Troubleshooting 先使用 config/knowledge/troubleshooting_matrix_reference.csv
```

DB 完整後再做：

```text
1. 新增 db_persistence_adapter.py
2. D output 寫入 PostgreSQL
3. alert_event 寫入 DB
4. batch_station_status 寫入 DB
5. future_prediction_result 寫入 DB
6. troubleshooting 改查 DB knowledge table
7. TimeSeriesService 再逐步改成從 DB 讀 sensor_1min / sensor_3min
```

---

## 16. 結論

今日先完成 B 方案，將原本 TimeSeriesService 補齊為 8 個 component，並對齊少榆同學 EventRule 所需的 sensor 欄位。接著加入 EventRule adapter，透過 `sensor_thresholds.json` 判斷每個 station 與 component 的 normal、warning、fault 狀態，並產生 `component_overview` 與 `fault_detail`。

確認 B 方案通過後，進一步完成 D 方案。D 方案新增 `d_integration_adapter.py`，將 EventRule 結果轉成 Monitoring、alert_event、batch_station_status、Future prediction 與 Troubleshooting payload。Future 模式會在 `slider_value > 0` 時使用 `latest_valid` 作為 sample method，並產生 future prediction 結果。Troubleshooting 目前先以本機 CSV 對照原因與改善建議，後續等 DB schema 完整後再改成正式 DB 整合。
