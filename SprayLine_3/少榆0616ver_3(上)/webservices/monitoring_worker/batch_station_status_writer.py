from typing import Dict, Any

from webservices.integration_adapter.database_versionb_adapter import (
    get_batch_station_status,
    upsert_batch_station_status as db_upsert_batch_station_status,
)
from webservices.monitoring_worker.detection_mapping import build_batch_station_status_record


def upsert_batch_station_status(conn, batch_id: str, station_id: str, detected: Dict[str, Any]) -> Dict[str, Any]:
    """Update batch_station_status through Database/versionB.db_status.

    db_status.upsert_batch_station_status 會覆蓋 6 個 state + 6 個 response FK，
    因此 0616ver_3 先讀取目前快照，再 merge 本次 detected，最後寫入完整 record。
    """
    if not detected.get("state_field"):
        return {
            "skipped": True,
            "reason": "no_state_field_mapping",
            "sensor_name": detected.get("sensor_name"),
        }

    current = get_batch_station_status(conn, batch_id, station_id)
    record = build_batch_station_status_record(batch_id, station_id, detected, current=current)
    db_upsert_batch_station_status(conn, record)
    conn.commit()
    return {
        "skipped": False,
        "batch_id": batch_id,
        "station_id": station_id,
        "updated_field": detected.get("state_field"),
        "updated_response_field": detected.get("response_field"),
        "state": detected.get("state"),
        "primary_response_id": detected.get("primary_response_id"),
        "record": record,
    }
