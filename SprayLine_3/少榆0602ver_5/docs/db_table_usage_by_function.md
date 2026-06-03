# DB Table Usage by Service Function

基準版本：`少榆0602ver_2`

本文件完成「第 3 階段：DB Schema v2 / Service Function 對接細化」。

## alert_log

- DB Zone：`Zone6AlertTwin`
- 使用此 table 的 service functions：
  - `acknowledge_alert` → `/api/v1/alerts/{alert_id}/acknowledge`
  - `get_overall_status` → `/api/v1/lines/{line_id}/status`
  - `get_station_risk_detail` → `/api/v1/lines/{line_id}/risk-detail`
  - `list_pending_alerts` → `/api/v1/lines/{line_id}/alerts/pending`
  - `trigger_alert` → `/api/v1/alerts/trigger`

## batch_run

- DB Zone：`Zone2ProductionQuality`
- 使用此 table 的 service functions：
  - `get_yield_comparison` → `/api/v1/lines/{line_id}/charts/yield-comparison`
  - `list_batches_filtered` → `/api/v1/lines/{line_id}/batches`

## component_health_snapshot

- DB Zone：`Zone2ProductionQuality`
- 使用此 table 的 service functions：
  - `get_overall_status` → `/api/v1/lines/{line_id}/status`
  - `get_station_dashboard_status` → `/api/v1/lines/{line_id}/summary`

## component_master

- DB Zone：`Zone1ConfigMaster`
- 使用此 table 的 service functions：
  - `get_station_dashboard_status` → `/api/v1/lines/{line_id}/summary`

## diagnosis_result

- DB Zone：`Zone4KnowledgeDiagnosis`
- 使用此 table 的 service functions：
  - `get_diagnosis_timeline` → `/api/v1/lines/{line_id}/diagnosis/timeline`
  - `get_latest_diagnosis` → `/api/v1/lines/{line_id}/diagnosis/latest`
  - `get_station_risk_detail` → `/api/v1/lines/{line_id}/risk-detail`
  - `list_pending_alerts` → `/api/v1/lines/{line_id}/alerts/pending`
  - `trigger_alert` → `/api/v1/alerts/trigger`

## filter_threshold

- DB Zone：`Zone4KnowledgeDiagnosis`
- 使用此 table 的 service functions：
  - `get_diagnosis_timeline` → `/api/v1/lines/{line_id}/diagnosis/timeline`
  - `get_latest_diagnosis` → `/api/v1/lines/{line_id}/diagnosis/latest`

## ml_feature_snapshot

- DB Zone：`Zone5MLPrediction`
- 使用此 table 的 service functions：
  - `get_ml_feature_input` → `/api/v1/parts/{part_uuid}/ml-features`

## ml_prediction_result

- DB Zone：`Zone5MLPrediction`
- 使用此 table 的 service functions：
  - `get_kpi_summary` → `/api/v1/lines/{line_id}/kpi`
  - `get_latest_prediction` → `/api/v1/parts/{part_uuid}/prediction/latest`
  - `get_overall_status` → `/api/v1/lines/{line_id}/status`
  - `get_prediction_accuracy` → `/api/v1/lines/{line_id}/prediction-accuracy`
  - `get_quality_trend` → `/api/v1/lines/{line_id}/charts/quality-trend`
  - `get_station_risk_detail` → `/api/v1/lines/{line_id}/risk-detail`
  - `get_yield_comparison` → `/api/v1/lines/{line_id}/charts/yield-comparison`
  - `list_batches_filtered` → `/api/v1/lines/{line_id}/batches`
  - `list_pending_alerts` → `/api/v1/lines/{line_id}/alerts/pending`
  - `trigger_alert` → `/api/v1/alerts/trigger`

## nozzle_threshold

- DB Zone：`Zone4KnowledgeDiagnosis`
- 使用此 table 的 service functions：
  - `get_diagnosis_timeline` → `/api/v1/lines/{line_id}/diagnosis/timeline`
  - `get_latest_diagnosis` → `/api/v1/lines/{line_id}/diagnosis/latest`

## omniverse_sync_log

- DB Zone：`Zone6AlertTwin`
- 使用此 table 的 service functions：
  - `get_omniverse_validation_result` → `/api/v1/parts/{part_uuid}/omniverse/validation`

## part_history

- DB Zone：`Zone2ProductionQuality`
- 使用此 table 的 service functions：
  - `get_cycle_time_trend` → `/api/v1/lines/{line_id}/charts/cycle-time-trend`
  - `get_kpi_summary` → `/api/v1/lines/{line_id}/kpi`
  - `get_yield_comparison` → `/api/v1/lines/{line_id}/charts/yield-comparison`

## process_threshold

- DB Zone：`Zone4KnowledgeDiagnosis`
- 使用此 table 的 service functions：
  - `get_diagnosis_timeline` → `/api/v1/lines/{line_id}/diagnosis/timeline`
  - `get_latest_diagnosis` → `/api/v1/lines/{line_id}/diagnosis/latest`

## production_line

- DB Zone：`Zone1ConfigMaster`
- 使用此 table 的 service functions：
  - `get_station_dashboard_status` → `/api/v1/lines/{line_id}/summary`

## qc_result

- DB Zone：`Zone2ProductionQuality`
- 使用此 table 的 service functions：
  - `get_kpi_summary` → `/api/v1/lines/{line_id}/kpi`
  - `get_prediction_accuracy` → `/api/v1/lines/{line_id}/prediction-accuracy`
  - `get_quality_trend` → `/api/v1/lines/{line_id}/charts/quality-trend`
  - `get_yield_comparison` → `/api/v1/lines/{line_id}/charts/yield-comparison`
  - `list_batches_filtered` → `/api/v1/lines/{line_id}/batches`
  - `list_pending_alerts` → `/api/v1/lines/{line_id}/alerts/pending`
  - `trigger_alert` → `/api/v1/alerts/trigger`

## robot_pose

- DB Zone：`Zone3RuntimeSensing`
- 使用此 table 的 service functions：
  - `get_latest_runtime_window` → `/api/v1/lines/{line_id}/stations/latest`

## runtime_metric

- DB Zone：`Zone3RuntimeSensing`
- 使用此 table 的 service functions：
  - `get_kpi_summary` → `/api/v1/lines/{line_id}/kpi`
  - `get_latest_runtime_window` → `/api/v1/lines/{line_id}/stations/latest`
  - `get_metric_trend` → `/api/v1/lines/{line_id}/metrics/{metric_name}/trend`
  - `get_utilization_trend` → `/api/v1/lines/{line_id}/charts/utilization-trend`

## runtime_reference

- DB Zone：`Zone3RuntimeSensing`
- 使用此 table 的 service functions：
  - `get_latest_runtime_window` → `/api/v1/lines/{line_id}/stations/latest`

## runtime_signal

- DB Zone：`Zone3RuntimeSensing`
- 使用此 table 的 service functions：
  - `get_latest_runtime_window` → `/api/v1/lines/{line_id}/stations/latest`

## runtime_window

- DB Zone：`Zone3RuntimeSensing`
- 使用此 table 的 service functions：
  - `get_latest_runtime_window` → `/api/v1/lines/{line_id}/stations/latest`
  - `get_metric_trend` → `/api/v1/lines/{line_id}/metrics/{metric_name}/trend`

## trajectory_result

- DB Zone：`Zone6AlertTwin`
- 使用此 table 的 service functions：
  - `get_omniverse_validation_result` → `/api/v1/parts/{part_uuid}/omniverse/validation`
