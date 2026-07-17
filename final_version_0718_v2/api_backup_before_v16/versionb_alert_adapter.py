from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from versionb_loader import load_db_config_file, load_versionb_modules, get_versionb_status


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    return value


def _db_unavailable_response(action: str) -> Dict[str, Any]:
    status = get_versionb_status()
    return {
        "schema_version": "v1.0",
        "service_name": "TimeSeriesService",
        "output_type": action,
        "db_available": False,
        "versionb_status": status,
        "message": "versionB DB is not connected yet. API contract is ready; install psycopg2 and configure PostgreSQL to enable live DB queries.",
    }


def _open_connection() -> tuple[Optional[Any], Optional[Dict[str, Any]], Dict[str, Any]]:
    loaded = load_versionb_modules()
    if not loaded.get("available"):
        return None, None, loaded

    db_connection = loaded["modules"]["db_connection"]
    overrides = load_db_config_file()
    try:
        conn = db_connection.get_connection(**overrides)
        return conn, loaded["modules"], loaded
    except Exception as exc:
        loaded = {**loaded, "available": False, "error": repr(exc)}
        return None, None, loaded


def get_alerts(
    station_id: str | None = None,
    state: str | None = None,
    acknowledged: bool | None = None,
    days: int = 7,
    limit: int = 50,
) -> Dict[str, Any]:
    conn, modules, loaded = _open_connection()
    if conn is None or modules is None:
        response = _db_unavailable_response("versionb_alert_list")
        response.update({
            "query": {
                "station_id": station_id,
                "state": state,
                "acknowledged": acknowledged,
                "days": days,
                "limit": limit,
            },
            "alerts": [],
            "total": 0,
        })
        response["versionb_status"] = {
            **response["versionb_status"],
            "db_module_error": loaded.get("error"),
        }
        return response

    try:
        rows = modules["db_alert"].get_alerts_by_filters(
            conn,
            station_id=station_id,
            state=state,
            acknowledged=acknowledged,
            days=days,
            limit=limit,
        )
        return {
            "schema_version": "v1.0",
            "service_name": "TimeSeriesService",
            "output_type": "versionb_alert_list",
            "db_available": True,
            "versionb_path": loaded.get("path"),
            "alerts": _json_safe(rows),
            "total": len(rows),
        }
    finally:
        conn.close()


def get_alert_card(event_id: str) -> Dict[str, Any]:
    conn, modules, loaded = _open_connection()
    if conn is None or modules is None:
        response = _db_unavailable_response("versionb_alert_card")
        response.update({"event_id": event_id, "alert": None})
        response["versionb_status"] = {
            **response["versionb_status"],
            "db_module_error": loaded.get("error"),
        }
        return response

    try:
        card = modules["db_alert"].get_alert_ui_card(conn, event_id)
        if card is None:
            return {
                "schema_version": "v1.0",
                "service_name": "TimeSeriesService",
                "output_type": "versionb_alert_card",
                "db_available": True,
                "event_id": event_id,
                "alert": None,
                "message": "alert not found",
            }
        return _json_safe({
            "schema_version": "v1.0",
            "service_name": "TimeSeriesService",
            "output_type": "versionb_alert_card",
            "db_available": True,
            "alert": card,
        })
    finally:
        conn.close()


def get_responses_for_cause(cause_id: str) -> Dict[str, Any]:
    conn, modules, loaded = _open_connection()
    if conn is None or modules is None:
        response = _db_unavailable_response("versionb_cause_responses")
        response.update({"cause_id": cause_id, "responses": []})
        response["versionb_status"] = {
            **response["versionb_status"],
            "db_module_error": loaded.get("error"),
        }
        return response

    try:
        rows = modules["db_alert"].get_responses_for_cause(conn, cause_id)
        return _json_safe({
            "schema_version": "v1.0",
            "service_name": "TimeSeriesService",
            "output_type": "versionb_cause_responses",
            "db_available": True,
            "cause_id": cause_id,
            "responses": rows,
            "total": len(rows),
        })
    finally:
        conn.close()


def get_unacknowledged_alerts(station_id: str, limit: int = 50) -> Dict[str, Any]:
    conn, modules, loaded = _open_connection()
    if conn is None or modules is None:
        response = _db_unavailable_response("versionb_unacknowledged_alerts")
        response.update({"station_id": station_id, "alerts": [], "count": 0})
        response["versionb_status"] = {
            **response["versionb_status"],
            "db_module_error": loaded.get("error"),
        }
        return response

    try:
        rows = modules["db_alert"].get_unacknowledged_alerts(conn, station_id=station_id, limit=limit)
        return _json_safe({
            "schema_version": "v1.0",
            "service_name": "TimeSeriesService",
            "output_type": "versionb_unacknowledged_alerts",
            "db_available": True,
            "station_id": station_id,
            "alerts": rows,
            "count": len(rows),
        })
    finally:
        conn.close()


def acknowledge_alert(event_id: str, acknowledged_at: str | None = None) -> Dict[str, Any]:
    conn, modules, loaded = _open_connection()
    if conn is None or modules is None:
        response = _db_unavailable_response("versionb_alert_acknowledge")
        response.update({
            "event_id": event_id,
            "acknowledged_at": acknowledged_at,
            "status": "db_not_connected",
        })
        response["versionb_status"] = {
            **response["versionb_status"],
            "db_module_error": loaded.get("error"),
        }
        return response

    try:
        ack_dt = None
        if acknowledged_at:
            ack_dt = datetime.fromisoformat(acknowledged_at.replace("Z", "+00:00"))
        modules["db_alert"].acknowledge_alert(conn, event_id, ack_dt)
        conn.commit()
        return _json_safe({
            "schema_version": "v1.0",
            "service_name": "TimeSeriesService",
            "output_type": "versionb_alert_acknowledge",
            "db_available": True,
            "event_id": event_id,
            "acknowledged_at": ack_dt or datetime.now(),
            "status": "ok",
        })
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
