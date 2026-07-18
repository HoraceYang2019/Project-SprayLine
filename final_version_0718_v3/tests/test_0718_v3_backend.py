from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for rel in ("", "api", "services", "database"):
    path = str(ROOT / rel)
    if path not in sys.path:
        sys.path.insert(0, path)

from db_future import build_future_prediction_idempotency_key  # noqa: E402
from future_service.future_service import build_future_prediction_payload  # noqa: E402
from integrated_service.sprayline_integrated_service import IntegratedSprayLineService  # noqa: E402
from service_orchestration_adapter import _error  # noqa: E402


class _AbnormalFuturePredictor:
    def predict_station_raw_metrics(self, **_kwargs):
        return {
            "predicted_raw_metrics": {
                "paint_flow_ml_min": 115.0,
                "filter_diff_pressure_bar": 0.72,
                "servo_torque_load_pct": 50.0,
                "air_pressure_bar": 3.2,
                "spray_width_mm": 120.0,
                "path_error_mm": 0.05,
                "temperature_c": 25.0,
                "humidity_rh": 55.0,
            },
            "input_window": {"valid_sample_count_1min": 10},
            "confidence": {"overall": "medium"},
            "metric_diagnostics": {},
        }


class BackendV3Tests(unittest.TestCase):
    def test_idempotency_key_uses_logical_prediction_identity(self):
        base = {
            "batch_id": "B_001",
            "station_id": "Station_1",
            "prediction_method": "linear_trend_v1",
        }
        first = build_future_prediction_idempotency_key(
            {**base, "prediction_time": "2026-07-18T08:00:00+00:00"}
        )
        same_in_taipei = build_future_prediction_idempotency_key(
            {**base, "prediction_time": "2026-07-18T16:00:00+08:00"}
        )
        different_horizon = build_future_prediction_idempotency_key(
            {**base, "prediction_time": "2026-07-18T08:05:00+00:00"}
        )

        self.assertEqual(first, same_in_taipei)
        self.assertNotEqual(first, different_horizon)

    def test_future_payload_exposes_quality_semantics(self):
        payload = build_future_prediction_payload(
            batch_id="B_001",
            station_id="Station_1",
            prediction_time="2026-07-18T08:05:00+00:00",
            predicted_ok_rate=88.0,
            predicted_ng_count=5,
            quality_score=88.0,
            estimated_defect_rate_pct=12.0,
            prediction_method="linear_trend_v1",
        )

        self.assertEqual(
            payload["quality_score_semantics"],
            "process_quality_score_not_measured_yield",
        )
        self.assertIn("not_measured_yield", payload["predicted_ok_rate_semantics"])
        self.assertIn("not_measured_defect_rate", payload["estimated_defect_rate_semantics"])

    def test_integrated_future_contains_ttl_cause_and_response(self):
        service = IntegratedSprayLineService()
        service.future_predictor = _AbnormalFuturePredictor()
        snapshot = {
            "batch_id": "B_001",
            "station_id": "Station_1",
            "ts": "2026-07-18T08:00:00+00:00",
        }

        payload = service.estimate_future_from_history(
            rows_1min=[],
            rows_3min=[],
            snapshot=snapshot,
            station_id="Station_1",
            prediction_time="2026-07-18T08:05:00+00:00",
        )

        self.assertEqual(payload["prediction_method"], "linear_trend_v1")
        self.assertIn("FILTER_CLOG", payload["cause_ids"])
        self.assertIn("REPLACE_FILTER", payload["response_ids"])
        self.assertIn("BACKWASH_FILTER", payload["response_ids"])
        self.assertEqual(payload["rule_sources"], ["ontology/sprayline_threshold.ttl"])
        self.assertEqual(
            payload["rule_evaluations"]["filter_diff_pressure_bar"]["state"],
            "fault",
        )

    def test_adapter_error_has_status_without_traceback(self):
        try:
            raise ValueError("bad window")
        except ValueError as exc:
            result = _error("test_validation", exc)

        self.assertFalse(result["success"])
        self.assertEqual(result["_http_status"], 422)
        self.assertEqual(result["error_code"], "invalid_request")
        self.assertNotIn("traceback_tail", result)

    def test_v3_migration_and_compose_contract(self):
        migration = (ROOT / "database" / "migrate_0718_v3_backend.sql").read_text(
            encoding="utf-8"
        )
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertNotIn("DROP TABLE", migration.upper())
        self.assertIn("uq_future_prediction_idempotency", migration)
        self.assertIn("rule_evaluations JSONB", migration)
        self.assertIn("db-migrate:", compose)
        self.assertIn("condition: service_completed_successfully", compose)


if __name__ == "__main__":
    unittest.main()
