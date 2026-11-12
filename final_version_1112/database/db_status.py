"""
SprayLine DB — 批次站點狀態快照（batch_station_status）
對應 Schema v5.1、PostgreSQL 16

匯入方式
--------
from db_status import get_latest_station_status, upsert_batch_station_status
"""

from __future__ import annotations

from db_connection import _fetch, _fetchone


# ══════════════════════════════════════════════════════════════════════════════
# ZONE 4：批次站點詳細狀態（batch_station_status）
# ══════════════════════════════════════════════════════════════════════════════

def get_batch_station_status(conn, batch_id: str, station_id: str) -> dict | None:
    """取得指定批次 × 指定站點的診斷快照（6 狀態 + 6 解方）。

    使用方式
    --------
    status = get_batch_station_status(conn, "B_20260609_001", "Station_1")
    if status:
        print(status["filter_state"], status["filter_response_id"])
    """
    sql = """
        SELECT bss.*,
               rc_robot.description_zh  AS robot_arm_response_desc,
               rc_filter.description_zh AS filter_response_desc,
               rc_nozzle.description_zh AS nozzle_response_desc
        FROM   batch_station_status bss
        LEFT JOIN response_catalog rc_robot
               ON rc_robot.response_id = bss.robot_arm_response_id
        LEFT JOIN response_catalog rc_filter
               ON rc_filter.response_id = bss.filter_response_id
        LEFT JOIN response_catalog rc_nozzle
               ON rc_nozzle.response_id = bss.nozzle_response_id
        WHERE  bss.batch_id   = %s
          AND  bss.station_id = %s
    """
    return _fetchone(conn, sql, (batch_id, station_id))


def get_latest_station_status(conn, station_id: str) -> dict | None:
    """取得指定站點最新一筆批次狀態快照。

    使用方式
    --------
    latest = get_latest_station_status(conn, "Station_2")
    """
    sql = """
        SELECT bss.*
        FROM   batch_station_status bss
        JOIN   batch_run br ON br.batch_id = bss.batch_id
        WHERE  bss.station_id = %s
        ORDER  BY br.start_time DESC
        LIMIT  1
    """
    return _fetchone(conn, sql, (station_id,))


def upsert_batch_station_status(conn, record: dict) -> None:
    """寫入（或更新）一筆批次站點診斷快照，ON CONFLICT DO UPDATE（不自動 commit）。

    SprayLine_3 推理引擎每批次完成後呼叫，寫入 6 元件狀態 + 6 解方 FK。
    若同一 (batch_id, station_id) 已存在則覆蓋，確保可重複執行。

    使用方式
    --------
    upsert_batch_station_status(conn, {
        "batch_id":                 "B_20260610_001",
        "station_id":               "Station_1",
        "robot_arm_state":          "ok",
        "nozzle_state":             "ok",
        "filter_state":             "warning",
        "compressor_state":         "ok",
        "spray_width_state":        "ok",
        "quality_state":            "ok",
        "robot_arm_response_id":    None,
        "nozzle_response_id":       None,
        "filter_response_id":       "REPLACE_FILTER",
        "compressor_response_id":   None,
        "spray_width_response_id":  None,
        "quality_response_id":      None,
        "quality_score_pct":        92.5,
        "qc_pct":                   7.5,
        "estimated_defect_rate_pct": 7.5,
        "estimated_film_thickness_um": 15.2,
    })
    conn.commit()

    state 可選值：'ok' / 'warning' / 'fault' / None
    """
    sql = """
        INSERT INTO batch_station_status (
            batch_id, station_id,
            robot_arm_state,  nozzle_state,  filter_state,
            compressor_state, spray_width_state, quality_state,
            robot_arm_response_id,   nozzle_response_id,   filter_response_id,
            compressor_response_id,  spray_width_response_id, quality_response_id,
            quality_score_pct, qc_pct, estimated_defect_rate_pct,
            estimated_film_thickness_um, metric_updated_at
        ) VALUES (
            %(batch_id)s, %(station_id)s,
            %(robot_arm_state)s,  %(nozzle_state)s,  %(filter_state)s,
            %(compressor_state)s, %(spray_width_state)s, %(quality_state)s,
            %(robot_arm_response_id)s,  %(nozzle_response_id)s,  %(filter_response_id)s,
            %(compressor_response_id)s, %(spray_width_response_id)s, %(quality_response_id)s,
            %(quality_score_pct)s, %(qc_pct)s, %(estimated_defect_rate_pct)s,
            %(estimated_film_thickness_um)s, COALESCE(%(metric_updated_at)s, now())
        )
        ON CONFLICT (batch_id, station_id) DO UPDATE SET
            robot_arm_state          = EXCLUDED.robot_arm_state,
            nozzle_state             = EXCLUDED.nozzle_state,
            filter_state             = EXCLUDED.filter_state,
            compressor_state         = EXCLUDED.compressor_state,
            spray_width_state        = EXCLUDED.spray_width_state,
            quality_state            = EXCLUDED.quality_state,
            robot_arm_response_id    = EXCLUDED.robot_arm_response_id,
            nozzle_response_id       = EXCLUDED.nozzle_response_id,
            filter_response_id       = EXCLUDED.filter_response_id,
            compressor_response_id   = EXCLUDED.compressor_response_id,
            spray_width_response_id  = EXCLUDED.spray_width_response_id,
            quality_response_id      = EXCLUDED.quality_response_id,
            quality_score_pct        = EXCLUDED.quality_score_pct,
            qc_pct                   = EXCLUDED.qc_pct,
            estimated_defect_rate_pct = EXCLUDED.estimated_defect_rate_pct,
            estimated_film_thickness_um = EXCLUDED.estimated_film_thickness_um,
            metric_updated_at        = EXCLUDED.metric_updated_at,
            write_time               = now()
    """
    defaults = {
        "robot_arm_state": None, "nozzle_state": None,
        "filter_state": None, "compressor_state": None,
        "spray_width_state": None, "quality_state": None,
        "robot_arm_response_id": None, "nozzle_response_id": None,
        "filter_response_id": None, "compressor_response_id": None,
        "spray_width_response_id": None, "quality_response_id": None,
        "quality_score_pct": None, "qc_pct": None,
        "estimated_defect_rate_pct": None,
        "estimated_film_thickness_um": None,
        "metric_updated_at": None,
    }
    with conn.cursor() as cur:
        cur.execute(sql, {**defaults, **record})
