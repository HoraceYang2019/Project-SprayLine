# TimeSeriesService Sample Method and Formula Notes

本檔案依 `Project-SprayLine-main_0531/WebServices/time_series_service` 整合，已套用本專案命名規則。

## sample_method

| time_type | sample_method |
|---|---|
| past | mean |
| current | recent_average |
| future | latest_valid |

## 已納入公式

- `nozzle_clog_rate_pct = max(0, (nominal_flow_rate_ml_min - flow_rate_ml_min) / nominal_flow_rate_ml_min * 100)`
- `flow_loss_pct = max(0, (in_flow_ml_min - out_flow_ml_min) / in_flow_ml_min * 100)`
- `maintainability_pct = rul_hr / (rul_hr + usage_time_hr) * 100`
- `line_clog_rate_pct = max(nozzle_clog_rate_pct, filter_clog_rate_pct)`
- `line_maintainability_pct = min(nozzle_maintainability_pct, filter_maintainability_pct)`
- `quality_score_pct = ok_count / total_count * 100`，若無此資料則 fallback 至 `coverage_score_pct`
- `utilization_pct = running_time_sec / total_window_time_sec * 100`
- `availability_pct = available_time_sec / planned_time_sec * 100`
- `cycle_time_sec = part_end_time - part_start_time`

## 注意

這些是 TimeSeriesService 的數值計算規則。  
`state`、`risk_text`、`fault_detail`、`component_overview` 仍由外部 Rule Service / Threshold 設計決定。
