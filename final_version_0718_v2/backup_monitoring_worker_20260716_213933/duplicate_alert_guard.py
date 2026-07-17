"""Duplicate alert suppression for MonitoringWorker.

0616ver_4 補強項目：Timer 每分鐘執行時，若同一異常仍在 lookback window 內，
可能會重複寫入 alert_event。本模組透過 Database/versionB.db_alert.get_unacknowledged_alerts()
查詢近期未確認告警，避免少榆端自行維護 alert 查詢 SQL。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from integration_adapter.database_versionb_adapter import get_unacknowledged_alerts
from monitoring_worker.config import DUPLICATE_ALERT_SUPPRESSION_MINUTES


def _as_aware_datetime(value: Any) -> datetime | None:
    """Convert DB ts value to timezone-aware datetime when possible."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def is_duplicate_unacknowledged_alert(
    conn,
    row: Dict[str, Any],
    detected: Dict[str, Any],
    suppression_minutes: int = DUPLICATE_ALERT_SUPPRESSION_MINUTES,
) -> Dict[str, Any]:
    """Return suppression decision for a candidate alert.

    Match key:
    - batch_id
    - station_id
    - sensor_name
    - state / severity_state
    - cause_id / cause

    Only unacknowledged alerts within the recent suppression window are considered duplicates.
    This keeps the service safe during 1-minute Timer checks while still allowing a new alert
    after the suppression window or after an operator acknowledges the old alert.
    """
    if suppression_minutes <= 0:
        return {"duplicate": False, "reason": "suppression_disabled"}

    station_id = row.get("station_id")
    batch_id = row.get("batch_id")
    sensor_name = detected.get("sensor_name")
    state = detected.get("state") or detected.get("severity_state")
    cause_id = detected.get("cause_id") or detected.get("cause")

    if not station_id or not batch_id or not sensor_name or not state:
        return {"duplicate": False, "reason": "insufficient_key"}

    since = datetime.now(timezone.utc) - timedelta(minutes=suppression_minutes)

    try:
        alerts = get_unacknowledged_alerts(conn, station_id=station_id, limit=200)
    except Exception as exc:  # Fail-open: duplicate guard must not block real alert writes.
        return {"duplicate": False, "reason": "duplicate_check_failed", "error": str(exc)}

    for alert in alerts:
        alert_ts = _as_aware_datetime(alert.get("ts"))
        if alert_ts and alert_ts < since:
            continue
        if alert.get("batch_id") != batch_id:
            continue
        if alert.get("sensor_name") != sensor_name:
            continue
        if alert.get("state") != state:
            continue
        if (alert.get("cause") or None) != (cause_id or None):
            continue
        return {
            "duplicate": True,
            "reason": "recent_unacknowledged_alert_exists",
            "existing_event_id": str(alert.get("event_id")),
            "suppression_minutes": suppression_minutes,
        }

    return {"duplicate": False, "reason": "no_recent_duplicate"}
