"""
SprayLine DB — 門檻值與元件知識庫（sensor_threshold / cause / response / component / issue / solution）
對應 Schema v5.1、PostgreSQL 16

匯入方式
--------
from db_knowledge import get_single_threshold, get_solutions_for_issue
"""

from __future__ import annotations

from db_connection import _fetch, _fetchone


# ══════════════════════════════════════════════════════════════════════════════
# ZONE 6：門檻值查詢（sensor_threshold）
# ══════════════════════════════════════════════════════════════════════════════

def get_sensor_thresholds(conn, sensor_name: str | None = None) -> list[dict]:
    """取得感測器門檻值清單（全部或指定感測器的所有類型）。

    使用方式
    --------
    all_thresholds = get_sensor_thresholds(conn)
    filter_thresh  = get_sensor_thresholds(conn, "filter_diff_pressure_bar")

    # 轉為字典方便查詢
    rows = get_sensor_thresholds(conn, "servo_torque_load_pct")
    thresh = {r["threshold_type"]: r["value"] for r in rows}
    # thresh == {"warning": 60.0, "fault": 75.0}
    """
    if sensor_name:
        sql = """
            SELECT sensor_name, threshold_type, value, updated_at, updated_by, note
            FROM   sensor_threshold
            WHERE  sensor_name = %s
            ORDER  BY threshold_type
        """
        return _fetch(conn, sql, (sensor_name,))
    else:
        sql = """
            SELECT sensor_name, threshold_type, value, updated_at, updated_by, note
            FROM   sensor_threshold
            ORDER  BY sensor_name, threshold_type
        """
        return _fetch(conn, sql)


def get_single_threshold(conn, sensor_name: str, threshold_type: str) -> float | None:
    """取得單一感測器指定類型的門檻值（純數值）。

    推理引擎狀態判斷時，只需要「某感測器的 fault 門檻」這樣的單一數值，
    不需要回傳整個字典結構。

    使用方式
    --------
    fault_val = get_single_threshold(conn, "filter_diff_pressure_bar", "fault")
    warn_val  = get_single_threshold(conn, "servo_torque_load_pct", "warning")

    if measured_value > fault_val:
        state = "fault"
    elif measured_value > warn_val:
        state = "warning"

    threshold_type：'warning' / 'fault' / 'warning_lo' / 'warning_hi' /
                    'fault_lo' / 'fault_hi'
    回傳 None 代表該組合不存在。
    """
    sql = """
        SELECT value
        FROM   sensor_threshold
        WHERE  sensor_name    = %s
          AND  threshold_type = %s
    """
    row = _fetchone(conn, sql, (sensor_name, threshold_type))
    return float(row["value"]) if row else None


# ══════════════════════════════════════════════════════════════════════════════
# ZONE 7：元件問題解方知識庫
# ══════════════════════════════════════════════════════════════════════════════

def get_solutions_for_issue(conn, component_id: str, issue_id: str) -> list[dict]:
    """查詢「某元件發生某問題」時的建議解方，依優先順序排列。

    使用方式
    --------
    solutions = get_solutions_for_issue(conn, "FILTER", "FILTER_CLOG")
    for s in solutions:
        print(s["relevance_rank"], s["solution_id"], s["description"],
              s["effectiveness_pct"])
    """
    sql = """
        SELECT m.relevance_rank,
               m.effectiveness_pct,
               s.solution_id,
               s.description,
               s.downtime_estimate_min,
               s.skill_required,
               m.note
        FROM   component_issue_solution_map m
        JOIN   solution_catalog             s ON s.solution_id = m.solution_id
        WHERE  m.component_id = %s
          AND  m.issue_id     = %s
        ORDER  BY m.relevance_rank ASC NULLS LAST
    """
    return _fetch(conn, sql, (component_id, issue_id))


def get_issues_for_component(conn, component_id: str) -> list[dict]:
    """取得某元件所有已知問題（含嚴重程度）。

    使用方式
    --------
    issues = get_issues_for_component(conn, "ROBOT_ARM")
    for i in issues:
        print(i["issue_id"], i["display_name"], i["severity"])
    """
    sql = """
        SELECT DISTINCT ic.issue_id,
               ic.display_name,
               ic.description,
               ic.severity
        FROM   component_issue_solution_map m
        JOIN   issue_catalog                ic ON ic.issue_id = m.issue_id
        WHERE  m.component_id = %s
        ORDER  BY ic.severity DESC, ic.issue_id
    """
    return _fetch(conn, sql, (component_id,))


def get_issues_by_state(conn, component_id: str, state: str) -> list[dict]:
    """Map component state to likely issues for troubleshooting services.

    The DB stores concrete issue_id values, while some services expose
    coarse states such as ok, warning, and fault. This helper provides a
    stable bridge without changing issue_catalog.
    """
    if state == "ok":
        return []

    if state == "fault":
        severities = ("high", "medium")
    elif state == "warning":
        severities = ("medium", "low")
    else:
        severities = ("high", "medium", "low")

    sql = """
        SELECT DISTINCT ic.issue_id,
               ic.display_name,
               ic.description,
               ic.severity
        FROM   component_issue_solution_map m
        JOIN   issue_catalog                ic ON ic.issue_id = m.issue_id
        WHERE  m.component_id = %s
          AND  ic.severity = ANY(%s)
        ORDER  BY
            CASE ic.severity
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                ELSE 3
            END,
            ic.issue_id
    """
    return _fetch(conn, sql, (component_id, list(severities)))


def get_cause_info(conn, cause_id: str) -> dict | None:
    """取得單筆故障原因的詳細資訊。

    使用方式
    --------
    cause = get_cause_info(conn, "FILTER_CLOG")
    print(cause["description_zh"], cause["severity"])
    """
    return _fetchone(
        conn,
        "SELECT * FROM cause_catalog WHERE cause_id = %s",
        (cause_id,),
    )


def get_response_info(conn, response_id: str) -> dict | None:
    """取得單筆應對措施的詳細資訊。

    使用方式
    --------
    resp = get_response_info(conn, "REPLACE_FILTER")
    print(resp["description_zh"], resp["downtime_estimate_min"])
    """
    return _fetchone(
        conn,
        "SELECT * FROM response_catalog WHERE response_id = %s",
        (response_id,),
    )


def get_all_components(conn) -> list[dict]:
    """取得所有元件清單。

    使用方式
    --------
    components = get_all_components(conn)
    # component_id: ROBOT_ARM / NOZZLE / FILTER / AIR_COMPRESSOR / SPRAY_WIDTH / QUALITY
    """
    return _fetch(conn, "SELECT * FROM component_catalog ORDER BY category, component_id")
