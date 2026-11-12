"""
SprayLine DB — 複合查詢（跨資料表聚合）
對應 Schema v5.1、PostgreSQL 16

此模組提供跨多張資料表的聚合查詢，供儀表板與推理引擎一次取得完整快照。

匯入方式
--------
from db_composite import get_station_dashboard_snapshot, diagnose_component
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from db_connection import _fetch, _fetchone
from db_batch import get_batch_by_id
from db_sensor import get_latest_sensor_1min
from db_status import get_latest_station_status
from db_knowledge import get_solutions_for_issue
from db_future import get_future_prediction_summary


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


def get_batch_detail(conn, batch_id: str) -> dict:
    """Return batch, station statuses, and alerts for a batch."""
    batch = get_batch_by_id(conn, batch_id)
    stations = _fetch(
        conn,
        """
            SELECT *
            FROM   batch_station_status
            WHERE  batch_id = %s
            ORDER  BY station_id
        """,
        (batch_id,),
    )
    alerts = _fetch(
        conn,
        """
            SELECT *
            FROM   alert_event
            WHERE  batch_id = %s
            ORDER  BY ts DESC
        """,
        (batch_id,),
    )
    return {"batch": batch, "stations": stations, "alerts": alerts}


def get_manager_summary(conn, target_date: date, station_id: str | None = None) -> dict:
    """Return daily manager summary counts and station breakdown."""
    start_dt = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(days=1)

    batch_conditions = ["br.start_time >= %s", "br.start_time < %s"]
    batch_params: list = [start_dt, end_dt]
    if station_id:
        batch_conditions.append(
            "EXISTS (SELECT 1 FROM sensor_1min s WHERE s.batch_id = br.batch_id AND s.station_id = %s)"
        )
        batch_params.append(station_id)

    batch_where = " AND ".join(batch_conditions)
    batch_counts = _fetchone(
        conn,
        f"""
            SELECT
                COUNT(*) AS total_batches,
                COUNT(*) FILTER (WHERE status = 'ok') AS ok_batches,
                COUNT(*) FILTER (WHERE status = 'warning') AS warning_batches,
                COUNT(*) FILTER (WHERE status = 'bad') AS bad_batches
            FROM batch_run br
            WHERE {batch_where}
        """,
        tuple(batch_params),
    ) or {}

    alert_conditions = ["ts >= %s", "ts < %s"]
    alert_params: list = [start_dt, end_dt]
    if station_id:
        alert_conditions.append("station_id = %s")
        alert_params.append(station_id)

    alert_where = " AND ".join(alert_conditions)
    alert_counts = _fetchone(
        conn,
        f"""
            SELECT
                COUNT(*) AS total_alerts,
                COUNT(*) FILTER (WHERE acknowledged_at IS NULL) AS unacknowledged_alerts
            FROM alert_event
            WHERE {alert_where}
        """,
        tuple(alert_params),
    ) or {}

    station_breakdown = _fetch(
        conn,
        """
            SELECT
                station_id,
                COUNT(*) AS total_alerts,
                COUNT(*) FILTER (WHERE acknowledged_at IS NULL) AS unacknowledged_alerts,
                COUNT(*) FILTER (WHERE state = 'warning') AS warning_alerts,
                COUNT(*) FILTER (WHERE state = 'fault') AS fault_alerts
            FROM alert_event
            WHERE ts >= %s
              AND ts < %s
              AND (%s IS NULL OR station_id = %s)
            GROUP BY station_id
            ORDER BY station_id
        """,
        (start_dt, end_dt, station_id, station_id),
    )

    return {
        "date": target_date.isoformat(),
        "station": station_id,
        "total_batches": batch_counts.get("total_batches", 0),
        "ok_batches": batch_counts.get("ok_batches", 0),
        "warning_batches": batch_counts.get("warning_batches", 0),
        "bad_batches": batch_counts.get("bad_batches", 0),
        "total_alerts": alert_counts.get("total_alerts", 0),
        "unacknowledged_alerts": alert_counts.get("unacknowledged_alerts", 0),
        "station_breakdown": station_breakdown,
        "future_prediction_summary": get_future_prediction_summary(conn, station_id=station_id),
    }
