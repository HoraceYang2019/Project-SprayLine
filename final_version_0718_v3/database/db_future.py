"""Future prediction result queries for SprayLine DB."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any

from psycopg2.extras import Json

from db_connection import _fetch, _fetchone


def build_future_prediction_idempotency_key(payload: dict[str, Any]) -> str:
    """Return a stable key for one logical station prediction."""
    prediction_time = payload.get("prediction_time")
    if not isinstance(prediction_time, datetime):
        prediction_time = datetime.fromisoformat(
            str(prediction_time).replace("Z", "+00:00")
        )
    if prediction_time.tzinfo is None:
        prediction_time = prediction_time.replace(tzinfo=timezone.utc)
    epoch_text = f"{prediction_time.timestamp():.6f}"
    canonical_identity = "|".join(
        [
            str(payload.get("batch_id") or ""),
            str(payload.get("station_id") or ""),
            epoch_text,
            str(payload.get("prediction_method") or ""),
        ]
    )
    # Keep this identical to migrate_0718_v3_backend.sql for legacy rows.
    return hashlib.md5(canonical_identity.encode("utf-8")).hexdigest()


def insert_future_prediction_result(conn, payload: dict[str, Any]) -> str:
    """Upsert one logical Future prediction and return its stable row ID."""
    sql = """
        INSERT INTO future_prediction_result (
            prediction_id,
            batch_id,
            station_id,
            prediction_time,
            predicted_ok_rate,
            predicted_ng_count,
            quality_score,
            estimated_defect_rate_pct,
            quality_score_semantics,
            risk_level,
            prediction_method,
            model_input_source,
            idempotency_key,
            rule_evaluations,
            cause_ids,
            response_ids,
            rule_sources,
            created_at
        ) VALUES (
            COALESCE(%(prediction_id)s, gen_random_uuid()),
            %(batch_id)s,
            %(station_id)s,
            %(prediction_time)s,
            %(predicted_ok_rate)s,
            %(predicted_ng_count)s,
            %(quality_score)s,
            %(estimated_defect_rate_pct)s,
            %(quality_score_semantics)s,
            %(risk_level)s,
            %(prediction_method)s,
            %(model_input_source)s,
            %(idempotency_key)s,
            %(rule_evaluations)s,
            %(cause_ids)s,
            %(response_ids)s,
            %(rule_sources)s,
            COALESCE(%(created_at)s, now())
        )
        ON CONFLICT (idempotency_key) WHERE idempotency_key IS NOT NULL
        DO UPDATE SET
            predicted_ok_rate = EXCLUDED.predicted_ok_rate,
            predicted_ng_count = EXCLUDED.predicted_ng_count,
            quality_score = EXCLUDED.quality_score,
            estimated_defect_rate_pct = EXCLUDED.estimated_defect_rate_pct,
            quality_score_semantics = EXCLUDED.quality_score_semantics,
            risk_level = EXCLUDED.risk_level,
            model_input_source = EXCLUDED.model_input_source,
            rule_evaluations = EXCLUDED.rule_evaluations,
            cause_ids = EXCLUDED.cause_ids,
            response_ids = EXCLUDED.response_ids,
            rule_sources = EXCLUDED.rule_sources
        RETURNING prediction_id
    """
    defaults = {
        "prediction_id": None,
        "station_id": None,
        "predicted_ok_rate": None,
        "predicted_ng_count": None,
        "quality_score": None,
        "estimated_defect_rate_pct": None,
        "quality_score_semantics": "process_quality_score_not_measured_yield",
        "risk_level": None,
        "prediction_method": None,
        "model_input_source": None,
        "idempotency_key": None,
        "rule_evaluations": {},
        "cause_ids": [],
        "response_ids": [],
        "rule_sources": [],
        "created_at": None,
    }
    values = {**defaults, **payload}
    values["idempotency_key"] = (
        values.get("idempotency_key")
        or build_future_prediction_idempotency_key(values)
    )
    for json_field in ("rule_evaluations", "cause_ids", "response_ids", "rule_sources"):
        values[json_field] = Json(values.get(json_field) or ({} if json_field == "rule_evaluations" else []))
    with conn.cursor() as cur:
        cur.execute(sql, values)
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
