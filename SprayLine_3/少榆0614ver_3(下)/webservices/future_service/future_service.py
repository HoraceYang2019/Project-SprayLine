from typing import Optional, Dict, Any
import json


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
    model_input_source: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a Future prediction result payload.

    少榆端負責建立 Future 預測結果 payload 與 risk_level。
    正式寫回 DB 的 endpoint / table 由 Database / DB API 端補齊後串接。

    Required DB table, pending Yu-Cheng update:
    - future_prediction_result
    """
    return {
        "batch_id": batch_id,
        "station_id": station_id,
        "prediction_time": prediction_time,
        "predicted_ok_rate": predicted_ok_rate,
        "predicted_ng_count": predicted_ng_count,
        "quality_score": quality_score,
        "risk_level": compute_risk_level(predicted_ok_rate, predicted_ng_count),
        "model_input_source": model_input_source,
        "persistence_status": "payload_ready_pending_yucheng_db_api",
    }


if __name__ == "__main__":
    demo = build_future_prediction_payload(
        batch_id="BATCH_DEMO_001",
        station_id="Station_1",
        prediction_time="2026-06-14T10:00:00+08:00",
        predicted_ok_rate=88.5,
        predicted_ng_count=22,
        quality_score=87.0,
        model_input_source="sensor_1min;sensor_3min;batch_run",
    )
    print(json.dumps(demo, ensure_ascii=False, indent=2))
