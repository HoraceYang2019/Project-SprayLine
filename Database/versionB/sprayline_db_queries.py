"""
SprayLine Database Query & Write Functions
對應 Schema v5.1（setup_db.sql）、PostgreSQL 16

使用方式
--------
from sprayline_db_queries import get_connection, get_latest_batches, insert_batch_run, ...

conn = get_connection()          # 預設讀 DB_* 環境變數
rows = get_latest_batches(conn)
conn.close()

# 或以 with 語法自動關閉連線
import psycopg2
with psycopg2.connect(**DB_CONFIG) as conn:
    rows = get_latest_batches(conn)

函式命名規則
-----------
get_*        → SELECT，回傳 list[dict] 或 dict | None
insert_*     → INSERT，不自動 commit，回傳 None 或新產生的 PK 字串
update_*     → UPDATE，不自動 commit，回傳 None
upsert_*     → INSERT … ON CONFLICT DO UPDATE，不自動 commit，回傳 None
link_*       → 關聯表 INSERT（M:N junction），不自動 commit，回傳 None
acknowledge_* → UPDATE acknowledged_at，不自動 commit，回傳 None

所有寫入函式均不自動 commit，由呼叫端在適當時機執行 conn.commit()。
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import psycopg2
import psycopg2.extras


# ── 連線設定 ──────────────────────────────────────────────────────────────────

DB_CONFIG: dict[str, Any] = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "dbname":   os.getenv("DB_NAME",     "sprayline"),
}


def get_connection(**overrides) -> psycopg2.extensions.connection:
    """建立資料庫連線並回傳 connection 物件。

    使用方式
    --------
    conn = get_connection()
    conn = get_connection(host="192.168.1.10", password="secret")
    """
    cfg = {**DB_CONFIG, **overrides}
    conn = psycopg2.connect(**cfg)
    conn.autocommit = False
    return conn


def _fetch(conn, sql: str, params=()) -> list[dict]:
    """內部工具：執行 SELECT 並回傳 list[dict]。"""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def _fetchone(conn, sql: str, params=()) -> dict | None:
    """內部工具：執行 SELECT 並回傳第一筆 dict 或 None。"""
    rows = _fetch(conn, sql, params)
    return rows[0] if rows else None


# ══════════════════════════════════════════════════════════════════════════════
# ZONE 2：批次生產（batch_run）
# ══════════════════════════════════════════════════════════════════════════════

def get_latest_batches(conn, limit: int = 10) -> list[dict]:
    """取得最近 N 筆批次記錄，依 start_time 倒序排列。

    使用方式
    --------
    batches = get_latest_batches(conn, limit=5)
    for b in batches:
        print(b["batch_id"], b["status"])

    回傳欄位：batch_id, start_time, ended_time, status
    """
    sql = """
        SELECT batch_id, start_time, ended_time, status
        FROM   batch_run
        ORDER  BY start_time DESC
        LIMIT  %s
    """
    return _fetch(conn, sql, (limit,))


def get_batch_by_id(conn, batch_id: str) -> dict | None:
    """依 batch_id 取得單筆批次。找不到則回傳 None。

    使用方式
    --------
    batch = get_batch_by_id(conn, "B_20260609_001")
    if batch:
        print(batch["status"])
    """
    sql = """
        SELECT batch_id, start_time, ended_time, status
        FROM   batch_run
        WHERE  batch_id = %s
    """
    return _fetchone(conn, sql, (batch_id,))


def get_running_batches(conn) -> list[dict]:
    """取得所有 status='running' 的進行中批次。

    使用方式
    --------
    running = get_running_batches(conn)
    """
    sql = """
        SELECT batch_id, start_time, status
        FROM   batch_run
        WHERE  status = 'running'
        ORDER  BY start_time DESC
    """
    return _fetch(conn, sql)


def get_batches_by_date_range(
    conn,
    start_date: datetime,
    end_date: datetime,
    status: str | None = None,
) -> list[dict]:
    """取得指定日期區間內的批次清單，可選擇性過濾 status。

    使用方式
    --------
    from datetime import datetime, timezone
    batches = get_batches_by_date_range(
        conn,
        start_date=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 6, 9, tzinfo=timezone.utc),
    )
    # 只看異常批次
    bad = get_batches_by_date_range(conn, start_date, end_date, status="bad")

    status 可選值：'running' / 'ok' / 'warning' / 'bad' / None（不過濾）
    """
    if status:
        sql = """
            SELECT batch_id, start_time, ended_time, status
            FROM   batch_run
            WHERE  start_time >= %s
              AND  start_time <  %s
              AND  status      = %s
            ORDER  BY start_time DESC
        """
        return _fetch(conn, sql, (start_date, end_date, status))
    else:
        sql = """
            SELECT batch_id, start_time, ended_time, status
            FROM   batch_run
            WHERE  start_time >= %s
              AND  start_time <  %s
            ORDER  BY start_time DESC
        """
        return _fetch(conn, sql, (start_date, end_date))


def get_latest_completed_batch(conn, station_id: str | None = None) -> dict | None:
    """取得最新一筆已完成批次（ended_time IS NOT NULL）。

    若傳入 station_id，則回傳該站點有感測資料的最新已完成批次。
    time_series_service 計算可用時率時需要此函式。

    使用方式
    --------
    batch = get_latest_completed_batch(conn)
    batch = get_latest_completed_batch(conn, station_id="Station_1")
    if batch:
        print(batch["batch_id"], batch["ended_time"])
    """
    if station_id:
        sql = """
            SELECT br.batch_id, br.start_time, br.ended_time, br.status
            FROM   batch_run br
            WHERE  br.ended_time IS NOT NULL
              AND  EXISTS (
                  SELECT 1 FROM sensor_1min s
                  WHERE  s.batch_id   = br.batch_id
                    AND  s.station_id = %s
              )
            ORDER  BY br.ended_time DESC
            LIMIT  1
        """
        return _fetchone(conn, sql, (station_id,))
    else:
        sql = """
            SELECT batch_id, start_time, ended_time, status
            FROM   batch_run
            WHERE  ended_time IS NOT NULL
            ORDER  BY ended_time DESC
            LIMIT  1
        """
        return _fetchone(conn, sql)


def insert_batch_run(
    conn,
    batch_id: str,
    start_time: datetime,
    ended_time: datetime | None = None,
    status: str = "running",
) -> None:
    """寫入一筆新批次記錄（不自動 commit）。

    使用方式
    --------
    from datetime import datetime, timezone
    insert_batch_run(conn, "B_20260610_001", datetime.now(timezone.utc))
    conn.commit()

    status 可選值：'running' / 'ok' / 'warning' / 'bad'
    """
    sql = """
        INSERT INTO batch_run (batch_id, start_time, ended_time, status)
        VALUES (%s, %s, %s, %s)
    """
    with conn.cursor() as cur:
        cur.execute(sql, (batch_id, start_time, ended_time, status))


def update_batch_status(
    conn,
    batch_id: str,
    status: str,
    ended_time: datetime | None = None,
) -> None:
    """更新批次狀態與結束時間（不自動 commit）。

    批次完成後，推理引擎應呼叫此函式將 status 從 'running' 改為
    'ok' / 'warning' / 'bad'，並寫入 ended_time。
    time_series_service 的可用時率計算依賴正確的 ended_time。

    使用方式
    --------
    from datetime import datetime, timezone
    update_batch_status(conn, "B_20260610_001", "warning",
                        ended_time=datetime.now(timezone.utc))
    conn.commit()

    status 可選值：'running' / 'ok' / 'warning' / 'bad'
    """
    sql = """
        UPDATE batch_run
        SET    status     = %s,
               ended_time = COALESCE(%s, ended_time)
        WHERE  batch_id   = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (status, ended_time, batch_id))


# ══════════════════════════════════════════════════════════════════════════════
# ZONE 3：感測資料（sensor_1min / sensor_3min）
# ══════════════════════════════════════════════════════════════════════════════

def get_latest_sensor_1min(conn, station_id: str) -> dict | None:
    """取得指定站點的最新一筆每分鐘感測資料。

    使用方式
    --------
    row = get_latest_sensor_1min(conn, "Station_1")
    print(row["filter_diff_pressure_bar"], row["servo_torque_load_pct"])

    station_id：Station_1 / Station_2 / Station_3
    """
    sql = """
        SELECT *
        FROM   sensor_1min
        WHERE  station_id = %s
        ORDER  BY ts DESC
        LIMIT  1
    """
    return _fetchone(conn, sql, (station_id,))


def get_sensor_1min_series(
    conn,
    station_id: str,
    batch_id: str | None = None,
    hours: float = 1.0,
) -> list[dict]:
    """取得指定站點最近 N 小時（或指定批次）的分鐘感測時間序列。

    使用方式
    --------
    # 最近 2 小時
    series = get_sensor_1min_series(conn, "Station_2", hours=2)

    # 指定批次
    series = get_sensor_1min_series(conn, "Station_1", batch_id="B_20260609_001")

    回傳：依 ts 升序排列的 list[dict]
    """
    if batch_id:
        sql = """
            SELECT *
            FROM   sensor_1min
            WHERE  station_id = %s
              AND  batch_id   = %s
            ORDER  BY ts ASC
        """
        return _fetch(conn, sql, (station_id, batch_id))
    else:
        sql = """
            SELECT *
            FROM   sensor_1min
            WHERE  station_id = %s
              AND  ts >= NOW() - (%s || ' hours')::INTERVAL
            ORDER  BY ts ASC
        """
        return _fetch(conn, sql, (station_id, str(hours)))


def get_pdm_trend(conn, station_id: str, hours: float = 24.0) -> list[dict]:
    """取得 PdM 核心指標趨勢（濾網壓差 + 伺服負載），用於折線圖。

    使用方式
    --------
    trend = get_pdm_trend(conn, "Station_1", hours=48)
    for r in trend:
        print(r["ts"], r["filter_diff_pressure_bar"], r["servo_torque_load_pct"])
    """
    sql = """
        SELECT ts,
               filter_diff_pressure_bar,
               servo_torque_load_pct
        FROM   sensor_1min
        WHERE  station_id = %s
          AND  ts >= NOW() - (%s || ' hours')::INTERVAL
        ORDER  BY ts ASC
    """
    return _fetch(conn, sql, (station_id, str(hours)))


def get_batch_sensor_aggregates(conn, batch_id: str, station_id: str) -> dict | None:
    """取得指定批次 × 站點的感測統計值（平均、最大、最小、標準差）。

    推理引擎判斷元件狀態（ok/warning/fault）時，需要批次內的聚合值
    而非單筆瞬間值，例如「批次平均壓差」才能判斷濾網是否堵塞。

    使用方式
    --------
    agg = get_batch_sensor_aggregates(conn, "B_20260609_001", "Station_1")
    if agg:
        print(agg["avg_filter_diff_pressure_bar"])  # 批次平均壓差
        print(agg["max_servo_torque_load_pct"])     # 批次最高伺服負載
        print(agg["avg_film_thickness_um"])         # 批次平均膜厚
        print(agg["stddev_film_thickness_um"])      # 膜厚標準差（均勻性）
        print(agg["reading_count"])                 # 本批次筆數

    回傳 None 代表該批次 × 站點無資料。
    """
    sql = """
        SELECT
            COUNT(*)                                   AS reading_count,
            AVG(filter_diff_pressure_bar)              AS avg_filter_diff_pressure_bar,
            MAX(filter_diff_pressure_bar)              AS max_filter_diff_pressure_bar,
            AVG(servo_torque_load_pct)                 AS avg_servo_torque_load_pct,
            MAX(servo_torque_load_pct)                 AS max_servo_torque_load_pct,
            AVG(film_thickness_um)                     AS avg_film_thickness_um,
            STDDEV(film_thickness_um)                  AS stddev_film_thickness_um,
            MIN(film_thickness_um)                     AS min_film_thickness_um,
            MAX(film_thickness_um)                     AS max_film_thickness_um,
            AVG(spray_width_mm)                        AS avg_spray_width_mm,
            STDDEV(spray_width_mm)                     AS stddev_spray_width_mm,
            AVG(paint_flow_ml_min)                     AS avg_paint_flow_ml_min,
            AVG(air_pressure_bar)                      AS avg_air_pressure_bar,
            MAX(vibration_g)                           AS max_vibration_g,
            MAX(path_error_mm)                         AS max_path_error_mm,
            AVG(pump_current_a)                        AS avg_pump_current_a
        FROM   sensor_1min
        WHERE  batch_id   = %s
          AND  station_id = %s
    """
    row = _fetchone(conn, sql, (batch_id, station_id))
    if row and row.get("reading_count") == 0:
        return None
    return row


def get_latest_sensor_3min(conn, station_id: str) -> dict | None:
    """取得指定站點最新一筆每 3 分鐘環境感測資料（溫度、濕度、減速機溫度）。

    使用方式
    --------
    env = get_latest_sensor_3min(conn, "Station_3")
    print(env["temperature_c"], env["humidity_rh"])
    """
    sql = """
        SELECT *
        FROM   sensor_3min
        WHERE  station_id = %s
        ORDER  BY ts DESC
        LIMIT  1
    """
    return _fetchone(conn, sql, (station_id,))


def get_sensor_3min_series(
    conn,
    station_id: str,
    ts_start: datetime | None = None,
    ts_end: datetime | None = None,
    hours: float = 24.0,
) -> list[dict]:
    """取得指定站點的 3 分鐘環境感測時間序列。

    可傳入 ts_start / ts_end 精確指定區間（對應 time_series_service 的查詢模式），
    或僅傳入 hours 取最近 N 小時。

    使用方式
    --------
    # 最近 24 小時
    series = get_sensor_3min_series(conn, "Station_2", hours=24)

    # 指定時間區間（對應 time_series_service._BuildLineRawParameters）
    series = get_sensor_3min_series(conn, "Station_1",
                                    ts_start=datetime(...), ts_end=datetime(...))

    回傳欄位：ts, station_id, gearbox_temperature_c, temperature_c, humidity_rh
    """
    if ts_start and ts_end:
        sql = """
            SELECT ts, station_id,
                   gearbox_temperature_c, temperature_c, humidity_rh
            FROM   sensor_3min
            WHERE  station_id = %s
              AND  ts BETWEEN %s AND %s
            ORDER  BY ts ASC
        """
        return _fetch(conn, sql, (station_id, ts_start, ts_end))
    else:
        sql = """
            SELECT ts, station_id,
                   gearbox_temperature_c, temperature_c, humidity_rh
            FROM   sensor_3min
            WHERE  station_id = %s
              AND  ts >= NOW() - (%s || ' hours')::INTERVAL
            ORDER  BY ts ASC
        """
        return _fetch(conn, sql, (station_id, str(hours)))


def insert_sensor_readings_batch(conn, readings: list[dict]) -> None:
    """批次寫入 sensor_1min 感測資料（不自動 commit）。

    DataPreprocess 清洗完成後呼叫此函式，一次寫入多筆含 data_quality_flag 的資料。
    使用 execute_values 批次插入，效能遠優於逐筆 execute。

    使用方式
    --------
    readings = [
        {
            "ts": datetime(..., tzinfo=timezone.utc),
            "batch_id": "B_20260610_001",
            "station_id": "Station_1",
            "film_thickness_um": 15.2,
            "paint_flow_ml_min": 108.3,
            "nozzle_roll": 0.01,
            "filter_diff_pressure_bar": 0.22,
            "filter_inflow_ml_min": 110.0,
            "filter_outflow_ml_min": 109.5,
            "pump_current_a": 2.1,
            "air_pressure_bar": 2.5,
            "spray_width_mm": 105.0,
            "servo_torque_load_pct": 42.0,
            "path_error_mm": 0.03,
            "vibration_g": 0.12,
            "tcp_x_mm": 100.0, "tcp_y_mm": 50.0, "tcp_z_mm": 200.0,
            "speed_mm_s": 300.0,
            "data_quality_flag": "正常",   # '正常' / '空值' / '突波'
        },
        ...
    ]
    insert_sensor_readings_batch(conn, readings)
    conn.commit()

    data_quality_flag 預設為 '正常'，DataPreprocess 針對補值設 '空值'、
    IQR 平滑設 '突波'。
    """
    if not readings:
        return

    cols = [
        "ts", "batch_id", "station_id",
        "film_thickness_um", "paint_flow_ml_min", "nozzle_roll",
        "filter_diff_pressure_bar", "filter_inflow_ml_min", "filter_outflow_ml_min",
        "pump_current_a", "air_pressure_bar", "spray_width_mm",
        "servo_torque_load_pct", "path_error_mm", "vibration_g",
        "tcp_x_mm", "tcp_y_mm", "tcp_z_mm", "speed_mm_s",
        "data_quality_flag",
    ]
    rows = [tuple(r.get(c) for c in cols) for r in readings]
    col_str = ", ".join(cols)
    sql = f"INSERT INTO sensor_1min ({col_str}) VALUES %s"

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows)


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
            compressor_response_id,  spray_width_response_id, quality_response_id
        ) VALUES (
            %(batch_id)s, %(station_id)s,
            %(robot_arm_state)s,  %(nozzle_state)s,  %(filter_state)s,
            %(compressor_state)s, %(spray_width_state)s, %(quality_state)s,
            %(robot_arm_response_id)s,  %(nozzle_response_id)s,  %(filter_response_id)s,
            %(compressor_response_id)s, %(spray_width_response_id)s, %(quality_response_id)s
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
            write_time               = now()
    """
    defaults = {
        "robot_arm_state": None, "nozzle_state": None,
        "filter_state": None, "compressor_state": None,
        "spray_width_state": None, "quality_state": None,
        "robot_arm_response_id": None, "nozzle_response_id": None,
        "filter_response_id": None, "compressor_response_id": None,
        "spray_width_response_id": None, "quality_response_id": None,
    }
    with conn.cursor() as cur:
        cur.execute(sql, {**defaults, **record})


# ══════════════════════════════════════════════════════════════════════════════
# ALERT & EVENT（alert_event / alert_cause_link / alert_response_link）
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


# ══════════════════════════════════════════════════════════════════════════════
# 門檻值查詢（sensor_threshold）
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
# ZONE 5：元件問題解方知識庫
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


# ══════════════════════════════════════════════════════════════════════════════
# 複合查詢（跨表）
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


# ══════════════════════════════════════════════════════════════════════════════
# 快速測試（python sprayline_db_queries.py）
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json

    print("SprayLine DB Query — 連線測試")
    print(f"目標：{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}\n")

    try:
        conn = get_connection()
    except Exception as e:
        print(f"[錯誤] 無法連線：{e}")
        raise SystemExit(1)

    tests = [
        # ── 讀取函式 ──
        ("最近 3 批次",             lambda: get_latest_batches(conn, 3)),
        ("進行中批次",               lambda: get_running_batches(conn)),
        ("最新已完成批次",           lambda: get_latest_completed_batch(conn)),
        ("Station_1 最新感測",       lambda: get_latest_sensor_1min(conn, "Station_1")),
        ("Station_1 環境感測",       lambda: get_latest_sensor_3min(conn, "Station_1")),
        ("Station_1 批次聚合統計",   lambda: get_batch_sensor_aggregates(
                                         conn, "B_20260602_001", "Station_1")),
        ("未確認告警（前5）",        lambda: get_unacknowledged_alerts(conn, limit=5)),
        ("複合條件：fault 告警",     lambda: get_alerts_by_filters(
                                         conn, state="fault", acknowledged=False, days=30)),
        ("濾網 fault 門檻值",        lambda: get_single_threshold(
                                         conn, "filter_diff_pressure_bar", "fault")),
        ("濾網堵塞解方",             lambda: get_solutions_for_issue(conn, "FILTER", "FILTER_CLOG")),
        ("元件清單",                 lambda: get_all_components(conn)),
    ]

    for label, fn in tests:
        print(f"── {label} ─────────────────────────────")
        result = fn()
        print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
        print()

    conn.close()
    print("測試完成。")
