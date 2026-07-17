from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

RULE_FILE = Path(__file__).resolve().parents[1] / "rules" / "sensor_thresholds.json"

SENSOR_TO_COMPONENT = {
    "film_thickness_um": "quality_module",
    "paint_flow_ml_min": "nozzle",
    "nozzle_roll": "nozzle",
    "filter_diff_pressure_bar": "filter_mesh",
    "filter_inflow_ml_min": "filter_mesh",
    "filter_outflow_ml_min": "filter_mesh",
    "pump_current_a": "pump_unit",
    "air_pressure_bar": "air_compressor",
    "spray_width_mm": "spray_width",
    "servo_torque_load_pct": "robot_arm",
    "path_error_mm": "robot_arm",
    "vibration_g": "robot_arm",
    "tcp_x_mm": "robot_arm",
    "tcp_y_mm": "robot_arm",
    "tcp_z_mm": "robot_arm",
    "speed_mm_s": "robot_arm",
    "gearbox_temperature_c": "robot_arm",
    "temperature_c": "environment",
    "humidity_rh": "environment",
}

COMPONENT_NAME_ZH = {
    "quality_module": "品質模組",
    "nozzle": "噴嘴",
    "filter_mesh": "濾網",
    "pump_unit": "幫浦單元",
    "air_compressor": "空壓系統",
    "spray_width": "噴幅",
    "robot_arm": "機械手臂",
    "environment": "環境",
}

STATE_PRIORITY = {
    None: 0,
    "normal": 1,
    "ok": 1,
    "warning": 2,
    "fault": 3,
}

STATE_TEXT_ZH = {
    "normal": "正常",
    "warning": "警告",
    "fault": "異常",
}


def _load_rules(rule_file: Path = RULE_FILE) -> Dict[str, Any]:
    if not rule_file.exists():
        return {"version": "missing", "rules": {}}
    return json.loads(rule_file.read_text(encoding="utf-8"))


def _in_band(value: float, band: Dict[str, Any]) -> bool:
    if "min" in band and value < band["min"]:
        return False
    if "min_exclusive" in band and value <= band["min_exclusive"]:
        return False
    if "max" in band and value > band["max"]:
        return False
    if "max_exclusive" in band and value >= band["max_exclusive"]:
        return False
    return True


def classify_value(sensor_name: str, value: Any, rule_file: Path = RULE_FILE) -> Optional[str]:
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None

    rules = _load_rules(rule_file).get("rules", {})
    rule = rules.get(sensor_name)
    if not rule:
        return None

    numeric_value = float(value)

    if any(_in_band(numeric_value, band) for band in rule.get("fault", [])):
        return "fault"

    if any(_in_band(numeric_value, band) for band in rule.get("warning", [])):
        return "warning"

    normal_band = rule.get("normal", {})
    if normal_band and _in_band(numeric_value, normal_band):
        return "normal"

    return "warning"


def worse_state(left: Optional[str], right: Optional[str]) -> Optional[str]:
    return left if STATE_PRIORITY.get(left, 0) >= STATE_PRIORITY.get(right, 0) else right


def evaluate_station_rules(
    *,
    station_id: str,
    line_id: str,
    batch_id: str,
    timestamp: str,
    sensor_payload: Dict[str, Any],
    data_quality_flag: Optional[str] = None,
    rule_file: Path = RULE_FILE,
) -> Dict[str, Any]:
    """
    Local EventRule adapter for B-stage integration.

    This intentionally does not write alert_event to DB.  It only evaluates
    Shaoyu's sensor_thresholds.json and returns state/risk payload for UI.
    """

    if data_quality_flag == "interpolated":
        return {
            "station_id": station_id,
            "line_id": line_id,
            "batch_id": batch_id,
            "timestamp": timestamp,
            "data_quality_flag": data_quality_flag,
            "station_state": "normal",
            "risk_text": None,
            "fault_detail": [],
            "component_overview": build_component_overview({}),
            "triggered_events": [],
            "skipped": True,
            "skip_reason": "interpolated_data",
        }

    component_states: Dict[str, Optional[str]] = {}
    triggered_events: List[Dict[str, Any]] = []
    fault_detail: List[Dict[str, Any]] = []
    station_state: Optional[str] = "normal"

    for sensor_name, value in sensor_payload.items():
        state = classify_value(sensor_name, value, rule_file=rule_file)
        component_name = SENSOR_TO_COMPONENT.get(sensor_name)

        if component_name and state:
            component_states[component_name] = worse_state(component_states.get(component_name, "normal"), state)
            station_state = worse_state(station_state, state)

        if state in {"warning", "fault"}:
            event = {
                "batch_id": batch_id,
                "station_id": station_id,
                "line_id": line_id,
                "sensor_name": sensor_name,
                "component_name": component_name,
                "component_name_zh": COMPONENT_NAME_ZH.get(component_name, component_name),
                "measured_value": value,
                "state": state,
                "state_zh": STATE_TEXT_ZH.get(state, state),
                "timestamp": timestamp,
                "message": f"{sensor_name} classified as {state}",
                "rule_source": "config/rules/sensor_thresholds.json",
            }
            triggered_events.append(event)
            fault_detail.append(event)

    return {
        "station_id": station_id,
        "line_id": line_id,
        "batch_id": batch_id,
        "timestamp": timestamp,
        "data_quality_flag": data_quality_flag,
        "station_state": station_state or "normal",
        "risk_text": build_risk_text(triggered_events),
        "fault_detail": fault_detail,
        "component_overview": build_component_overview(component_states, triggered_events),
        "triggered_events": triggered_events,
        "skipped": False,
        "skip_reason": None,
    }


def build_component_overview(
    component_states: Dict[str, Optional[str]],
    triggered_events: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    triggered_events = triggered_events or []
    ordered_components = [
        "quality_module",
        "nozzle",
        "filter_mesh",
        "pump_unit",
        "air_compressor",
        "spray_width",
        "robot_arm",
        "environment",
    ]

    overview = []
    for component_name in ordered_components:
        state = component_states.get(component_name, "normal") or "normal"
        sensors = [
            event.get("sensor_name")
            for event in triggered_events
            if event.get("component_name") == component_name
        ]
        overview.append({
            "component_name": component_name,
            "component_name_zh": COMPONENT_NAME_ZH.get(component_name, component_name),
            "state": state,
            "state_zh": STATE_TEXT_ZH.get(state, state),
            "triggered_sensors": sensors,
        })
    return overview


def build_risk_text(triggered_events: List[Dict[str, Any]]) -> Optional[str]:
    if not triggered_events:
        return None

    fault_count = sum(1 for event in triggered_events if event.get("state") == "fault")
    warning_count = sum(1 for event in triggered_events if event.get("state") == "warning")

    if fault_count > 0:
        return f"{fault_count} 項異常、{warning_count} 項警告"

    return f"{warning_count} 項警告"
