"""
SprayLine DB — 感測資料（sensor_1min / sensor_3min）
對應 Schema v5.1、PostgreSQL 16

匯入方式
--------
from db_sensor import get_latest_sensor_1min, insert_sensor_readings_batch
"""

from __future__ import annotations

from datetime import datetime, timezone

import psycopg2.extras

from db_connection import _fetch, _fetchone


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
    ts_start: datetime | None = None,
    ts_end: datetime | None = None,
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
    elif ts_start and ts_end:
        sql = """
            SELECT *
            FROM   sensor_1min
            WHERE  station_id = %s
              AND  ts BETWEEN %s AND %s
            ORDER  BY ts ASC
        """
        return _fetch(conn, sql, (station_id, ts_start, ts_end))
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
            SELECT *
            FROM   sensor_3min
            WHERE  station_id = %s
              AND  ts BETWEEN %s AND %s
            ORDER  BY ts ASC
        """
        return _fetch(conn, sql, (station_id, ts_start, ts_end))
    else:
        sql = """
            SELECT *
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
    rows = [
        tuple(r.get(c, "normal") if c == "data_quality_flag" else r.get(c) for c in cols)
        for r in readings
    ]
    col_str = ", ".join(cols)
    sql = f"INSERT INTO sensor_1min ({col_str}) VALUES %s"

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows)


def insert_sensor_3min_readings_batch(conn, readings: list[dict]) -> None:
    """Batch insert environment and gearbox readings into sensor_3min."""
    if not readings:
        return

    cols = [
        "ts", "batch_id", "station_id",
        "gearbox_temperature_c", "temperature_c", "humidity_rh",
        "data_quality_flag",
    ]
    rows = [
        tuple(r.get(c, "normal") if c == "data_quality_flag" else r.get(c) for c in cols)
        for r in readings
    ]
    col_str = ", ".join(cols)
    sql = f"INSERT INTO sensor_3min ({col_str}) VALUES %s"

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows)


def query_sensor_1min(conn, station_id: str, start_time: datetime, end_time: datetime) -> list[dict]:
    """Stable service wrapper for sensor_1min time-window reads."""
    return get_sensor_1min_series(
        conn,
        station_id=station_id,
        ts_start=start_time,
        ts_end=end_time,
    )


def query_sensor_3min(conn, station_id: str, start_time: datetime, end_time: datetime) -> list[dict]:
    """Stable service wrapper for sensor_3min time-window reads."""
    return get_sensor_3min_series(
        conn,
        station_id=station_id,
        ts_start=start_time,
        ts_end=end_time,
    )
