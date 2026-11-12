"""Data-anchor runner for SprayLine MonitoringWorker.

This module is intentionally separated from monitoring_worker.py
to preserve the existing service API and integration behavior.
"""

from __future__ import annotations

import json
import time
import traceback
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from integration_adapter.database_versionb_adapter import (
    get_connection,
    query_sensor_1min,
    query_sensor_3min,
)
from monitoring_worker.checkpoint_repository import (
    load_checkpoint,
    save_checkpoint,
)
from monitoring_worker.config import (
    CHECKPOINT_FILE,
    DEFAULT_LOOKBACK_MINUTES,
    DEFAULT_STATIONS,
    MONITOR_INTERVAL_SECONDS,
    MONITOR_RUN_MODE,
    MONITOR_TIME_MODE,
)
from monitoring_worker.monitoring_worker import process_row


SUPPORTED_TABLES = {
    "sensor_1min",
    "sensor_3min",
}


def _as_aware_datetime(value: Any) -> Optional[datetime]:
    """Convert DB or ISO timestamp to timezone-aware datetime."""
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )

            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)

            return parsed

        except ValueError:
            return None

    return None


def get_anchor_time(
    conn,
    table: str,
    station: str,
) -> Optional[datetime]:
    """Return wall-clock time or the latest DB timestamp."""
    if MONITOR_TIME_MODE == "wall_clock":
        return datetime.now(timezone.utc)

    if table not in SUPPORTED_TABLES:
        raise ValueError(f"Unsupported table: {table}")

    # The table name is restricted by SUPPORTED_TABLES.
    sql = f"""
        SELECT MAX(ts)
        FROM public.{table}
        WHERE station_id = %s
    """

    cursor = conn.cursor()

    try:
        cursor.execute(sql, (station,))
        row = cursor.fetchone()
    finally:
        cursor.close()

    if not row:
        return None

    return _as_aware_datetime(row[0])


def fetch_incremental_rows(
    conn,
    table: str,
    station: str,
    lookback_minutes: int,
) -> Tuple[
    List[Dict[str, Any]],
    Optional[datetime],
    Optional[str],
    Optional[str],
]:
    """Read rows newer than the station/table checkpoint.

    Returns:
        rows,
        anchor_time,
        checkpoint_before,
        checkpoint_reset_reason
    """
    anchor_time = get_anchor_time(
        conn,
        table,
        station,
    )

    if anchor_time is None:
        return [], None, None, None

    checkpoint_before = load_checkpoint(
        CHECKPOINT_FILE,
        table,
        station,
    )

    checkpoint_time = _as_aware_datetime(
        checkpoint_before
    )

    checkpoint_reset_reason = None

    # The data generator may rebuild the DB and move simulated
    # time backwards. A checkpoint ahead of the data must reset.
    if (
        checkpoint_time is not None
        and checkpoint_time > anchor_time
    ):
        checkpoint_reset_reason = (
            "checkpoint_ahead_of_data_anchor"
        )
        checkpoint_time = None

    if checkpoint_time is None:
        start_time = anchor_time - timedelta(
            minutes=lookback_minutes
        )
    else:
        start_time = checkpoint_time

    if table == "sensor_1min":
        rows = query_sensor_1min(
            conn,
            station,
            start_time,
            anchor_time,
        )
    elif table == "sensor_3min":
        rows = query_sensor_3min(
            conn,
            station,
            start_time,
            anchor_time,
        )
    else:
        raise ValueError(f"Unsupported table: {table}")

    filtered_rows: List[Dict[str, Any]] = []

    # Enforce start < ts <= anchor even if the existing DB
    # wrapper uses inclusive boundaries.
    for row in rows:
        row_time = _as_aware_datetime(
            row.get("ts")
        )

        if row_time is None:
            continue

        if row_time <= start_time:
            continue

        if row_time > anchor_time:
            continue

        filtered_rows.append(row)

    filtered_rows.sort(
        key=lambda item: (
            _as_aware_datetime(item.get("ts"))
            or datetime.min.replace(
                tzinfo=timezone.utc
            )
        )
    )

    return (
        filtered_rows,
        anchor_time,
        checkpoint_before,
        checkpoint_reset_reason,
    )


def run_anchored_once(
    station: Optional[str] = None,
    lookback_minutes: int = DEFAULT_LOOKBACK_MINUTES,
) -> Dict[str, Any]:
    """Process one incremental DB window."""
    conn = get_connection()

    try:
        stations = (
            [station]
            if station
            else DEFAULT_STATIONS
        )

        result: Dict[str, Any] = {
            "worker": "anchored_monitoring_worker",
            "run_mode": MONITOR_RUN_MODE,
            "time_mode": MONITOR_TIME_MODE,
            "lookback_minutes": lookback_minutes,
            "checkpoint_file": CHECKPOINT_FILE,
            "stations": stations,
            "processed": [],
        }

        for current_station in stations:
            for table in (
                "sensor_1min",
                "sensor_3min",
            ):
                (
                    rows,
                    anchor_time,
                    checkpoint_before,
                    checkpoint_reset_reason,
                ) = fetch_incremental_rows(
                    conn,
                    table,
                    current_station,
                    lookback_minutes,
                )

                row_results: List[Dict[str, Any]] = []

                # If process_row raises an exception, the checkpoint
                # is not advanced. This prevents silent data loss.
                for row in rows:
                    row_results.append(
                        process_row(
                            conn,
                            table,
                            row,
                        )
                    )

                checkpoint_after = checkpoint_before

                if rows:
                    final_time = _as_aware_datetime(
                        rows[-1].get("ts")
                    )

                    if final_time is not None:
                        checkpoint_after = (
                            final_time.isoformat()
                        )

                        save_checkpoint(
                            CHECKPOINT_FILE,
                            table,
                            checkpoint_after,
                            current_station,
                        )

                event_count = sum(
                    len(row_result.get("events", []))
                    for row_result in row_results
                )

                result["processed"].append(
                    {
                        "station": current_station,
                        "table": table,
                        "anchor_time": (
                            anchor_time.isoformat()
                            if anchor_time
                            else None
                        ),
                        "checkpoint_before": (
                            checkpoint_before
                        ),
                        "checkpoint_after": (
                            checkpoint_after
                        ),
                        "checkpoint_reset_reason": (
                            checkpoint_reset_reason
                        ),
                        "row_count": len(rows),
                        "event_count": event_count,
                        "rows": row_results,
                    }
                )

        return result

    finally:
        conn.close()


def run_anchored_forever(
    station: Optional[str] = None,
    interval_seconds: int = MONITOR_INTERVAL_SECONDS,
) -> None:
    """Run anchored monitoring continuously."""
    while True:
        try:
            result = run_anchored_once(
                station=station
            )

            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    default=str,
                    indent=2,
                ),
                flush=True,
            )

        except Exception:
            print(
                "[AnchoredMonitoringWorker ERROR]",
                flush=True,
            )
            traceback.print_exc()

        time.sleep(interval_seconds)


if __name__ == "__main__":
    if MONITOR_RUN_MODE == "forever":
        run_anchored_forever()
    else:
        print(
            json.dumps(
                run_anchored_once(),
                ensure_ascii=False,
                default=str,
                indent=2,
            )
        )