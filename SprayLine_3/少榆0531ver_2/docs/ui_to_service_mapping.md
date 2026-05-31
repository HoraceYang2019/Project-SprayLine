<!--
檔案備註：
UI 對 service 欄位對照表：從最終 UI 畫面反推 service 欄位，說明每個 UI 區塊要讀哪個欄位。

資料夾流程定位：流程 Step 1：從 UI 需求反推 service 欄位。
-->

# UI to Service Mapping

| UI 區塊 | UI 顯示內容 | service 欄位 |
|---|---|---|
| Summary Card | 總站數 Total Stations | `summary.total_station_count` |
| Summary Card | 正常 Normal | `summary.normal_count` |
| Summary Card | 注意 Warning | `summary.warning_count` |
| Summary Card | 預測風險 Predict Risk | `summary.predict_risk_count` |
| Station Card | 站別名稱 | `stations[].station_name_zh`, `stations[].station_name_en` |
| Station Card | 狀態 badge | `stations[].state` |
| Component Overview | 手臂 Arm | `stations[].component_overview[].component_key = arm` |
| Component Overview | 噴嘴 Nozzle | `stations[].component_overview[].component_key = nozzle` |
| Component Overview | 空壓機 AirCompressor | `stations[].component_overview[].component_key = air_compressor` |
| Component Overview | 氣閥 Air Valve | `stations[].component_overview[].component_key = air_valve` |
| Component Overview | 濾網 Filter Mesh | `stations[].component_overview[].component_key = filter_mesh` |
| Component Overview | 品質 Quality | `stations[].component_overview[].component_key = quality` |
| Part Status | Availability | `stations[].metrics.availability_pct` |
| Part Status | Clog Rate | `stations[].metrics.clog_rate_pct` |
| Part Status | Pressure | `stations[].metrics.pressure_bar` |
| Part Status | Flow Rate | `stations[].metrics.flow_rate_ml_min` |
| Part Status | Maintainability | `stations[].metrics.maintainability_pct` |
| Part Status | Quality Score | `stations[].metrics.quality_score_pct` |
| Process Parameters | Recipe | `stations[].process_parameters.recipe_name` |
| Process Parameters | Temperature | `stations[].process_parameters.temperature_c` |
| Process Parameters | Utilization | `stations[].process_parameters.utilization_pct` |
| Process Parameters | Cycle Time | `stations[].process_parameters.cycle_time_sec` |
| Time Series Viewer | mode | `viewer_state.mode` 或 query `mode` |
| Time Series Viewer | slider | query `slider_value` |
| Time Series Viewer | narrative | `narrative.summary_text` |
| Time Series Viewer | trend | `trend_series[]` |
