# TimeSeriesService

本資料夾是依照目前討論內容整理出的 service 部分。

## 1. 我要 call 什麼 function

主要 call function：

```python
HandleTimeSeriesQuery()
```

| Function 名稱 | 功能 |
|---|---|
| `HandleTimeSeriesQuery()` | 主入口，UI 或 Integration Service 呼叫 |
| `DetermineTimeType()` | 根據 `slider_value` 判斷 past / current / future |
| `ResolveLineScope()` | 判斷要處理哪些 line |
| `QueryData()` | 查詢或接收 raw data |
| `GetSampleMethod()` | 根據 past / current / future 選擇 sample method |
| `ApplySampleMethods()` | 對整筆 raw data 套用 sample method |
| `ApplySampleMethod()` | 對單一欄位計算代表值 |
| `CalculateNozzleMetrics()` | 計算噴嘴指標 |
| `CalculateFilterMetrics()` | 計算濾網指標 |
| `CalculateSprayWidthMetrics()` | 計算噴幅指標 |
| `CalculateLineMetrics()` | 整合成 line-level metrics |
| `BuildLineOutput()` | 建立單一 line output |
| `BuildOutput()` | 建立完整 service output |

## 2. 我要收到什麼資料

### UI request

```json
{
  "serviceName": "TimeSeriesService",
  "requestId": null,
  "mode": "time",
  "window_type": "current",
  "slider_value": 0,
  "line_scope": "all",
  "requested_metrics": [
    "availability_pct",
    "clog_rate_pct",
    "pressure_bar",
    "flow_rate_ml_min",
    "maintainability_pct",
    "quality_score_pct",
    "risk_text",
    "spray_width_mm",
    "recipe_name",
    "temperature_c",
    "utilization_pct",
    "cycle_time_sec"
  ]
}
```

### raw data 欄位

Nozzle：

```text
spray_pressure_bar
spray_flow_rate_ml_min
nominal_flow_rate_ml_min
nozzle_usage_time_hr
nozzle_rul_hr
```

Filter Mesh：

```text
in_flow_ml_min
out_flow_ml_min
filter_usage_time_hr
filter_rul_hr
```

Spray Width：

```text
spray_width_mm
target_spray_width_mm
target_min_mm
target_max_mm
```

Process / Quality：

```text
temperature_c
recipe_name
running_time_sec
total_window_time_sec
available_time_sec
planned_time_sec
part_start_time
part_end_time
ok_count
total_count
defect
```

## 3. 我要怎麼做計算

### Time type

```text
slider_value < 0  -> past
slider_value == 0 -> current
slider_value > 0  -> future
```

### sample method

| 時間類型 | 數值型資料 |
|---|---|
| past | mean |
| current | recent_average |
| future | latest_valid |

### Nozzle

```text
nozzle_clog_rate_pct =
max(0, (nominal_flow_rate_ml_min - spray_flow_rate_ml_min)
        / nominal_flow_rate_ml_min * 100)
```

```text
nozzle_maintainability_pct =
nozzle_rul_hr / (nozzle_rul_hr + nozzle_usage_time_hr) * 100
```

### Filter Mesh

```text
flow_loss_pct =
max(0, (in_flow_ml_min - out_flow_ml_min)
        / in_flow_ml_min * 100)
```

```text
filter_clog_rate_pct = flow_loss_pct
```

```text
filter_maintainability_pct =
filter_rul_hr / (filter_rul_hr + filter_usage_time_hr) * 100
```

### Spray Width

```text
width_error_mm = spray_width_mm - target_spray_width_mm
```

```text
width_error_pct =
abs(spray_width_mm - target_spray_width_mm)
 / target_spray_width_mm * 100
```

```text
coverage_score_pct = max(0, 100 - width_error_pct)
```

### Line-level metrics

```text
clog_rate_pct = max(nozzle_clog_rate_pct, filter_clog_rate_pct)
```

```text
maintainability_pct = min(nozzle_maintainability_pct, filter_maintainability_pct)
```

```text
quality_score_pct = ok_count / total_count * 100
```

沒有 `ok_count` / `total_count` 時：

```text
quality_score_pct = coverage_score_pct
```

```text
utilization_pct = running_time_sec / total_window_time_sec * 100
availability_pct = available_time_sec / planned_time_sec * 100
cycle_time_sec = part_end_time - part_start_time
```

## 4. 計算完之後要輸出什麼

完整 output 主要結構：

```json
{
  "schema_version": "v1.0",
  "generated_at": null,
  "serviceName": "TimeSeriesService",
  "requestId": null,
  "viewer_state": {},
  "summary": {},
  "stations": [],
  "calculation_info": {}
}
```

每一筆 `stations[]` 包含：

```text
line_id
station_name_zh
station_name_en
state
component_overview
metrics
process_parameters
component_metrics
fault_detail
spray_width_image
```

## 5. Rule 不在本 service 裡

本 service 不負責：

```text
state
risk_text
fault_detail
component_overview
normal_count
warning_count
predict_risk_count
```

這些會先保留為：

```text
state = null
risk_text = null
fault_detail = []
component_overview = []
```

後續交給 Rule Service / Rule Engine 根據本 service 算好的數值判斷。
