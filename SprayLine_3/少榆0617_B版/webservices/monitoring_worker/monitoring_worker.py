from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
import time

from webservices.integration_adapter.database_versionb_adapter import get_connection, query_sensor_1min, query_sensor_3min
from webservices.monitoring_worker.config import (
    MONITOR_INTERVAL_SECONDS,
    DEFAULT_LOOKBACK_MINUTES,
    CHECKPOINT_FILE,
    DEFAULT_STATIONS,
)
from webservices.monitoring_worker.checkpoint_repository import save_checkpoint
from webservices.monitoring_worker.threshold_evaluator import extract_sensor_payload, evaluate_sensor_payload
from webservices.monitoring_worker.alert_event_writer import write_alert_event
from webservices.monitoring_worker.batch_station_status_writer import upsert_batch_station_status


def fetch_rows(
    conn,
    table: str,
    station: str,
    lookback_minutes: int = DEFAULT_LOOKBACK_MINUTES,
) -> List[Dict[str, Any]]:
    """Fetch sensor rows via Yu-Cheng Database/versionB.db_sensor query functions."""
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=lookback_minutes)
    if table == "sensor_1min":
        return query_sensor_1min(conn, station, start_time, end_time)
    if table == "sensor_3min":
        return query_sensor_3min(conn, station, start_time, end_time)
    raise ValueError(f"Unsupported table: {table}")


def process_row(conn, table: str, row: Dict[str, Any]) -> Dict[str, Any]:
    if row.get("data_quality_flag") == "interpolated":
        return {"table": table, "ts": row.get("ts"), "skipped": True, "reason": "interpolated_data", "events": []}

    sensor_payload = extract_sensor_payload(row, table)
    detected_list = evaluate_sensor_payload(sensor_payload)
    events = []
    station_id = row.get("station_id")
    batch_id = row.get("batch_id")

    for detected in detected_list:
        if batch_id and station_id:
            event_result = write_alert_event(conn, row, detected)
            status_result = upsert_batch_station_status(conn, batch_id, station_id, detected)
            events.append({"alert_event": event_result, "batch_station_status": status_result})
        else:
            events.append({"skipped": True, "reason": "missing_batch_id_or_station_id", "detected": detected})

    return {"table": table, "ts": row.get("ts"), "skipped": False, "events": events}


def run_monitoring_once(
    station: Optional[str] = None,
    lookback_minutes: int = DEFAULT_LOOKBACK_MINUTES,
) -> Dict[str, Any]:
    conn = get_connection()
    try:
        stations = [station] if station else DEFAULT_STATIONS
        result = {"stations": stations, "lookback_minutes": lookback_minutes, "processed": []}
        for current_station in stations:
            for table in ("sensor_1min", "sensor_3min"):
                rows = fetch_rows(conn, table, current_station, lookback_minutes)
                table_events = [process_row(conn, table, row) for row in rows]
                if rows:
                    save_checkpoint(CHECKPOINT_FILE, table, str(rows[-1]["ts"]), current_station)
                result["processed"].append({
                    "station": current_station,
                    "table": table,
                    "row_count": len(rows),
                    "rows": table_events,
                })
        return result
    finally:
        conn.close()


def run_forever(station: Optional[str] = None, interval_seconds: int = MONITOR_INTERVAL_SECONDS) -> None:
    while True:
        run_monitoring_once(station=station)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    print(run_monitoring_once())
