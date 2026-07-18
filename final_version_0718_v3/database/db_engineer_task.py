"""Database operations for Manager UI engineer notification tasks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from psycopg2.extras import Json

from db_connection import _fetch, _fetchone


def _uuid_param(value: str | UUID | None) -> str | None:
    """Pass UUIDs as strings so this module does not require a global psycopg2 UUID adapter."""
    return str(value) if value is not None else None


def create_engineer_task(conn, task: dict[str, Any]) -> dict[str, Any]:
    task_id = UUID(str(task.get("task_id"))) if task.get("task_id") else uuid4()
    payload = task.get("payload_json") or {}
    row = _fetchone(
        conn,
        """
        INSERT INTO engineer_task (
            task_id, source_alert_event_id, station_id, station_name,
            process_name, batch_id, batch_label, data_date, data_hour,
            level, issue, recommendation, engineer_name, engineer_email,
            delivery_status, payload_json
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, 'pending', %s
        )
        RETURNING *
        """,
        (
            _uuid_param(task_id),
            _uuid_param(task.get("source_alert_event_id")),
            task["station_id"],
            task["station_name"],
            task["process_name"],
            task.get("batch_id"),
            task.get("batch_label"),
            task.get("data_date"),
            task.get("data_hour"),
            task.get("level") or "warning",
            task["issue"],
            task["recommendation"],
            task.get("engineer_name"),
            task["engineer_email"],
            Json(payload),
        ),
    )
    conn.commit()
    return row or {}


def get_engineer_task(conn, task_id: str | UUID) -> dict[str, Any] | None:
    return _fetchone(conn, "SELECT * FROM engineer_task WHERE task_id = %s", (_uuid_param(task_id),))


def get_engineer_tasks(
    conn,
    delivery_status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    if delivery_status:
        return _fetch(
            conn,
            """
            SELECT * FROM engineer_task
            WHERE delivery_status = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (delivery_status, limit, offset),
        )
    return _fetch(
        conn,
        """
        SELECT * FROM engineer_task
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """,
        (limit, offset),
    )


def mark_engineer_task_sent(
    conn,
    task_id: str | UUID,
    apps_script_response: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    row = _fetchone(
        conn,
        """
        UPDATE engineer_task
        SET delivery_status = 'sent', delivery_error = NULL,
            sent_at = NOW(), apps_script_response_json = %s,
            updated_at = NOW()
        WHERE task_id = %s
        RETURNING *
        """,
        (Json(apps_script_response or {}), _uuid_param(task_id)),
    )
    conn.commit()
    return row


def mark_engineer_task_failed(
    conn,
    task_id: str | UUID,
    error: str,
    apps_script_response: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    row = _fetchone(
        conn,
        """
        UPDATE engineer_task
        SET delivery_status = 'failed', delivery_error = %s,
            apps_script_response_json = %s, updated_at = NOW()
        WHERE task_id = %s
        RETURNING *
        """,
        (error, Json(apps_script_response or {}), _uuid_param(task_id)),
    )
    conn.commit()
    return row


def acknowledge_engineer_task(
    conn,
    task_id: str | UUID,
    *,
    acknowledged_at: datetime | None = None,
    acknowledged_by: str | None = None,
    acknowledged_email: str | None = None,
    ack_source: str = "apps_script",
    ack_note: str | None = None,
    apps_script_response: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    ack_time = acknowledged_at or datetime.now(timezone.utc)
    row = _fetchone(
        conn,
        """
        UPDATE engineer_task
        SET delivery_status = 'acknowledged', acknowledged_at = %s,
            acknowledged_by = %s, acknowledged_email = %s,
            ack_source = %s, ack_note = %s,
            apps_script_response_json = COALESCE(%s, apps_script_response_json),
            updated_at = NOW()
        WHERE task_id = %s
        RETURNING *
        """,
        (
            ack_time,
            acknowledged_by,
            acknowledged_email,
            ack_source,
            ack_note,
            Json(apps_script_response) if apps_script_response is not None else None,
            _uuid_param(task_id),
        ),
    )
    conn.commit()
    return row
