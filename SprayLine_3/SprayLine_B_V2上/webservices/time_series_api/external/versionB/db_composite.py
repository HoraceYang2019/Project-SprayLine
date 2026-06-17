"""
SprayLine DB — 複合查詢（跨資料表聚合）
對應 Schema v5.1、PostgreSQL 16

此模組提供跨多張資料表的聚合查詢，供儀表板與推理引擎一次取得完整快照。

匯入方式
--------
from db_composite import get_station_dashboard_snapshot, diagnose_component
"""

from __future__ import annotations

from db_connection import _fetchone
from db_sensor import get_latest_sensor_1min
from db_status import get_latest_station_status
from db_knowledge import get_solutions_for_issue


# ══════════════════════════════════════════════════════════════════════════════
# ZONE 8：複合查詢（跨表）
# ══════════════════════════════════════════════════════════════════════════════

def get_station_dashboard_snapshot(conn, station_id: str) -> dict:
    """一次取得指定站點的儀表板快照：最新感測值 + 最新狀態 + 未確認告警數。

    使用方式
    --------
    snap = get_station_dashboard_snapshot(conn, "Station_1")
    print(snap["latest_sensor"])
    print(snap["latest_status"])
    print(snap["unacked_alert_count"])
    """
    latest_sensor = get_latest_sensor_1min(conn, station_id)
    latest_status = get_latest_station_status(conn, station_id)

    count_sql = """
        SELECT COUNT(*) AS cnt
        FROM   alert_event
        WHERE  station_id       = %s
          AND  acknowledged_at IS NULL
    """
    row = _fetchone(conn, count_sql, (station_id,))
    unacked_count = row["cnt"] if row else 0

    return {
        "station_id":          station_id,
        "latest_sensor":       latest_sensor,
        "latest_status":       latest_status,
        "unacked_alert_count": unacked_count,
    }


def diagnose_component(conn, component_id: str, issue_id: str) -> dict:
    """診斷指定元件問題：回傳問題詳情 + 排序解方清單。

    使用方式
    --------
    result = diagnose_component(conn, "FILTER", "FILTER_CLOG")
    print(result["issue"]["display_name"])
    for s in result["solutions"]:
        print(s["relevance_rank"], s["solution_id"], s["effectiveness_pct"])
    """
    issue = _fetchone(
        conn,
        "SELECT * FROM issue_catalog WHERE issue_id = %s",
        (issue_id,),
    )
    solutions = get_solutions_for_issue(conn, component_id, issue_id)
    return {"component_id": component_id, "issue": issue, "solutions": solutions}
