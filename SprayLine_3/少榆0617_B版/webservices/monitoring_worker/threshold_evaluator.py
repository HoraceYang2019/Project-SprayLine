from typing import Dict, Any, List

from webservices.event_rule_service.event_rule_service import classify_value
from webservices.monitoring_worker.detection_mapping import build_detection_result

ONE_MIN_SENSOR_COLUMNS = [
    "film_thickness_um", "paint_flow_ml_min", "nozzle_roll",
    "filter_diff_pressure_bar", "filter_inflow_ml_min", "filter_outflow_ml_min",
    "pump_current_a", "air_pressure_bar", "spray_width_mm",
    "servo_torque_load_pct", "path_error_mm", "vibration_g",
    "tcp_x_mm", "tcp_y_mm", "tcp_z_mm", "speed_mm_s",
]

THREE_MIN_SENSOR_COLUMNS = [
    "gearbox_temperature_c", "temperature_c", "humidity_rh",
]


def extract_sensor_payload(row: Dict[str, Any], table: str) -> Dict[str, float]:
    cols = ONE_MIN_SENSOR_COLUMNS if table == "sensor_1min" else THREE_MIN_SENSOR_COLUMNS
    return {name: row.get(name) for name in cols if row.get(name) is not None}


def evaluate_sensor_payload(sensor_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    results = []
    for sensor_name, value in sensor_payload.items():
        state = classify_value(sensor_name, float(value))
        if state in {"warning", "fault"}:
            results.append(build_detection_result(sensor_name, float(value), state))
    return results
