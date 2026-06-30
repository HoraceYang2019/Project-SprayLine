from typing import Dict, Any

from webservices.integration_adapter.database_versionb_adapter import (
    insert_alert_event,
    link_alert_cause,
    link_alert_response,
)
from webservices.monitoring_worker.duplicate_alert_guard import is_duplicate_unacknowledged_alert


def write_alert_event(conn, row: Dict[str, Any], detected: Dict[str, Any]) -> Dict[str, Any]:
    """Write one alert_event and optional cause/response links through Database/versionB.

    0616ver_4 對齊 db_alert.py 目前設計：
    - alert_event.cause 先放 cause_catalog.cause_id（例如 FILTER_CLOG）。
    - alert_cause_link / alert_response_link 若 mapping 有值就同步建立。
    - cause_id / response_id 最終語意仍待余宇承確認；本函式不自寫 SQL。
    """
    cause_id = detected.get("cause_id") or detected.get("cause")
    response_ids = list(detected.get("response_ids") or [])

    duplicate_decision = is_duplicate_unacknowledged_alert(conn, row, detected)
    if duplicate_decision.get("duplicate"):
        return {
            "skipped": True,
            "reason": duplicate_decision.get("reason"),
            "existing_event_id": duplicate_decision.get("existing_event_id"),
            "batch_id": row.get("batch_id"),
            "station_id": row.get("station_id"),
            "sensor_name": detected.get("sensor_name"),
            "state": detected.get("state"),
            "severity_state": detected.get("severity_state"),
            "issue_state": detected.get("issue_state"),
            "cause_id": cause_id,
            "suppression_minutes": duplicate_decision.get("suppression_minutes"),
        }

    event_id = insert_alert_event(
        conn,
        batch_id=row["batch_id"],
        station_id=row["station_id"],
        sensor_name=detected["sensor_name"],
        measured_value=detected["measured_value"],
        state=detected["state"],
        cause=cause_id,
        message=detected.get("message") or f"{detected['sensor_name']} classified as {detected['state']}",
        ts=row.get("ts"),
    )

    linked_causes: list[str] = []
    linked_responses: list[str] = []
    if cause_id:
        link_alert_cause(conn, event_id, cause_id, is_primary=True)
        linked_causes.append(cause_id)
    for response_id in response_ids:
        link_alert_response(conn, event_id, response_id)
        linked_responses.append(response_id)

    conn.commit()
    return {
        "event_id": event_id,
        "batch_id": row.get("batch_id"),
        "station_id": row.get("station_id"),
        "sensor_name": detected.get("sensor_name"),
        "state": detected.get("state"),
        "severity_state": detected.get("severity_state"),
        "issue_state": detected.get("issue_state"),
        "fault_state": detected.get("fault_state"),
        "cause_id": cause_id,
        "linked_causes": linked_causes,
        "linked_responses": linked_responses,
        "measured_value": detected.get("measured_value"),
    }
