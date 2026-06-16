# TimeSeriesService v3 B-stage integration with Shaoyu 0614ver_3

本版本是 **B 方案**：補齊 component metrics，並接入少榆 0614ver_3 的 EventRule threshold 判斷，但尚未正式接 DB、Monitoring worker、Future prediction、Troubleshooting DB。

## 已完成

### 1. 補齊 component_metrics

原本只有：

- nozzle
- filter_mesh
- spray_width

本版補齊為：

- quality_module
- nozzle
- filter_mesh
- pump_unit
- air_compressor
- spray_width
- robot_arm
- environment

### 2. 對齊少榆 sensor 欄位

主要欄位改成少榆 `station_sensor_mapping.csv` 的名稱：

- film_thickness_um
- paint_flow_ml_min
- nozzle_roll
- filter_diff_pressure_bar
- filter_inflow_ml_min
- filter_outflow_ml_min
- pump_current_a
- air_pressure_bar
- spray_width_mm
- servo_torque_load_pct
- path_error_mm
- vibration_g
- tcp_x_mm / tcp_y_mm / tcp_z_mm
- speed_mm_s
- gearbox_temperature_c
- temperature_c
- humidity_rh

為了相容舊 UI，也保留舊 alias：

- pressure_bar = air_pressure_bar
- flow_rate_ml_min = paint_flow_ml_min
- in_flow_ml_min = filter_inflow_ml_min
- out_flow_ml_min = filter_outflow_ml_min

### 3. 噴幅範圍對齊少榆 EventRule

噴幅 target 已從原本 52 mm 等級改為：

- target_spray_width_mm = 115
- target_min_mm = 105
- target_max_mm = 125

這樣可與少榆 `sensor_thresholds.json` 中的 `spray_width_mm` rule 對齊。

### 4. 接入 EventRule 判斷

新增：

```text
src/event_rule_adapter.py
rules/sensor_thresholds.json
```

`event_rule_adapter.py` 會讀取少榆的：

```text
rules/sensor_thresholds.json
```

並在 `CalculateLineMetrics()` 中執行 rule 判斷，產生：

- station.state
- metrics.risk_text
- component_overview
- fault_detail
- event_rule_evaluation

## 目前資料流程

```text
HandleTimeSeriesQuery()
  ↓
QueryRawDataFromDatabase()
  ↓
BuildRandomRawDataset() 產生少榆格式 sensor 欄位
  ↓
ApplySampleMethods()
  ↓
CalculateLineMetrics()
  ↓
CalculateComponentMetrics()
  ↓
evaluate_station_rules()
  ↓
BuildOutput()
```

## 尚未做，保留給 D 方案

- MonitoringWorker 正式週期監控
- alert_event 寫入正式 DB
- batch_station_status 寫入正式 DB
- FutureService 預測 payload 正式串接
- TroubleshootingService DB 查詢
- alert acknowledge API

## 測試方式

```bash
cd time_series_service_v3_B_integrated/src
uvicorn api_server:app --reload --port 8001
```

開啟：

```text
http://127.0.0.1:8001/docs
```

先測：

```text
POST /api/time-series/ui/summary
```

request：

```json
{
  "schema_version": "v1.0",
  "request_id": "ui_summary_B_test",
  "mode": "time",
  "window_type": "current",
  "slider_value": 0,
  "line_scope": "all",
  "random_seed": 42
}
```

成功時應該看到：

- summary.rule_integrated = true
- stations[].state 不是 null
- stations[].component_overview 有 8 個元件
- stations[].component_metrics 有 8 個元件
- 若有 warning/fault，stations[].fault_detail 會有內容

## D 方案接續方向

確認 B 方案穩定後，再把 `event_rule_adapter.py` 替換或包裝成少榆正式 service 呼叫：

```text
EventRuleService.evaluate_event_rules()
MonitoringWorker.run_monitoring_once()
FutureService.build_future_prediction_payload()
TroubleshootingService.get_state_recommendations()
```

建議順序：

1. 先接 FutureService payload
2. 再接 Troubleshooting CSV / local knowledge
3. 再接 alert_event DB write
4. 最後接 MonitoringWorker 排程與 ack API
