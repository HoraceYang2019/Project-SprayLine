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

    Duplicate match key:
    - station_id
    - sensor_name
    - state / severity_state
    - cause_id / cause

    batch_id is intentionally excluded because the simulated data may
    generate a different batch_id every minute.

    Only recent, unacknowledged alerts are considered duplicates.
    Warning and fault remain separate states, so an escalation from
    warning to fault can still create a new alert.
    """
    if suppression_minutes <= 0:
        return {
            "duplicate": False,
            "reason": "suppression_disabled",
        }

    station_id = row.get("station_id")
    sensor_name = detected.get("sensor_name")
    state = detected.get("state") or detected.get("severity_state")
    cause_id = detected.get("cause_id") or detected.get("cause")

    if not station_id or not sensor_name or not state:
        return {
            "duplicate": False,
            "reason": "insufficient_key",
        }

    reference_time = (
        _as_aware_datetime(row.get("ts"))
        or datetime.now(timezone.utc)
    )

    since = reference_time - timedelta(
        minutes=suppression_minutes
    )

    try:
        alerts = get_unacknowledged_alerts(
            conn,
            station_id=station_id,
            limit=200,
        )
    except Exception as exc:
        # Fail-open: duplicate checking must not block real alerts.
        return {
            "duplicate": False,
            "reason": "duplicate_check_failed",
            "error": str(exc),
        }

    for alert in alerts:
        alert_ts = _as_aware_datetime(alert.get("ts"))

        if alert_ts is None:
            continue

        # Only compare alerts from the previous suppression window.
        # Future alerts must not suppress the current sensor row.
        if alert_ts < since or alert_ts > reference_time:
            continue

        if alert.get("station_id") not in (None, station_id):
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

    return {
        "duplicate": False,
        "reason": "no_recent_duplicate",
    }