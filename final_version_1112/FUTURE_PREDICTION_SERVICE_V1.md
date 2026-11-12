# Future Prediction Service v1

## Purpose

Extend the existing Future Service to replace the previous fixed Quality Score degradation with history-based prediction.
The first version uses linear trend extrapolation (`linear_trend_v1`) and predicts raw sensor values before reusing existing process formulas and ontology rules.

## Data flow

```text
Recent 60-minute sensor_1min / sensor_3min history
    -> remove data_quality_flag=interpolated rows
    -> fit one linear trend per raw sensor
    -> extrapolate to prediction_time
    -> clamp slope and physical range
    -> IntegratedSprayLineService.derive_formal_metrics()
    -> ontology/rule classification
    -> Engineer UI endpoints
```

## Predicted raw metrics

- `servo_torque_load_pct`
- `path_error_mm`
- `paint_flow_ml_min`
- `air_pressure_bar`
- `spray_width_mm`
- `filter_diff_pressure_bar`
- `temperature_c`
- `humidity_rh`

Derived metrics such as `estimated_film_thickness_um`, `quality_score_pct`, `flow_error_pct`, `pressure_error_pct`, and `filter_clog_index_pct` are recalculated by the existing Integrated Service formulas.

## Existing endpoint

No new endpoint was added. Future results are returned by the existing endpoints:

```http
POST /api/time-series/ui/summary
POST /api/time-series/ui/station-detail
POST /api/time-series/ui/component-detail
```

The main JSON location is:

```json
{
  "future_prediction": {
    "prediction_method": "linear_trend_v1",
    "horizon_minutes": 60,
    "predicted_metrics": {
      "paint_flow_ml_min": 109.1,
      "filter_diff_pressure_bar": 0.218,
      "air_pressure_bar": 3.141,
      "spray_width_mm": 98.2,
      "servo_torque_load_pct": 49.72,
      "path_error_mm": 0.0495,
      "estimated_film_thickness_um": 14.48,
      "quality_score_pct": 75.91
    },
    "predicted_components": {
      "robot_arm_state": "normal",
      "nozzle_state": "warning",
      "compressor_state": "normal",
      "spray_width_state": "normal",
      "filter_state": "normal",
      "quality_state": "warning",
      "station_state": "warning"
    },
    "cause_ids": ["NOZZLE_CLOG"],
    "response_ids": ["CLEAN_NOZZLE", "REPLACE_NOZZLE"],
    "rule_sources": ["ontology/sprayline_threshold.ttl"],
    "quality_score_semantics": "process_quality_score_not_measured_yield",
    "confidence": {
      "overall": "medium",
      "by_metric": {}
    },
    "metric_diagnostics": {}
  }
}
```

For compatibility, explicit aliases are also placed directly under `future_prediction`, for example:

- `predicted_paint_flow_ml_min`
- `predicted_filter_diff_pressure_bar`
- `predicted_spray_width_mm`
- `predicted_estimated_film_thickness_um`
- `predicted_quality_score_pct`

## Files changed

### Added

- `FUTURE_PREDICTION_SERVICE_V1.md`

### Modified

- `services/future_service/future_service.py`
  - The linear trend predictor is implemented directly in the existing Future Service.
  - No additional prediction service module is created.
- `services/integrated_service/sprayline_integrated_service.py`
- `api/shaoyu_ui_bridge.py`
- `ui/engineer/app/services/dashboard_service.py`

## Database persistence

`future_prediction_result` stores the legacy summary fields together with
`rule_evaluations`, `cause_ids`, `response_ids`, `rule_sources`, quality-score
semantics and an idempotency key. Repeating the same logical prediction updates
the existing row instead of inserting a duplicate.

## Limitations

- This is linear extrapolation, not an ML model.
- At least five valid samples are required per metric; otherwise the service uses the latest valid value with low confidence.
- Interpolated rows are excluded.
- Output bounds and slope guards prevent unreasonable extrapolation.
- `quality_score_pct` is a derived process-quality score, not measured product yield.
- The full `predicted_metrics` object remains in the API response; the persisted rule evidence is stored separately as JSONB.
