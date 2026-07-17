from __future__ import annotations

from typing import Any, Dict, List


LINE_TO_STATION = {
    "line_1": "Station_1",
    "line_2": "Station_2",
    "line_3": "Station_3",
    "M1": "Station_1",
    "M2": "Station_2",
    "M3": "Station_3",
    "Station_1": "Station_1",
    "Station_2": "Station_2",
    "Station_3": "Station_3",
}

STATION_TO_LINE = {
    "Station_1": "line_1",
    "Station_2": "line_2",
    "Station_3": "line_3",
}

STATION_TO_UI = {
    "Station_1": "M1",
    "Station_2": "M2",
    "Station_3": "M3",
}

COMPONENT_METRICS = {
    "quality_module": ["quality_score_pct", "estimated_defect_rate_pct", "qc_pct", "estimated_film_thickness_um", "film_thickness_um", "predicted_ok_rate"],
    "quality": ["quality_score_pct", "estimated_defect_rate_pct", "qc_pct", "estimated_film_thickness_um", "film_thickness_um", "predicted_ok_rate"],
    "nozzle": ["paint_flow_ml_min", "flow_error_pct", "nozzle_flow_loss_pct", "air_pressure_bar"],
    "filter_mesh": ["filter_diff_pressure_bar", "filter_clog_index_pct"],
    "filter": ["filter_diff_pressure_bar", "filter_clog_index_pct"],
    "pump_unit": ["paint_flow_ml_min"],
    "air_compressor": ["air_pressure_bar", "pressure_bar", "pressure_error_pct"],
    "air": ["air_pressure_bar", "pressure_bar", "pressure_error_pct"],
    "spray_width": ["spray_width_mm", "target_spray_width_mm", "spray_width_error_pct", "spray_width_score_pct"],
    "width": ["spray_width_mm", "target_spray_width_mm", "spray_width_error_pct", "spray_width_score_pct"],
    "robot_arm": ["servo_torque_load_pct", "path_error_mm"],
    "arm": ["servo_torque_load_pct", "path_error_mm"],
    "environment": ["temperature_c", "humidity_rh"],
}

COMPONENT_ALIASES = {
    "QUALITY": "quality_module",
    "quality": "quality_module",
    "quality_module": "quality_module",
    "FILTER": "filter_mesh",
    "filter": "filter_mesh",
    "filter_mesh": "filter_mesh",
    "NOZZLE": "nozzle",
    "nozzle": "nozzle",
    "AIR_COMPRESSOR": "air_compressor",
    "air": "air_compressor",
    "air_compressor": "air_compressor",
    "SPRAY_WIDTH": "spray_width",
    "width": "spray_width",
    "spray_width": "spray_width",
    "ROBOT_ARM": "robot_arm",
    "arm": "robot_arm",
    "robot_arm": "robot_arm",
}

COMPONENT_DISPLAY = {
    "robot_arm": {"component_key": "robot_arm", "component_id": "ROBOT_ARM", "name": "機械手臂", "en": "RobotArm", "metric": "servo_torque_load_pct", "unit": "%"},
    "nozzle": {"component_key": "nozzle", "component_id": "NOZZLE", "name": "噴嘴", "en": "Nozzle", "metric": "paint_flow_ml_min", "unit": "ml/min"},
    "air_compressor": {"component_key": "air_compressor", "component_id": "AIR_COMPRESSOR", "name": "空壓機", "en": "AirCompressor", "metric": "air_pressure_bar", "unit": "bar"},
    "spray_width": {"component_key": "spray_width", "component_id": "SPRAY_WIDTH", "name": "噴幅", "en": "SprayWidth", "metric": "spray_width_mm", "unit": "mm"},
    "filter_mesh": {"component_key": "filter", "component_id": "FILTER", "name": "濾網", "en": "FilterMesh", "metric": "filter_diff_pressure_bar", "unit": "bar"},
    "quality_module": {"component_key": "quality", "component_id": "QUALITY", "name": "品質", "en": "Quality", "metric": "quality_score_pct", "unit": "%"},
}


def normalize_component_name(value: Any) -> str:
    if value is None:
        return ""
    return COMPONENT_ALIASES.get(str(value), str(value))


def _round(value: Any, digits: int = 2) -> Any:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(value, digits)
    return value


def resolve_station_scope(value: Any) -> Any:
    if value in (None, "all"):
        return "all"
    if isinstance(value, list):
        return [LINE_TO_STATION.get(item, item) for item in value]
    return LINE_TO_STATION.get(value, value)


def build_integrated_request_from_ui(ui_request: Dict[str, Any]) -> Dict[str, Any]:
    station_scope = ui_request.get("station_scope") or ui_request.get("line_scope") or ui_request.get("line_id") or "all"
    req: Dict[str, Any] = {
        "schema_version": ui_request.get("schema_version", "v1.0"),
        "service_name": "IntegratedSprayLineService",
        "request_id": ui_request.get("request_id"),
        "mode": ui_request.get("mode", "time"),
        "window_type": ui_request.get("window_type", "time_slider"),
        "slider_value": ui_request.get("slider_value", 0),
        "window_minutes": ui_request.get("window_minutes", ui_request.get("past_window_minutes", 30)),
        "station_scope": resolve_station_scope(station_scope),
    }
    anchor_batch_id = ui_request.get("anchor_batch_id") or ui_request.get("batch_anchor_id")
    if anchor_batch_id:
        req["anchor_batch_id"] = anchor_batch_id
    if ui_request.get("batch_id"):
        req["batch_id"] = ui_request.get("batch_id")
    metrics = ui_request.get("requested_metrics")
    if metrics:
        req["requested_metrics"] = metrics
    return req


def _metric_dict_from_station(station: Dict[str, Any]) -> Dict[str, Any]:
    snapshot = station.get("current_snapshot", {}) or {}
    future = station.get("future_prediction_payload", {}) or {}
    future_metrics = future.get("predicted_metrics", {}) or {}
    summary = ((station.get("past_window") or {}).get("summary") or {})
    station_metrics = station.get("metrics") or {}

    # Future v1 exposes predicted sensor/derived values under
    # future_prediction_payload.predicted_metrics.  These values must take
    # precedence over the current snapshot in future mode.
    source_order = (
        (future_metrics, future, snapshot, station_metrics, summary)
        if future
        else (snapshot, station_metrics, summary, future_metrics, future)
    )

    def pick(*keys: str) -> Any:
        for source in source_order:
            for key in keys:
                if source.get(key) is not None:
                    return source.get(key)
        return None

    metrics = {
        "air_pressure_bar": pick("air_pressure_bar"),
        "pressure_bar": pick("air_pressure_bar"),
        "pressure_error_pct": pick("pressure_error_pct", "avg_pressure_error_pct"),
        "paint_flow_ml_min": pick("paint_flow_ml_min"),
        "flow_rate_ml_min": pick("paint_flow_ml_min"),
        "flow_error_pct": pick("flow_error_pct", "avg_flow_error_pct"),
        "nozzle_flow_loss_pct": pick("nozzle_flow_loss_pct", "avg_nozzle_flow_loss_pct"),
        "spray_width_mm": pick("spray_width_mm"),
        "target_spray_width_mm": pick("target_spray_width_mm"),
        "spray_width_error_pct": pick("spray_width_error_pct", "avg_spray_width_error_pct"),
        "spray_width_score_pct": pick("spray_width_score_pct", "avg_spray_width_score_pct"),
        "filter_diff_pressure_bar": pick("filter_diff_pressure_bar"),
        "filter_clog_index_pct": pick("filter_clog_index_pct", "avg_filter_clog_index_pct"),
        "servo_torque_load_pct": pick("servo_torque_load_pct"),
        "path_error_mm": pick("path_error_mm"),
        "temperature_c": pick("temperature_c"),
        "humidity_rh": pick("humidity_rh"),
        "quality_score_pct": pick("quality_score_pct", "avg_quality_score_pct", "quality_score", "predicted_ok_rate"),
        "quality_score": pick("quality_score_pct", "quality_score", "predicted_ok_rate"),
        "estimated_defect_rate_pct": pick("estimated_defect_rate_pct", "qc_pct"),
        "qc_pct": pick("qc_pct", "estimated_defect_rate_pct"),
        "estimated_film_thickness_um": pick("estimated_film_thickness_um", "avg_estimated_film_thickness_um"),
        # Compatibility alias for the existing Engineer UI quality card.
        # The value remains an estimate derived by Integrated Service.
        "film_thickness_um": pick("estimated_film_thickness_um", "film_thickness_um", "avg_estimated_film_thickness_um"),
        "predicted_ok_rate": pick("predicted_ok_rate"),
        "predicted_ng_count": pick("predicted_ng_count"),
        "risk_level": pick("risk_level"),
        "risk_text": pick("risk_level", "risk_text"),
    }
    if future:
        ok_rate = metrics.get("predicted_ok_rate") or metrics.get("quality_score_pct") or metrics.get("quality_score")
        if ok_rate is not None:
            metrics["quality_score_pct"] = ok_rate
            metrics["quality_score"] = ok_rate
            metrics["estimated_defect_rate_pct"] = round(max(0.0, 100.0 - float(ok_rate)), 2)
            metrics["qc_pct"] = metrics["estimated_defect_rate_pct"]
    return {k: _round(v) for k, v in metrics.items() if v is not None}


def _build_component_list(metrics: Dict[str, Any], *, is_future: bool = False) -> List[Dict[str, Any]]:
    """Expose six component values for UI station cards / summary.

    0620ver_1: component-detail already had values, but summary/station cards
    needed the same value/unit/status fields so the UI no longer shows
    "API 無資料" on top cards.
    """
    components: List[Dict[str, Any]] = []
    for canonical, spec in COMPONENT_DISPLAY.items():
        metric = spec["metric"]
        value = metrics.get(metric)
        level = "ok" if value is not None else "unknown"
        components.append({
            **spec,
            "canonical_component_name": canonical,
            "primary_metric": metric,
            "value": value,
            "raw_value": value,
            "status": "normal" if value is not None else "no_data",
            "level": level,
            "source": (
                "FuturePredictionService linear_trend_v1"
                if is_future
                else "IntegratedSprayLineService current_snapshot"
            ),
        })
    return components


def build_ui_station_card(station: Dict[str, Any]) -> Dict[str, Any]:
    station_id = station.get("station_id")
    line_id = station.get("line_id") or STATION_TO_LINE.get(station_id, station_id)
    ui_id = station.get("ui_id") or STATION_TO_UI.get(station_id, station_id)
    metrics = _metric_dict_from_station(station)
    snapshot = station.get("current_snapshot", {}) or {}
    future = station.get("future_prediction_payload")
    state = station.get("state") or "normal"
    risk_level = metrics.get("risk_level")
    if risk_level in ("high", "fault"):
        state = "fault"
    elif risk_level in ("medium", "warning") and state == "normal":
        state = "warning"
    return {
        "id": ui_id,
        "line_id": line_id,
        "station_id": station_id,
        "name": station.get("station_name_zh"),
        "english_name": station.get("station_name_en"),
        "state": state,
        "risk_text": metrics.get("risk_text"),
        "recipe": snapshot.get("recipe_name"),
        "metrics": metrics,
        "components": _build_component_list(metrics, is_future=bool(future)),
        "current_snapshot": snapshot,
        "past_window": station.get("past_window", {}),
        "time_series": station.get("time_series", {}),
        "future_prediction": future,
        "batch_axis": station.get("batch_axis"),
        "source": "IntegratedSprayLineService",
    }


def build_ui_summary_output(core_output: Dict[str, Any]) -> Dict[str, Any]:
    stations = [build_ui_station_card(st) for st in core_output.get("stations", [])]
    state_counts: Dict[str, int] = {}
    for station in stations:
        state = station.get("state", "unknown")
        state_counts[state] = state_counts.get(state, 0) + 1
    return {
        "schema_version": core_output.get("schema_version"),
        "service_name": "Shaoyu0620_API",
        "output_type": "ui_summary",
        "generated_at": core_output.get("generated_at"),
        "request_id": core_output.get("request_id"),
        "viewer_state": core_output.get("viewer_state", {}),
        "summary": {
            "station_count": len(stations),
            "state_counts": state_counts,
        },
        "stations": stations,
        "source": {
            "core_endpoint": "POST /api/time-series",
            "adapter_endpoint": "POST /api/time-series/ui/summary",
            "core_service": "IntegratedSprayLineService",
            "database_persistence": "Database/versionB",
        },
    }


def find_station(core_output: Dict[str, Any], line_or_station_id: str) -> Dict[str, Any] | None:
    target_station = LINE_TO_STATION.get(line_or_station_id, line_or_station_id)
    target_line = STATION_TO_LINE.get(target_station, line_or_station_id)
    for station in core_output.get("stations", []):
        if station.get("station_id") == target_station or station.get("line_id") == target_line:
            return station
    return None


def build_ui_station_detail_output(core_output: Dict[str, Any], line_id: str) -> Dict[str, Any]:
    station = find_station(core_output, line_id)
    if station is None:
        return {
            "success": False,
            "output_type": "ui_station_detail",
            "error_message": f"line_id/station_id not found: {line_id}",
            "available_stations": [s.get("station_id") for s in core_output.get("stations", [])],
        }
    card = build_ui_station_card(station)
    return {
        **card,
        "schema_version": core_output.get("schema_version"),
        "service_name": "Shaoyu0620_API",
        "output_type": "ui_station_detail",
        "generated_at": core_output.get("generated_at"),
        "request_id": core_output.get("request_id"),
        "viewer_state": core_output.get("viewer_state", {}),
    }


def build_ui_component_detail_output(core_output: Dict[str, Any], line_id: str, component_name: str) -> Dict[str, Any]:
    component_name = normalize_component_name(component_name)
    station = find_station(core_output, line_id)
    if station is None:
        return {
            "success": False,
            "output_type": "ui_component_detail",
            "error_message": f"line_id/station_id not found: {line_id}",
        }
    metrics = _metric_dict_from_station(station)
    keys = COMPONENT_METRICS.get(component_name, [])
    component_metrics = {key: metrics.get(key) for key in keys if key in metrics}
    series_points = []
    for point in station.get("time_series", {}).get("points", []):
        item = {"timestamp": point.get("timestamp")}
        for key in keys:
            if key in point:
                item[key] = point[key]
        series_points.append(item)
    return {
        "schema_version": core_output.get("schema_version"),
        "service_name": "Shaoyu0620_API",
        "output_type": "ui_component_detail",
        "generated_at": core_output.get("generated_at"),
        "request_id": core_output.get("request_id"),
        "viewer_state": core_output.get("viewer_state", {}),
        "line_id": station.get("line_id"),
        "station_id": station.get("station_id"),
        "component_name": component_name,
        "metrics": component_metrics,
        "current_snapshot": station.get("current_snapshot", {}),
        "time_series": {
            "point_count": len(series_points),
            "points": series_points,
        },
        "future_prediction": station.get("future_prediction_payload"),
        "source": {
            "core_endpoint": "POST /api/time-series",
            "adapter_endpoint": "POST /api/time-series/ui/component-detail",
            "core_service": "IntegratedSprayLineService",
        },
    }
