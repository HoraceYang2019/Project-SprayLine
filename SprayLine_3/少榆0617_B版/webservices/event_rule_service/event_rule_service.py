import json
from pathlib import Path
from typing import Optional

from webservices.monitoring_worker.alert_event_writer import write_alert_event
from webservices.monitoring_worker.detection_mapping import build_detection_result

RULE_FILE = Path(__file__).resolve().parents[2] / "rules" / "sensor_thresholds.json"


def _in_band(value, band):
    if "min" in band and value < band["min"]:
        return False
    if "min_exclusive" in band and value <= band["min_exclusive"]:
        return False
    if "max" in band and value > band["max"]:
        return False
    if "max_exclusive" in band and value >= band["max_exclusive"]:
        return False
    return True


def classify_value(sensor_name: str, value: float) -> Optional[str]:
    """Classify sensor value using local JSON threshold config.

    0615 討論後，threshold 依余宇承說法先用 JSON config 保存；
    即使 Database/versionB 目前存在 sensor_threshold table，少榆端仍以
    rules/sensor_thresholds.json 作為 Monitoring / EventRule 判斷來源。
    """
    rules = json.loads(RULE_FILE.read_text(encoding="utf-8"))["rules"]
    rule = rules.get(sensor_name)
    if not rule:
        return None
    if any(_in_band(value, b) for b in rule.get("fault", [])):
        return "fault"
    if any(_in_band(value, b) for b in rule.get("warning", [])):
        return "warning"
    if _in_band(value, rule.get("normal", {})):
        return "normal"
    return "warning"


def insert_alert_event(conn, batch_id, station, sensor_name, value, state, timestamp, message=None, cause=None):
    detected = build_detection_result(sensor_name, float(value), state)
    if cause:
        detected["cause"] = cause
        detected["cause_id"] = cause
    if message:
        detected["message"] = message
    row = {"batch_id": batch_id, "station_id": station, "ts": timestamp}
    return write_alert_event(conn, row, detected)


def evaluate_event_rules(
    conn,
    station: str,
    batch_id: str,
    timestamp: str,
    sensor_payload: dict,
    data_quality_flag: Optional[str] = None,
) -> dict:
    if data_quality_flag == "interpolated":
        return {
            "station": station,
            "batch_id": batch_id,
            "timestamp": timestamp,
            "data_quality_flag": data_quality_flag,
            "triggered_events": [],
            "skipped": True,
            "skip_reason": "interpolated_data",
        }

    triggered = []
    for sensor_name, value in sensor_payload.items():
        if value is None:
            continue
        state = classify_value(sensor_name, float(value))
        if state in {"warning", "fault"}:
            triggered.append(
                insert_alert_event(
                    conn,
                    batch_id,
                    station,
                    sensor_name,
                    float(value),
                    state,
                    timestamp,
                    f"{sensor_name} classified as {state}",
                )
            )
    return {
        "station": station,
        "batch_id": batch_id,
        "timestamp": timestamp,
        "data_quality_flag": data_quality_flag,
        "triggered_events": triggered,
        "skipped": False,
        "skip_reason": None,
    }
