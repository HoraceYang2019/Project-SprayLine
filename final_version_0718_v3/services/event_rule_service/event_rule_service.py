from typing import Optional

from event_rule_service.runtime_rule_classifier import classify_sensor_value
from monitoring_worker.alert_event_writer import write_alert_event
from monitoring_worker.detection_mapping import build_detection_result


def classify_value(sensor_name: str, value: float) -> Optional[str]:
    """Backward-compatible state-only wrapper around the Ontology runtime."""
    result = classify_sensor_value(sensor_name, value)
    state = result.get("state")
    return str(state) if state in {"normal", "warning", "fault"} else None


def insert_alert_event(
    conn,
    batch_id,
    station,
    sensor_name,
    value,
    state,
    timestamp,
    message=None,
    cause=None,
    response_ids=None,
    rule_source=None,
    rule_engine=None,
):
    detected = build_detection_result(sensor_name, float(value), state)
    if cause:
        detected["cause"] = cause
        detected["cause_id"] = cause
    if response_ids is not None:
        detected["response_ids"] = list(response_ids)
        detected["primary_response_id"] = response_ids[0] if response_ids else None
    if message:
        detected["message"] = message
    detected["rule_source"] = rule_source
    detected["rule_engine"] = rule_engine
    row = {"batch_id": batch_id, "station_id": station, "ts": timestamp}
    result = write_alert_event(conn, row, detected)
    result["rule_source"] = rule_source
    result["rule_engine"] = rule_engine
    return result


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
        classification = classify_sensor_value(sensor_name, float(value))
        state = classification.get("state")
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
                    cause=classification.get("cause_id"),
                    response_ids=classification.get("response_ids", []),
                    rule_source=classification.get("rule_source"),
                    rule_engine=classification.get("rule_engine"),
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
