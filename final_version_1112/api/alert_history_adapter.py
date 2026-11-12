"""API adapter：開啟唯讀資料庫連線並呼叫 AlertHistoryService。

回傳 (HTTP 狀態碼, JSON 內容)：
- 200：查詢成功
- 422：查詢參數不正確
- 503：資料庫模組或連線不可用
- 500：查詢時發生未預期錯誤
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Tuple

from alert_history_service.alert_history_service import (
    AlertQuery,
    AlertQueryError,
    list_alerts,
    list_episodes,
    summarize_alerts,
)
from versionb_alert_adapter import _db_unavailable_response, _json_safe, _open_connection

logger = logging.getLogger(__name__)

SERVICE_NAME = "AlertHistoryService"


def _envelope(output_type: str, **body: Any) -> Dict[str, Any]:
    return {"schema_version": "v1.0", "service_name": SERVICE_NAME, "output_type": output_type, **body}


def _run(output_type: str, request: Dict[str, Any], call: Callable[[Any], Dict[str, Any]]) -> Tuple[int, Dict[str, Any]]:
    conn, modules, loaded = _open_connection()
    if conn is None or modules is None:
        body = _db_unavailable_response(output_type)
        body.update(service_name=SERVICE_NAME, request=request)
        body["versionb_status"] = {**body["versionb_status"], "db_module_error": loaded.get("error")}
        return 503, _json_safe(body)
    try:
        conn.set_session(readonly=True)
        result = call(conn)
        return 200, _json_safe(_envelope(output_type, db_available=True, read_only=True, request=request, **result))
    except AlertQueryError as exc:
        return 422, _envelope(output_type, db_available=True, error="invalid_query", message=str(exc), request=request)
    except Exception as exc:  # 資料庫或其他未預期錯誤
        logger.exception("alert history query failed")
        return 500, _envelope(output_type, db_available=True, error="query_failed",
                              message=f"{type(exc).__name__}: {exc}", request=request)
    finally:
        try:
            conn.rollback()
        finally:
            conn.close()


def _query(filters: Dict[str, Any]) -> AlertQuery:
    return AlertQuery(**filters)


def get_alert_history(filters: Dict[str, Any], *, limit: int, offset: int) -> Tuple[int, Dict[str, Any]]:
    request = {**filters, "limit": limit, "offset": offset}
    return _run("alert_history", request, lambda conn: list_alerts(conn, _query(filters), limit=limit, offset=offset))


def get_alert_summary(filters: Dict[str, Any], *, group_by: str) -> Tuple[int, Dict[str, Any]]:
    request = {**filters, "group_by": group_by}
    return _run("alert_summary", request, lambda conn: summarize_alerts(conn, _query(filters), group_by=group_by))


def get_alert_episodes(filters: Dict[str, Any], *, gap_minutes: int, limit: int) -> Tuple[int, Dict[str, Any]]:
    request = {**filters, "gap_minutes": gap_minutes, "limit": limit}
    return _run("alert_episodes", request,
                lambda conn: list_episodes(conn, _query(filters), gap_minutes=gap_minutes, limit=limit))
