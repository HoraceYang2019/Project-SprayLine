from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any

EXPECTED_TABLES = (
    "batch_run",
    "sensor_1min",
    "sensor_3min",
    "batch_station_status",
    "alert_event",
    "future_prediction_result",
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _public_config() -> dict[str, Any]:
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "user": os.getenv("DB_USER", "postgres"),
        "dbname": os.getenv("DB_NAME", "sprayline"),
        "password_configured": bool(os.getenv("DB_PASSWORD", "")),
        "connect_timeout_sec": int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
    }


def check_database_status() -> dict[str, Any]:
    """Read-only PostgreSQL / Database-versionB status endpoint for the V16 Engineer UI.

    This function never creates, updates, deletes, or migrates any table.
    It only opens a connection and checks whether expected tables exist and have rows.
    """
    config = _public_config()
    status: dict[str, Any] = {
        "connected": False,
        "mode": "integrated",
        "read_only_check": True,
        "config": config,
        "database_versionb_path": os.getenv("SPRAYLINE_DB_FUNCTION_PATH") or os.getenv("VERSIONB_PATH") or "/app/database",
        "tables": {},
    }

    conn = None
    try:
        from db_connection import get_connection

        conn = get_connection(connect_timeout=config["connect_timeout_sec"])
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT current_database(), current_user,
                       COALESCE(inet_server_addr()::text, %s),
                       inet_server_port(), version()
                """,
                (config["host"],),
            )
            dbname, dbuser, server_addr, server_port, version = cur.fetchone()

            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = ANY(%s)
                """,
                (list(EXPECTED_TABLES),),
            )
            existing = {row[0] for row in cur.fetchall()}

            table_status: dict[str, Any] = {}
            for table in EXPECTED_TABLES:
                item: dict[str, Any] = {"exists": table in existing}
                if table in existing:
                    cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                    row_count = int(cur.fetchone()[0])
                    item["row_count"] = row_count
                    item["has_rows"] = row_count > 0
                    if table in {"sensor_1min", "sensor_3min"}:
                        cur.execute(f'SELECT MAX(ts) FROM "{table}"')
                        item["latest_timestamp"] = _json_safe(cur.fetchone()[0])
                table_status[table] = item

        status.update({
            "connected": True,
            "database": {
                "name": dbname,
                "user": dbuser,
                "server_address": server_addr,
                "server_port": server_port,
                "version": version,
            },
            "tables": table_status,
            "required_tables_found": all(table_status[t]["exists"] for t in ("sensor_1min", "sensor_3min")),
            "required_sensor_data_found": all(table_status[t].get("has_rows") for t in ("sensor_1min", "sensor_3min")),
        })
        return _json_safe(status)
    except Exception as exc:
        status.update({
            "stage": "open_or_query_database",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        })
        return _json_safe(status)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
