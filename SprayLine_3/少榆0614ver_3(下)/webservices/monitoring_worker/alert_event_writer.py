from typing import Dict, Any
from webservices.event_rule_service.event_rule_service import insert_alert_event


def write_alert_event(conn, row: Dict[str, Any], detected: Dict[str, Any]) -> Dict[str, Any]:
    return insert_alert_event(
        conn=conn,
        batch_id=row["batch_id"],
        station=row["station_id"],
        sensor_name=detected["sensor_name"],
        value=detected["measured_value"],
        state=detected["state"],
        timestamp=row["ts"],
        message=f"{detected['sensor_name']} classified as {detected['state']}",
    )
