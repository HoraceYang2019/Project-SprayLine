from typing import Optional, Dict, Any
import json

from integration_adapter.database_versionb_adapter import insert_future_prediction_result


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
    prediction_id: Optional[str] = None,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a payload aligned with Database/versionB.future_prediction_result.

    0615 之後，future_prediction_result 已由 Database/versionB 提供，
    少榆端負責產生 Future payload，並可透過 save_future_prediction_result()
    呼叫 db_future.insert_future_prediction_result 寫回 DB。
    """
    return {
        "prediction_id": prediction_id,
        "batch_id": batch_id,
        "station_id": station_id,
        "prediction_time": prediction_time,
        "predicted_ok_rate": predicted_ok_rate,
        "predicted_ng_count": predicted_ng_count,
        "quality_score": quality_score,
        "risk_level": compute_risk_level(predicted_ok_rate, predicted_ng_count),
        "model_input_source": model_input_source,
        "created_at": created_at,
    }


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
        model_input_source="sensor_1min;sensor_3min;batch_run",
    )
    print(json.dumps(demo, ensure_ascii=False, indent=2))
