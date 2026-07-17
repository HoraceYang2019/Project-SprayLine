from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

KNOWLEDGE_FILE = Path(__file__).resolve().parents[1] / "config" / "knowledge" / "troubleshooting_matrix_reference.csv"

COMPONENT_TO_ASSET = {
    "quality_module": "QUALITY",
    "nozzle": "NOZZLE",
    "filter_mesh": "FILTER",
    "air_compressor": "AIR_COMPRESSOR",
    "spray_width": "SPRAY_WIDTH",
    "robot_arm": "ROBOT_ARM",
}

SENSOR_TO_ISSUE = {
    "film_thickness_um": "FILM_THICKNESS_OOC",
    "paint_flow_ml_min": "NOZZLE_CLOG",
    "nozzle_roll": "NOZZLE_ANGLE_DRIFT",
    "filter_diff_pressure_bar": "FILTER_CLOG",
    "filter_inflow_ml_min": "FLOW_IMBALANCE",
    "filter_outflow_ml_min": "FLOW_IMBALANCE",
    "air_pressure_bar": "AIR_PRESSURE_UNSTABLE",
    "spray_width_mm": "SPRAY_WIDTH_DEVIATION",
    "servo_torque_load_pct": "SERVO_OVERLOAD",
    "path_error_mm": "PATH_ERROR_HIGH",
    "vibration_g": "VIBRATION_HIGH",
    "gearbox_temperature_c": "GEARBOX_OVERHEAT",
    "temperature_c": "SURFACE_DEFECT",
    "humidity_rh": "SURFACE_DEFECT",
}

RISK_SCORE = {"normal": 0, "warning": 1, "fault": 2}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_monitoring_payload(
    *,
    station: Dict[str, Any],
    sensor_payload: Dict[str, Any],
    sample_method_name: str,
) -> Dict[str, Any]:
    process = station.get("process_parameters", {})
    data_quality_flag = process.get("data_quality_flag")
    required_1min = [
        "film_thickness_um", "paint_flow_ml_min", "filter_diff_pressure_bar",
        "air_pressure_bar", "spray_width_mm", "servo_torque_load_pct",
        "path_error_mm", "vibration_g",
    ]
    required_3min = ["gearbox_temperature_c", "temperature_c", "humidity_rh"]

    missing_1min = [field for field in required_1min if sensor_payload.get(field) is None]
    missing_3min = [field for field in required_3min if sensor_payload.get(field) is None]

    status = "normal"
    if data_quality_flag not in {None, "normal"}:
        status = "warning"
    if missing_1min or missing_3min:
        status = "warning"

    return {
        "status": status,
        "sensor_1min_received": len(missing_1min) == 0,
        "sensor_3min_received": len(missing_3min) == 0,
        "missing_sensor_1min_fields": missing_1min,
        "missing_sensor_3min_fields": missing_3min,
        "data_quality_flag": data_quality_flag,
        "sample_method": sample_method_name,
        "last_update_time": process.get("timestamp") or utc_now(),
        "note": "D-stage Monitoring payload. Prototype checks field completeness and data_quality_flag; formal worker/DB polling can replace this block later.",
    }


def build_alert_event_payloads(station: Dict[str, Any]) -> List[Dict[str, Any]]:
    events = []
    for idx, event in enumerate(station.get("fault_detail", []), start=1):
        state = event.get("state")
        if state not in {"warning", "fault"}:
            continue
        events.append({
            "event_id": f"EVT_{event.get('station_id', 'Station')}_{idx}_{event.get('sensor_name', 'sensor')}",
            "batch_id": event.get("batch_id"),
            "station_id": event.get("station_id"),
            "line_id": event.get("line_id"),
            "sensor_name": event.get("sensor_name"),
            "component_name": event.get("component_name"),
            "component_name_zh": event.get("component_name_zh"),
            "measured_value": event.get("measured_value"),
            "state": state,
            "state_zh": event.get("state_zh"),
            "cause": event.get("message"),
            "ts": event.get("timestamp"),
            "message": event.get("message"),
            "acknowledged_at": None,
            "persistence_status": "payload_ready_demo_json",
        })
    return events


def build_batch_station_status_payload(station: Dict[str, Any]) -> Dict[str, Any]:
    overview = station.get("component_overview", [])
    metrics = station.get("metrics", {})
    return {
        "batch_id": station.get("process_parameters", {}).get("batch_id"),
        "station_id": station.get("station_id"),
        "line_id": station.get("line_id"),
        "station_state": station.get("state"),
        "quality_score_pct": metrics.get("quality_score_pct"),
        "qc_pct": metrics.get("qc_pct") or metrics.get("estimated_defect_rate_pct"),
        "estimated_defect_rate_pct": metrics.get("estimated_defect_rate_pct") or metrics.get("qc_pct"),
        "estimated_film_thickness_um": metrics.get("estimated_film_thickness_um"),
        "normal_component_count": sum(1 for item in overview if item.get("state") == "normal"),
        "warning_component_count": sum(1 for item in overview if item.get("state") == "warning"),
        "fault_component_count": sum(1 for item in overview if item.get("state") == "fault"),
        "updated_at": utc_now(),
        "persistence_status": "payload_ready_demo_json",
    }


def compute_risk_level(predicted_ok_rate: Optional[float], predicted_ng_count: Optional[int]) -> Optional[str]:
    if predicted_ok_rate is None and predicted_ng_count is None:
        return None
    ok = 100.0 if predicted_ok_rate is None else float(predicted_ok_rate)
    ng = 0 if predicted_ng_count is None else int(predicted_ng_count)
    if ok < 84 or ng >= 35:
        return "high"
    if ok < 90 or ng >= 20:
        return "medium"
    return "low"


def build_future_prediction_payload(station: Dict[str, Any], time_type: str) -> Optional[Dict[str, Any]]:
    if time_type != "future":
        return None

    metrics = station.get("metrics", {})
    state = station.get("state")
    quality_score = metrics.get("quality_score_pct")
    if isinstance(quality_score, (int, float)):
        # Demo prediction: future quality is affected by station state and current quality_score.
        penalty = {"normal": 1.0, "warning": 5.0, "fault": 12.0}.get(state, 0.0)
        predicted_ok_rate = max(0.0, min(100.0, float(quality_score) - penalty))
    else:
        predicted_ok_rate = None

    if predicted_ok_rate is None:
        predicted_ng_count = None
    else:
        predicted_ng_count = int(round(max(0.0, 100.0 - predicted_ok_rate) * 2.2))

    return {
        "prediction_id": f"PRED_{station.get('station_id')}_{station.get('process_parameters', {}).get('batch_id')}",
        "batch_id": station.get("process_parameters", {}).get("batch_id"),
        "station_id": station.get("station_id"),
        "prediction_time": utc_now(),
        "predicted_ok_rate": predicted_ok_rate,
        "predicted_ng_count": predicted_ng_count,
        "quality_score": quality_score,
        "risk_level": compute_risk_level(predicted_ok_rate, predicted_ng_count),
        "prediction_method": "deterministic_formula",
        "model_input_source": "sensor_1min;sensor_3min;batch_run;TimeSeriesService_future_latest_valid",
        "persistence_status": "payload_ready_pending_db_api",
    }


def _read_troubleshooting_rows(path: Path = KNOWLEDGE_FILE) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    data = path.read_bytes()
    text = None
    for enc in ("utf-8-sig", "utf-8", "cp950", "big5"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = data.decode("latin1")
    lines = [line for line in text.splitlines() if line.strip() and not line.startswith("sep=")]
    return list(csv.DictReader(lines))


def build_troubleshooting_payload(station: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = _read_troubleshooting_rows()
    results: List[Dict[str, Any]] = []

    for event in station.get("fault_detail", []):
        component_name = event.get("component_name")
        asset_type = COMPONENT_TO_ASSET.get(component_name)
        issue_state = SENSOR_TO_ISSUE.get(event.get("sensor_name"))
        matches = [
            row for row in rows
            if (not asset_type or row.get("component_id") == asset_type)
            and (not issue_state or row.get("state") == issue_state)
        ]
        if not matches and asset_type:
            matches = [row for row in rows if row.get("component_id") == asset_type]
        matches = sorted(matches, key=lambda row: int(row.get("relevance_rank") or 999))[:2]

        for row in matches:
            results.append({
                "station_id": event.get("station_id"),
                "line_id": event.get("line_id"),
                "batch_id": event.get("batch_id"),
                "sensor_name": event.get("sensor_name"),
                "measured_value": event.get("measured_value"),
                "event_state": event.get("state"),
                "component_name": component_name,
                "component_name_zh": event.get("component_name_zh"),
                "troubleshooting_state": row.get("state"),
                "state_name": row.get("state_name"),
                "state_description": row.get("state_description"),
                "severity": row.get("severity"),
                "countermeasure_id": row.get("countermeasure_id"),
                "countermeasure": row.get("countermeasure"),
                "downtime_estimate_min": _to_int(row.get("downtime_estimate_min")),
                "skill_required": row.get("skill_required"),
                "relevance_rank": _to_int(row.get("relevance_rank")),
                "effectiveness_pct": _to_float(row.get("effectiveness_pct")),
                "source_status": row.get("source_status"),
            })
    return results


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_d_integration_payloads(
    *,
    station: Dict[str, Any],
    time_type: str,
    sample_method_name: str,
) -> Dict[str, Any]:
    alert_events = build_alert_event_payloads(station)
    troubleshooting = build_troubleshooting_payload(station)
    future_prediction = build_future_prediction_payload(station, time_type)
    monitoring = build_monitoring_payload(
        station=station,
        sensor_payload=station.get("sensor_payload", {}),
        sample_method_name=sample_method_name,
    )
    return {
        "monitoring": monitoring,
        "event_rule": {
            "station_state": station.get("state"),
            "risk_text": station.get("metrics", {}).get("risk_text"),
            "alert_events": alert_events,
            "batch_station_status": build_batch_station_status_payload(station),
            "source": "B-stage local EventRule + D-stage DB payload adapter",
        },
        "future_prediction": future_prediction,
        "troubleshooting": troubleshooting,
    }


def flatten_d_payloads(stations: List[Dict[str, Any]]) -> Dict[str, Any]:
    alert_events: List[Dict[str, Any]] = []
    batch_station_status: List[Dict[str, Any]] = []
    future_predictions: List[Dict[str, Any]] = []
    troubleshooting: List[Dict[str, Any]] = []
    monitoring: List[Dict[str, Any]] = []

    for station in stations:
        d_payloads = station.get("d_payloads", {})
        event_rule = d_payloads.get("event_rule", {})
        alert_events.extend(event_rule.get("alert_events", []))
        if event_rule.get("batch_station_status"):
            batch_station_status.append(event_rule["batch_station_status"])
        if d_payloads.get("future_prediction"):
            future_predictions.append(d_payloads["future_prediction"])
        troubleshooting.extend(d_payloads.get("troubleshooting", []))
        if d_payloads.get("monitoring"):
            monitoring.append({
                "station_id": station.get("station_id"),
                "line_id": station.get("line_id"),
                **d_payloads["monitoring"],
            })

    return {
        "alert_events": alert_events,
        "batch_station_status": batch_station_status,
        "future_prediction_results": future_predictions,
        "troubleshooting_results": troubleshooting,
        "monitoring_results": monitoring,
    }
