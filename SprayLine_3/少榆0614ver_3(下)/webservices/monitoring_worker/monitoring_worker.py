from typing import Optional, Dict, Any, List
import time
import psycopg2.extras

from webservices.db import get_connection
from webservices.monitoring_worker.config import MONITOR_INTERVAL_SECONDS, DEFAULT_LOOKBACK_MINUTES, CHECKPOINT_FILE
from webservices.monitoring_worker.checkpoint_repository import load_checkpoint, save_checkpoint
from webservices.monitoring_worker.threshold_evaluator import extract_sensor_payload, evaluate_sensor_payload
from webservices.monitoring_worker.alert_event_writer import write_alert_event
from webservices.monitoring_worker.batch_station_status_writer import upsert_batch_station_status


def _has_column(conn, table: str, column: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
              SELECT 1 FROM information_schema.columns
              WHERE table_name=%s AND column_name=%s
            )
            """,
            (table, column),
        )
        return bool(cur.fetchone()[0])


def fetch_rows(conn, table: str, station: Optional[str] = None, lookback_minutes: int = DEFAULT_LOOKBACK_MINUTES) -> List[Dict[str, Any]]:
    has_quality = _has_column(conn, table, "data_quality_flag")
    quality_col = ", data_quality_flag" if has_quality else ""
    sql = f"""
        SELECT * {quality_col}
        FROM {table}
        WHERE ts >= NOW() - (%(lookback_minutes)s || ' minutes')::interval
          AND (%(station)s IS NULL OR station_id=%(station)s)
        ORDER BY ts ASC
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, {"lookback_minutes": lookback_minutes, "station": station})
        return [dict(r) for r in cur.fetchall()]


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
            events.append(write_alert_event(conn, row, detected))
            upsert_batch_station_status(conn, batch_id, station_id, detected)
    return {"table": table, "ts": row.get("ts"), "skipped": False, "events": events}


def run_monitoring_once(station: Optional[str] = None, lookback_minutes: int = DEFAULT_LOOKBACK_MINUTES) -> Dict[str, Any]:
    conn = get_connection()
    try:
        result = {"station": station, "lookback_minutes": lookback_minutes, "processed": []}
        for table in ("sensor_1min", "sensor_3min"):
            rows = fetch_rows(conn, table, station, lookback_minutes)
            table_events = []
            for row in rows:
                row_result = process_row(conn, table, row)
                table_events.append(row_result)
            if rows:
                save_checkpoint(CHECKPOINT_FILE, table, str(rows[-1]["ts"]), station)
            result["processed"].append({"table": table, "row_count": len(rows), "rows": table_events})
        return result
    finally:
        conn.close()


def run_forever(station: Optional[str] = None, interval_seconds: int = MONITOR_INTERVAL_SECONDS) -> None:
    while True:
        run_monitoring_once(station=station)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    print(run_monitoring_once())
