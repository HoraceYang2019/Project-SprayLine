"""
SprayLine DB — 告警事件（alert_event / alert_cause_link / alert_response_link）
對應 Schema v5.1、PostgreSQL 16

匯入方式
--------
from db_alert import get_unacknowledged_alerts, insert_alert_event, get_alert_ui_card
"""

from __future__ import annotations

from datetime import datetime, timezone

from db_connection import _fetch, _fetchone


# 技能等級排序（數值越小代表技能需求越低）
_SKILL_RANK: dict[str, int] = {
    "operator":   1,
    "technician": 2,
    "engineer":   3,
}


# ══════════════════════════════════════════════════════════════════════════════
# ZONE 5：告警查詢
# ══════════════════════════════════════════════════════════════════════════════

def get_unacknowledged_alerts(
    conn,
    station_id: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """取得未確認（acknowledged_at IS NULL）的告警，依發生時間倒序。

    使用方式
    --------
    alerts = get_unacknowledged_alerts(conn)                   # 全站
    alerts = get_unacknowledged_alerts(conn, "Station_1")      # 指定站點
    for a in alerts:
        print(a["station_id"], a["sensor_name"], a["state"])
    """
    if station_id:
        sql = """
            SELECT event_id, batch_id, station_id,
                   sensor_name, measured_value, state,
                   cause, ts, message
            FROM   alert_event
            WHERE  acknowledged_at IS NULL
              AND  station_id = %s
            ORDER  BY ts DESC
            LIMIT  %s
        """
        return _fetch(conn, sql, (station_id, limit))
    else:
        sql = """
            SELECT event_id, batch_id, station_id,
                   sensor_name, measured_value, state,
                   cause, ts, message
            FROM   alert_event
            WHERE  acknowledged_at IS NULL
            ORDER  BY ts DESC
            LIMIT  %s
        """
        return _fetch(conn, sql, (limit,))


def get_alert_history(
    conn,
    station_id: str | None = None,
    days: int = 7,
    limit: int = 200,
) -> list[dict]:
    """取得近 N 天的告警歷史（含已確認）。

    使用方式
    --------
    history = get_alert_history(conn, days=3)
    history = get_alert_history(conn, station_id="Station_3", days=1)
    """
    if station_id:
        sql = """
            SELECT *
            FROM   alert_event
            WHERE  station_id = %s
              AND  ts >= NOW() - (%s || ' days')::INTERVAL
            ORDER  BY ts DESC
            LIMIT  %s
        """
        return _fetch(conn, sql, (station_id, str(days), limit))
    else:
        sql = """
            SELECT *
            FROM   alert_event
            WHERE  ts >= NOW() - (%s || ' days')::INTERVAL
            ORDER  BY ts DESC
            LIMIT  %s
        """
        return _fetch(conn, sql, (str(days), limit))


def get_alerts_by_filters(
    conn,
    station_id: str | None = None,
    state: str | None = None,
    acknowledged: bool | None = None,
    days: int = 7,
    limit: int = 200,
) -> list[dict]:
    """以複合條件查詢告警（站點 + 狀態 + 是否已確認）。

    Dashboard 的告警列表需要同時過濾多個條件，例如
    「Station_1 最近 3 天未確認的 fault 告警」。

    使用方式
    --------
    # Station_1 的所有 fault 告警
    alerts = get_alerts_by_filters(conn, station_id="Station_1", state="fault")

    # 全站未確認的 warning
    alerts = get_alerts_by_filters(conn, state="warning", acknowledged=False)

    # 已確認的所有告警（近 30 天）
    alerts = get_alerts_by_filters(conn, acknowledged=True, days=30)

    state        : 'warning' / 'fault' / None（不過濾）
    acknowledged : True（已確認）/ False（未確認）/ None（不過濾）
    """
    conditions = ["ts >= NOW() - (%s || ' days')::INTERVAL"]
    params: list = [str(days)]

    if station_id:
        conditions.append("station_id = %s")
        params.append(station_id)
    if state:
        conditions.append("state = %s")
        params.append(state)
    if acknowledged is True:
        conditions.append("acknowledged_at IS NOT NULL")
    elif acknowledged is False:
        conditions.append("acknowledged_at IS NULL")

    where = " AND ".join(conditions)
    sql = f"""
        SELECT *
        FROM   alert_event
        WHERE  {where}
        ORDER  BY ts DESC
        LIMIT  %s
    """
    params.append(limit)
    return _fetch(conn, sql, tuple(params))


def get_alert_detail(conn, event_id: str) -> dict | None:
    """取得單筆告警 + 關聯原因清單 + 關聯應對措施清單。

    使用方式
    --------
    detail = get_alert_detail(conn, "some-uuid")
    if detail:
        print(detail["causes"])    # list[dict]
        print(detail["responses"]) # list[dict]
    """
    alert = _fetchone(
        conn,
        "SELECT * FROM alert_event WHERE event_id = %s",
        (event_id,),
    )
    if alert is None:
        return None

    causes    = get_alert_causes(conn, event_id)
    responses = get_alert_responses(conn, event_id)
    return {**alert, "causes": causes, "responses": responses}


def get_alert_causes(conn, event_id: str) -> list[dict]:
    """取得單筆告警的所有關聯原因（含 cause_catalog 詳情）。

    使用方式
    --------
    causes = get_alert_causes(conn, "some-uuid")
    for c in causes:
        print(c["cause_id"], c["is_primary"], c["severity"])
    """
    sql = """
        SELECT acl.cause_id, acl.is_primary,
               cc.description_zh, cc.category, cc.severity
        FROM   alert_cause_link acl
        JOIN   cause_catalog    cc ON cc.cause_id = acl.cause_id
        WHERE  acl.alert_id = %s
        ORDER  BY acl.is_primary DESC
    """
    return _fetch(conn, sql, (event_id,))


def get_alert_responses(conn, event_id: str) -> list[dict]:
    """取得單筆告警的所有關聯應對措施（含 response_catalog 詳情）。

    使用方式
    --------
    responses = get_alert_responses(conn, "some-uuid")
    for r in responses:
        print(r["response_id"], r["executed_at"], r["operator_id"])
    """
    sql = """
        SELECT arl.response_id, arl.executed_at, arl.operator_id,
               rc.description_zh, rc.downtime_estimate_min, rc.skill_required
        FROM   alert_response_link arl
        JOIN   response_catalog    rc ON rc.response_id = arl.response_id
        WHERE  arl.alert_id = %s
        ORDER  BY arl.executed_at ASC NULLS LAST
    """
    return _fetch(conn, sql, (event_id,))


def get_responses_for_cause(conn, cause_id: str) -> list[dict]:
    """給定 cause_id，查詢所有曾與此原因配對的應對措施（含停機時間與技能需求）。

    透過歷史告警的 M:N 關聯路徑查詢：
    cause_catalog → alert_cause_link → alert_event → alert_response_link → response_catalog

    回傳依 occurrence_count 倒序排列（最常被使用的解方優先），
    相同使用頻率時再依 downtime_estimate_min 升序排列。

    使用方式
    --------
    responses = get_responses_for_cause(conn, "FILTER_CLOG")
    for r in responses:
        print(r["response_id"], r["description_zh"])
        print(f"  停機估計：{r['downtime_estimate_min']} 分鐘")
        print(f"  所需技能：{r['skill_required']}")
        print(f"  歷史使用次數：{r['occurrence_count']}")

    回傳欄位：
        response_id, description_zh, downtime_estimate_min,
        skill_required, occurrence_count
    """
    mapped_sql = """
        SELECT
            rc.response_id,
            rc.description_zh,
            rc.downtime_estimate_min,
            rc.skill_required,
            crm.priority,
            crm.note,
            NULL::bigint AS occurrence_count
        FROM   cause_response_map crm
        JOIN   response_catalog   rc ON rc.response_id = crm.response_id
        WHERE  crm.cause_id = %s
        ORDER  BY crm.priority ASC,
                  rc.downtime_estimate_min ASC NULLS LAST
    """
    mapped = _fetch(conn, mapped_sql, (cause_id,))
    if mapped:
        return mapped

    sql = """
        SELECT
            rc.response_id,
            rc.description_zh,
            rc.downtime_estimate_min,
            rc.skill_required,
            NULL::int AS priority,
            NULL::text AS note,
            COUNT(DISTINCT ae.event_id) AS occurrence_count
        FROM   response_catalog    rc
        JOIN   alert_response_link arl ON rc.response_id  = arl.response_id
        JOIN   alert_event         ae  ON arl.alert_id    = ae.event_id
        JOIN   alert_cause_link    acl ON ae.event_id     = acl.alert_id
        WHERE  acl.cause_id = %s
        GROUP  BY rc.response_id, rc.description_zh,
                  rc.downtime_estimate_min, rc.skill_required
        ORDER  BY occurrence_count DESC,
                  rc.downtime_estimate_min ASC NULLS LAST
    """
    return _fetch(conn, sql, (cause_id,))


def get_alert_ui_card(conn, event_id: str) -> dict | None:
    """一次回傳 UI 告警卡片所需的全部欄位。

    內部呼叫 get_alert_detail() 並在 Python 層加工 UI 友善的派生欄位，
    不重複撰寫 SQL。UI 層可直接消費此結構，無需多次查詢。

    使用方式
    --------
    card = get_alert_ui_card(conn, "some-uuid")
    if card:
        print(card["primary_cause_zh"])     # 主要故障原因說明
        print(card["max_downtime_min"])      # 最壞情況停機時間
        print(card["min_skill_required"])    # 最低所需技能等級
        print(card["top_response_zh"])       # 最常用解方說明
        print(card["acknowledged"])          # 是否已確認（bool）

    回傳 None 代表 event_id 不存在。

    回傳結構
    --------
    {
        # 基本欄位（來自 alert_event）
        "event_id":         str,
        "station_id":       str,
        "sensor_name":      str,
        "state":            str,           # "warning" | "fault"
        "ts":               datetime,
        "message":          str | None,
        "acknowledged":     bool,
        "acknowledged_at":  datetime | None,

        # 原因清單（來自 alert_cause_link + cause_catalog）
        "causes": [
            {"cause_id": str, "description_zh": str,
             "severity": str, "is_primary": bool}
        ],

        # 解方清單（來自 alert_response_link + response_catalog）
        "responses": [
            {"response_id": str, "description_zh": str,
             "downtime_estimate_min": int | None,
             "skill_required": str | None}
        ],

        # UI 聚合欄位（Python 層計算）
        "primary_cause_zh":   str | None,  # is_primary=True 原因說明
        "max_downtime_min":   int | None,  # 所有解方中最大停機時間
        "min_skill_required": str | None,  # 最低技能需求
        "top_response_zh":    str | None,  # responses[0] 的說明
    }
    """
    detail = get_alert_detail(conn, event_id)
    if detail is None:
        return None

    causes    = detail.get("causes", [])
    responses = detail.get("responses", [])

    # 主要原因說明
    primary_cause_zh = next(
        (c["description_zh"] for c in causes if c.get("is_primary")),
        causes[0]["description_zh"] if causes else None,
    )

    # 最大停機時間（最壞情況）
    downtime_values = [
        r["downtime_estimate_min"]
        for r in responses
        if r.get("downtime_estimate_min") is not None
    ]
    max_downtime_min = max(downtime_values) if downtime_values else None

    # 最低技能需求（rank 最小的那個）
    skill_values = [
        r["skill_required"]
        for r in responses
        if r.get("skill_required") in _SKILL_RANK
    ]
    min_skill_required = (
        min(skill_values, key=lambda s: _SKILL_RANK[s])
        if skill_values else None
    )

    # 第一個解方說明（responses 依 executed_at 排序，已是最相關的）
    top_response_zh = responses[0]["description_zh"] if responses else None

    return {
        "event_id":           str(detail["event_id"]),
        "station_id":         detail.get("station_id"),
        "sensor_name":        detail.get("sensor_name"),
        "state":              detail.get("state"),
        "ts":                 detail.get("ts"),
        "message":            detail.get("message"),
        "acknowledged":       detail.get("acknowledged_at") is not None,
        "acknowledged_at":    detail.get("acknowledged_at"),
        "causes":             causes,
        "responses":          responses,
        "primary_cause_zh":   primary_cause_zh,
        "max_downtime_min":   max_downtime_min,
        "min_skill_required": min_skill_required,
        "top_response_zh":    top_response_zh,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ZONE 5：告警寫入
# ══════════════════════════════════════════════════════════════════════════════

def insert_alert_event(
    conn,
    batch_id: str,
    station_id: str,
    sensor_name: str,
    measured_value: float,
    state: str,
    cause: str | None = None,
    message: str | None = None,
    ts: datetime | None = None,
) -> str:
    """寫入一筆告警事件，回傳資料庫產生的 event_id（不自動 commit）。

    SprayLine_3 推理引擎偵測到感測值超過門檻時呼叫此函式。
    回傳的 event_id 供後續呼叫 link_alert_cause / link_alert_response 使用。

    使用方式
    --------
    event_id = insert_alert_event(
        conn,
        batch_id      = "B_20260610_001",
        station_id    = "Station_1",
        sensor_name   = "filter_diff_pressure_bar",
        measured_value= 0.72,
        state         = "fault",
        cause         = "FILTER_CLOG",
        message       = "濾網壓差超過 fault 門檻（0.70 bar）",
    )
    link_alert_cause(conn, event_id, "FILTER_CLOG", is_primary=True)
    link_alert_response(conn, event_id, "REPLACE_FILTER")
    conn.commit()

    state 可選值：'warning' / 'fault'
    cause 對應 cause_catalog.cause_id，可為 None
    """
    sql = """
        INSERT INTO alert_event
            (batch_id, station_id, sensor_name, measured_value,
             state, cause, message, ts)
        VALUES (%s, %s, %s, %s, %s, %s, %s, COALESCE(%s, now()))
        RETURNING event_id
    """
    with conn.cursor() as cur:
        cur.execute(sql, (
            batch_id, station_id, sensor_name, measured_value,
            state, cause, message, ts,
        ))
        row = cur.fetchone()
    return str(row[0])


def link_alert_cause(
    conn,
    event_id: str,
    cause_id: str,
    is_primary: bool = False,
) -> None:
    """將告警與原因關聯（alert_cause_link，M:N，不自動 commit）。

    使用方式
    --------
    link_alert_cause(conn, event_id, "FILTER_CLOG", is_primary=True)
    link_alert_cause(conn, event_id, "PUMP_DEGRADATION")
    conn.commit()
    """
    sql = """
        INSERT INTO alert_cause_link (alert_id, cause_id, is_primary)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
    """
    with conn.cursor() as cur:
        cur.execute(sql, (event_id, cause_id, is_primary))


def link_alert_response(
    conn,
    event_id: str,
    response_id: str,
    executed_at: datetime | None = None,
    operator_id: str | None = None,
) -> None:
    """將告警與應對措施關聯（alert_response_link，M:N，不自動 commit）。

    executed_at / operator_id 可在措施實際執行後再補填。

    使用方式
    --------
    # 建立關聯（尚未執行）
    link_alert_response(conn, event_id, "REPLACE_FILTER")

    # 記錄執行結果
    link_alert_response(conn, event_id, "REPLACE_FILTER",
                        executed_at=datetime.now(timezone.utc),
                        operator_id="OP-001")
    conn.commit()
    """
    sql = """
        INSERT INTO alert_response_link (alert_id, response_id, executed_at, operator_id)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (alert_id, response_id) DO UPDATE SET
            executed_at = COALESCE(EXCLUDED.executed_at, alert_response_link.executed_at),
            operator_id = COALESCE(EXCLUDED.operator_id, alert_response_link.operator_id)
    """
    with conn.cursor() as cur:
        cur.execute(sql, (event_id, response_id, executed_at, operator_id))


def acknowledge_alert(conn, event_id: str, acknowledged_at: datetime | None = None) -> None:
    """將單筆告警標記為已確認（不自動 commit）。

    使用方式
    --------
    acknowledge_alert(conn, "some-uuid")
    conn.commit()
    """
    ts = acknowledged_at or datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE alert_event SET acknowledged_at = %s WHERE event_id = %s",
            (ts, event_id),
        )


def acknowledge_alerts_batch(
    conn,
    event_ids: list[str],
    acknowledged_at: datetime | None = None,
) -> int:
    """批量確認多筆告警，回傳實際更新筆數（不自動 commit）。

    Dashboard 多選告警後批量確認時使用。

    使用方式
    --------
    updated = acknowledge_alerts_batch(conn, ["uuid-1", "uuid-2", "uuid-3"])
    conn.commit()
    print(f"已確認 {updated} 筆告警")
    """
    if not event_ids:
        return 0
    ts = acknowledged_at or datetime.now(timezone.utc)
    sql = """
        UPDATE alert_event
        SET    acknowledged_at = %s
        WHERE  event_id = ANY(%s)
          AND  acknowledged_at IS NULL
    """
    with conn.cursor() as cur:
        cur.execute(sql, (ts, event_ids))
        return cur.rowcount
