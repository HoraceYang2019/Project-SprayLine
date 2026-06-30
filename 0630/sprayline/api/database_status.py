from __future__ import annotations

from typing import Any
import traceback


def _error_payload(stage: str, exc: BaseException, config: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "status": "error",
        "connected": False,
        "stage": stage,
        "error_type": exc.__class__.__name__,
        "error_message": str(exc),
        "traceback_tail": traceback.format_exc(limit=2),
    }
    if config:
        payload["config"] = config
    return payload


def check_database_status() -> dict[str, Any]:
    """Best-effort DB connectivity check for the API status route."""
    try:
        from db_connection import DB_CONFIG, get_connection
    except Exception as exc:
        return _error_payload("import_db_connection", exc)

    safe_config = {
        "host": DB_CONFIG.get("host"),
        "port": DB_CONFIG.get("port"),
        "user": DB_CONFIG.get("user"),
        "dbname": DB_CONFIG.get("dbname"),
    }

    try:
        conn = get_connection()
    except Exception as exc:
        return _error_payload("connect", exc, config=safe_config)

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user, version()")
            current_database, current_user, version = cur.fetchone()
        return {
            "status": "ok",
            "connected": True,
            "config": safe_config,
            "database": current_database,
            "current_user": current_user,
            "server_version": version,
        }
    except Exception as exc:
        return _error_payload("query", exc, config=safe_config)
    finally:
        try:
            conn.close()
        except Exception:
            pass
