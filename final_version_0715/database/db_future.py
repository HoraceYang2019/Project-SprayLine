"""Future prediction result queries for SprayLine DB."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from db_connection import _fetch, _fetchone


def insert_future_prediction_result(conn, payload: dict[str, Any]) -> str:
    """Insert one future prediction result and return prediction_id."""
    sql = """
        INSERT INTO future_prediction_result (
            prediction_id,
            batch_id,
            station_id,
            prediction_time,
            predicted_ok_rate,
            predicted_ng_count,
            quality_score,
            risk_level,
            prediction_method,
            model_input_source,
            created_at
        ) VALUES (
            COALESCE(%(prediction_id)s, gen_random_uuid()),
            %(batch_id)s,
            %(station_id)s,
            %(prediction_time)s,
            %(predicted_ok_rate)s,
            %(predicted_ng_count)s,
            %(quality_score)s,
            %(risk_level)s,
            %(prediction_method)s,
            %(model_input_source)s,
            COALESCE(%(created_at)s, now())
        )
        RETURNING prediction_id
    """
    defaults = {
        "prediction_id": None,
        "station_id": None,
        "predicted_ok_rate": None,
        "predicted_ng_count": None,
        "quality_score": None,
        "risk_level": None,
        "prediction_method": None,
        "model_input_source": None,
        "created_at": None,
    }
    with conn.cursor() as cur:
        cur.execute(sql, {**defaults, **payload})
        row = cur.fetchone()
    return str(row[0])


def get_latest_future_prediction(conn, station_id: str | None = None) -> dict | None:
    """Return the latest future prediction, optionally scoped to a station."""
    if station_id:
        sql = """
            SELECT *
            FROM   future_prediction_result
            WHERE  station_id = %s
            ORDER  BY prediction_time DESC, created_at DESC
            LIMIT  1
        """
        return _fetchone(conn, sql, (station_id,))

    sql = """
        SELECT *
        FROM   future_prediction_result
        ORDER  BY prediction_time DESC, created_at DESC
        LIMIT  1
    """
    return _fetchone(conn, sql)


def get_future_predictions_by_range(
    conn,
    start_time: datetime,
    end_time: datetime,
    station_id: str | None = None,
) -> list[dict]:
    """Return future predictions by prediction_time range."""
    if station_id:
        sql = """
            SELECT *
            FROM   future_prediction_result
            WHERE  prediction_time >= %s
              AND  prediction_time <  %s
              AND  station_id = %s
            ORDER  BY prediction_time DESC
        """
        return _fetch(conn, sql, (start_time, end_time, station_id))

    sql = """
        SELECT *
        FROM   future_prediction_result
        WHERE  prediction_time >= %s
          AND  prediction_time <  %s
        ORDER  BY prediction_time DESC
    """
    return _fetch(conn, sql, (start_time, end_time))


def get_future_prediction_summary(conn, station_id: str | None = None) -> dict:
    """Return a compact latest-risk summary for manager views."""
    latest = get_latest_future_prediction(conn, station_id=station_id)
    return {
        "available": latest is not None,
        "pending_db_table": False,
        "latest_risk_level": latest.get("risk_level") if latest else None,
        "latest_predicted_ok_rate": latest.get("predicted_ok_rate") if latest else None,
        "latest_predicted_ng_count": latest.get("predicted_ng_count") if latest else None,
    }
