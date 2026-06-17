"""
SprayLine DB — 批次生產管理（batch_run）
對應 Schema v5.1、PostgreSQL 16

匯入方式
--------
from db_batch import get_latest_batches, insert_batch_run, update_batch_status
"""

from __future__ import annotations

from datetime import datetime

from db_connection import _fetch, _fetchone


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
