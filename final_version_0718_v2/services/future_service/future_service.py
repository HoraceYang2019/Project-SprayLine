"""Future prediction service for SprayLine.

This existing service module now contains both:
1. history-based raw sensor prediction (linear_trend_v1), and
2. future payload construction / persistence.

Derived process metrics and component states remain the responsibility of the
IntegratedSprayLineService and ontology/rule classifier.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import json

from integration_adapter.database_versionb_adapter import insert_future_prediction_result

RAW_1MIN_METRICS: Tuple[str, ...] = (
    "paint_flow_ml_min",
    "filter_diff_pressure_bar",
    "servo_torque_load_pct",
    "air_pressure_bar",
    "spray_width_mm",
    "path_error_mm",
)

RAW_3MIN_METRICS: Tuple[str, ...] = (
    "temperature_c",
    "humidity_rh",
)

# Physical/output bounds protect the first prediction version from runaway
# linear extrapolation.  They are safety limits, not process acceptance rules.
METRIC_BOUNDS: Dict[str, Tuple[float, float]] = {
    "paint_flow_ml_min": (0.0, 250.0),
    "filter_diff_pressure_bar": (0.0, 2.0),
    "servo_torque_load_pct": (0.0, 100.0),
    "air_pressure_bar": (0.0, 10.0),
    "spray_width_mm": (0.0, 250.0),
    "path_error_mm": (0.0, 2.0),
    "temperature_c": (-20.0, 80.0),
    "humidity_rh": (0.0, 100.0),
}

# Maximum absolute change per minute.  These caps are intentionally wider
# than normal operation so the simulator's short steep-degradation episodes
# remain visible, while long-horizon values still cannot explode numerically.
MAX_ABS_SLOPE_PER_MINUTE: Dict[str, float] = {
    "paint_flow_ml_min": 15.0,
    "filter_diff_pressure_bar": 0.15,
    "servo_torque_load_pct": 15.0,
    "air_pressure_bar": 0.15,
    "spray_width_mm": 8.0,
    "path_error_mm": 0.05,
    "temperature_c": 0.20,
    "humidity_rh": 0.50,
}


@dataclass(frozen=True)
class MetricPrediction:
    metric: str
    predicted_value: Optional[float]
    latest_value: Optional[float]
    slope_per_minute: Optional[float]
    raw_slope_per_minute: Optional[float]
    sample_count: int
    time_span_minutes: float
    r_squared: Optional[float]
    method: str
    confidence: str
    fallback_reason: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "predicted_value": self.predicted_value,
            "latest_value": self.latest_value,
            "slope_per_minute": self.slope_per_minute,
            "raw_slope_per_minute": self.raw_slope_per_minute,
            "sample_count": self.sample_count,
            "time_span_minutes": round(self.time_span_minutes, 4),
            "r_squared": self.r_squared,
            "method": self.method,
            "confidence": self.confidence,
            "fallback_reason": self.fallback_reason,
        }


def _to_float(value: Any) -> Optional[float]:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if isfinite(result) else None


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        parsed = value
    elif value is None:
        return None
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _round_metric(metric: str, value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    digits = {
        "filter_diff_pressure_bar": 4,
        "air_pressure_bar": 4,
        "path_error_mm": 5,
        "temperature_c": 3,
        "humidity_rh": 3,
    }.get(metric, 3)
    return round(value, digits)


def _valid_metric_samples(rows: Iterable[Mapping[str, Any]], metric: str) -> List[Tuple[datetime, float]]:
    samples: List[Tuple[datetime, float]] = []
    for row in rows:
        # Interpolated rows are intentionally excluded from model fitting.
        if str(row.get("data_quality_flag") or "normal").lower() == "interpolated":
            continue
        ts = _parse_datetime(row.get("ts") or row.get("timestamp"))
        value = _to_float(row.get(metric))
        if ts is None or value is None:
            continue
        samples.append((ts, value))

    # Deduplicate timestamps so repeated joins cannot bias the slope.
    by_time: Dict[datetime, float] = {ts: value for ts, value in samples}
    return sorted(by_time.items(), key=lambda item: item[0])


def _linear_regression(samples: Sequence[Tuple[datetime, float]]) -> Tuple[float, float, Optional[float], float]:
    """Return slope/minute, intercept, R² and time span in minutes."""
    origin = samples[0][0]
    x = [(ts - origin).total_seconds() / 60.0 for ts, _ in samples]
    y = [value for _, value in samples]
    count = len(samples)
    mean_x = sum(x) / count
    mean_y = sum(y) / count
    denominator = sum((item - mean_x) ** 2 for item in x)
    if denominator <= 0:
        return 0.0, mean_y, None, 0.0

    slope = sum((xv - mean_x) * (yv - mean_y) for xv, yv in zip(x, y)) / denominator
    intercept = mean_y - slope * mean_x

    total_variance = sum((value - mean_y) ** 2 for value in y)
    if total_variance <= 1e-12:
        r_squared = 1.0
    else:
        residual = sum((yv - (intercept + slope * xv)) ** 2 for xv, yv in zip(x, y))
        r_squared = max(0.0, min(1.0, 1.0 - residual / total_variance))

    span = max(x) - min(x)
    return slope, intercept, r_squared, span


def _confidence(sample_count: int, span_minutes: float, r_squared: Optional[float], fallback: bool) -> str:
    if fallback:
        return "low"
    if sample_count >= 20 and span_minutes >= 20 and (r_squared or 0.0) >= 0.45:
        return "high"
    if sample_count >= 8 and span_minutes >= 5:
        return "medium"
    return "low"


class FuturePredictionService:
    """Predict raw SprayLine sensor values with linear trend extrapolation."""

    prediction_method = "linear_trend_v1"

    def __init__(self, min_samples: int = 5):
        if min_samples < 2:
            raise ValueError("min_samples must be at least 2")
        self.min_samples = int(min_samples)

    def predict_metric(
        self,
        rows: Sequence[Mapping[str, Any]],
        metric: str,
        prediction_time: Any,
        fallback_value: Any = None,
    ) -> MetricPrediction:
        target_time = _parse_datetime(prediction_time)
        if target_time is None:
            raise ValueError("prediction_time must be an ISO-8601 datetime or datetime object")

        samples = _valid_metric_samples(rows, metric)
        latest_fallback = _to_float(fallback_value)

        if not samples:
            value = latest_fallback
            if value is not None and metric in METRIC_BOUNDS:
                value = _clamp(value, *METRIC_BOUNDS[metric])
            return MetricPrediction(
                metric=metric,
                predicted_value=_round_metric(metric, value),
                latest_value=_round_metric(metric, value),
                slope_per_minute=0.0 if value is not None else None,
                raw_slope_per_minute=None,
                sample_count=0,
                time_span_minutes=0.0,
                r_squared=None,
                method="last_value_fallback" if value is not None else "no_data",
                confidence="low",
                fallback_reason="no_valid_samples",
            )

        latest_ts, latest_value = samples[-1]
        horizon_minutes = max(0.0, (target_time - latest_ts).total_seconds() / 60.0)

        if len(samples) < self.min_samples:
            value = latest_value
            if metric in METRIC_BOUNDS:
                value = _clamp(value, *METRIC_BOUNDS[metric])
            span = (samples[-1][0] - samples[0][0]).total_seconds() / 60.0 if len(samples) > 1 else 0.0
            return MetricPrediction(
                metric=metric,
                predicted_value=_round_metric(metric, value),
                latest_value=_round_metric(metric, latest_value),
                slope_per_minute=0.0,
                raw_slope_per_minute=None,
                sample_count=len(samples),
                time_span_minutes=max(0.0, span),
                r_squared=None,
                method="last_value_fallback",
                confidence="low",
                fallback_reason=f"fewer_than_{self.min_samples}_valid_samples",
            )

        raw_slope, _, r_squared, span = _linear_regression(samples)
        slope_cap = MAX_ABS_SLOPE_PER_MINUTE.get(metric)
        slope = raw_slope if slope_cap is None else _clamp(raw_slope, -slope_cap, slope_cap)
        predicted = latest_value + slope * horizon_minutes
        if metric in METRIC_BOUNDS:
            predicted = _clamp(predicted, *METRIC_BOUNDS[metric])

        confidence = _confidence(len(samples), span, r_squared, fallback=False)
        return MetricPrediction(
            metric=metric,
            predicted_value=_round_metric(metric, predicted),
            latest_value=_round_metric(metric, latest_value),
            slope_per_minute=round(slope, 8),
            raw_slope_per_minute=round(raw_slope, 8),
            sample_count=len(samples),
            time_span_minutes=max(0.0, span),
            r_squared=round(r_squared, 4) if r_squared is not None else None,
            method=self.prediction_method,
            confidence=confidence,
            fallback_reason=None,
        )

    def predict_station_raw_metrics(
        self,
        rows_1min: Sequence[Mapping[str, Any]],
        rows_3min: Sequence[Mapping[str, Any]],
        prediction_time: Any,
        latest_snapshot: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        latest_snapshot = latest_snapshot or {}
        predictions: Dict[str, MetricPrediction] = {}

        for metric in RAW_1MIN_METRICS:
            predictions[metric] = self.predict_metric(
                rows_1min,
                metric,
                prediction_time,
                fallback_value=latest_snapshot.get(metric),
            )
        for metric in RAW_3MIN_METRICS:
            predictions[metric] = self.predict_metric(
                rows_3min,
                metric,
                prediction_time,
                fallback_value=latest_snapshot.get(metric),
            )

        predicted_metrics = {
            metric: prediction.predicted_value
            for metric, prediction in predictions.items()
            if prediction.predicted_value is not None
        }
        diagnostics = {metric: prediction.as_dict() for metric, prediction in predictions.items()}

        valid_rows_1min = [row for row in rows_1min if str(row.get("data_quality_flag") or "normal").lower() != "interpolated"]
        valid_rows_3min = [row for row in rows_3min if str(row.get("data_quality_flag") or "normal").lower() != "interpolated"]
        timestamps = [
            parsed
            for row in [*valid_rows_1min, *valid_rows_3min]
            if (parsed := _parse_datetime(row.get("ts") or row.get("timestamp"))) is not None
        ]

        confidence_rank = {"low": 1, "medium": 2, "high": 3}
        metric_confidences = [item.confidence for item in predictions.values() if item.predicted_value is not None]
        overall_confidence = (
            min(metric_confidences, key=lambda item: confidence_rank.get(item, 0))
            if metric_confidences
            else "low"
        )

        return {
            "prediction_method": self.prediction_method,
            "prediction_time": _parse_datetime(prediction_time).isoformat(),
            "predicted_raw_metrics": predicted_metrics,
            "metric_diagnostics": diagnostics,
            "confidence": {
                "overall": overall_confidence,
                "by_metric": {metric: item.confidence for metric, item in predictions.items()},
            },
            "input_window": {
                "start_time": min(timestamps).isoformat() if timestamps else None,
                "end_time": max(timestamps).isoformat() if timestamps else None,
                "sample_count_1min": len(rows_1min),
                "valid_sample_count_1min": len(valid_rows_1min),
                "sample_count_3min": len(rows_3min),
                "valid_sample_count_3min": len(valid_rows_3min),
                "interpolated_rows_excluded": (len(rows_1min) - len(valid_rows_1min)) + (len(rows_3min) - len(valid_rows_3min)),
            },
        }


def compute_risk_level(predicted_ok_rate: Optional[float], predicted_ng_count: Optional[int]) -> Optional[str]:
    """Compute batch risk level from Future prediction metrics.

    Current discussion rule, pending final confirmation:
    - high: predicted_ok_rate < 84 or predicted_ng_count >= 35
    - medium: predicted_ok_rate < 90 or predicted_ng_count >= 20
    - low: otherwise

    注意：此規則目前是討論版，用於 Future payload 與 UI 串接測試，
    不是宣告為最終正式品質規則。
    """
    if predicted_ok_rate is None and predicted_ng_count is None:
        return None

    ok = 100.0 if predicted_ok_rate is None else float(predicted_ok_rate)
    ng = 0 if predicted_ng_count is None else int(predicted_ng_count)

    if ok < 84 or ng >= 35:
        return "high"
    if ok < 90 or ng >= 20:
        return "medium"
    return "low"


def build_future_prediction_payload(
    batch_id: str,
    station_id: Optional[str],
    prediction_time: str,
    predicted_ok_rate: Optional[float] = None,
    predicted_ng_count: Optional[int] = None,
    quality_score: Optional[float] = None,
    prediction_method: Optional[str] = "deterministic_formula",
    model_input_source: Optional[str] = None,
    prediction_id: Optional[str] = None,
    created_at: Optional[str] = None,
    predicted_metrics: Optional[Dict[str, Any]] = None,
    predicted_components: Optional[Dict[str, Any]] = None,
    horizon_minutes: Optional[float] = None,
    input_window: Optional[Dict[str, Any]] = None,
    confidence: Optional[Dict[str, Any]] = None,
    metric_diagnostics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a Future payload with DB-compatible legacy summary fields.

    The legacy scalar fields remain aligned with
    Database/versionB.future_prediction_result.  ``predicted_metrics``,
    diagnostics and component states are API response fields in v1 and are not
    persisted as separate DB columns by the current database schema.
    """
    predicted_metrics = dict(predicted_metrics or {})
    predicted_components = dict(predicted_components or {})
    payload = {
        "prediction_id": prediction_id,
        "batch_id": batch_id,
        "station_id": station_id,
        "prediction_time": prediction_time,
        "horizon_minutes": horizon_minutes,
        "predicted_ok_rate": predicted_ok_rate,
        "predicted_ng_count": predicted_ng_count,
        "quality_score": quality_score,
        "risk_level": compute_risk_level(predicted_ok_rate, predicted_ng_count),
        "prediction_method": prediction_method,
        "model_input_source": model_input_source,
        "input_window": input_window or {},
        "confidence": confidence or {},
        "metric_diagnostics": metric_diagnostics or {},
        "predicted_metrics": predicted_metrics,
        "predicted_components": predicted_components,
        "created_at": created_at,
    }

    # Backward-compatible explicit aliases make the first prediction version
    # easy for UI clients to consume without guessing nested field names.
    for metric, value in predicted_metrics.items():
        payload[f"predicted_{metric}"] = value

    # The Engineer UI historically names the quality-card metric
    # ``film_thickness_um``.  The formal service value is estimated, so keep
    # the authoritative field and expose this compatibility alias explicitly.
    if predicted_metrics.get("estimated_film_thickness_um") is not None:
        payload["predicted_film_thickness_um"] = predicted_metrics["estimated_film_thickness_um"]

    return payload


def save_future_prediction_result(conn, payload: Dict[str, Any], commit: bool = True) -> str:
    """Save Future prediction payload through Yu-Cheng Database/versionB function.

    This calls:
    - db_future.insert_future_prediction_result(conn, payload)

    所有 DB function 均不自動 commit；此函式預設會 commit，
    若上層要管理 transaction，可傳 commit=False。
    """
    prediction_id = insert_future_prediction_result(conn, payload)
    if commit:
        conn.commit()
    return prediction_id


def build_and_save_future_prediction_result(conn, commit: bool = True, **kwargs) -> str:
    payload = build_future_prediction_payload(**kwargs)
    return save_future_prediction_result(conn, payload, commit=commit)


if __name__ == "__main__":
    demo = build_future_prediction_payload(
        batch_id="BATCH_DEMO_001",
        station_id="Station_1",
        prediction_time="2026-06-16T10:00:00+08:00",
        predicted_ok_rate=88.5,
        predicted_ng_count=22,
        quality_score=87.0,
        prediction_method="deterministic_formula",
        model_input_source="sensor_1min;sensor_3min;batch_run",
    )
    print(json.dumps(demo, ensure_ascii=False, indent=2))
