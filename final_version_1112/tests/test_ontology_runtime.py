from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for rel in ("", "services", "database"):
    path = str(ROOT / rel)
    if path not in sys.path:
        sys.path.insert(0, path)

from event_rule_service.runtime_rule_classifier import classify_sensor_value  # noqa: E402
from integrated_service.sprayline_integrated_service import IntegratedSprayLineService  # noqa: E402
from monitoring_worker.threshold_evaluator import evaluate_sensor_payload  # noqa: E402
from ontology.rule_inference import load_rules  # noqa: E402


class OntologyRuntimeTests(unittest.TestCase):
    def test_ontology_is_primary_rule_source(self):
        result = classify_sensor_value("air_pressure_bar", 4.1)

        self.assertEqual(result["state"], "fault")
        self.assertEqual(result["cause_id"], "AIR_PRESSURE_UNSTABLE")
        self.assertEqual(result["response_ids"], ["CALIBRATE_PRESSURE_VALVE"])
        self.assertEqual(result["rule_engine"], "ontology.rule_inference")
        self.assertEqual(result["rule_source"], "ontology/sprayline_threshold.ttl")
        self.assertIsNone(result["fallback_reason"])

    def test_runtime_thresholds_match_formal_ranges(self):
        self.assertEqual(classify_sensor_value("paint_flow_ml_min", 115)["state"], "normal")
        self.assertEqual(classify_sensor_value("paint_flow_ml_min", 100)["state"], "warning")
        self.assertEqual(classify_sensor_value("paint_flow_ml_min", 130)["state"], "fault")
        self.assertEqual(classify_sensor_value("servo_torque_load_pct", 35)["state"], "warning")
        self.assertEqual(classify_sensor_value("servo_torque_load_pct", 80)["state"], "fault")

    def test_json_fallback_is_explicit(self):
        missing_ttl = ROOT / "ontology" / "missing_runtime_threshold.ttl"
        result = classify_sensor_value("temperature_c", 25, ttl_path=missing_ttl)

        self.assertEqual(result["state"], "normal")
        self.assertEqual(result["rule_engine"], "json_threshold_fallback")
        self.assertEqual(result["rule_source"], "rules/sensor_thresholds.json")
        self.assertTrue(result["fallback_reason"].startswith("ontology_error:"))

    def test_monitoring_uses_ontology_cause_and_responses(self):
        results = evaluate_sensor_payload({"spray_width_mm": 145.0})

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["cause_id"], "SPRAY_WIDTH_DEVIATION")
        self.assertEqual(
            results[0]["response_ids"],
            ["ADJUST_TCP_Z", "ADJUST_FLOW_PRESSURE", "REPLACE_NOZZLE"],
        )
        self.assertEqual(results[0]["rule_engine"], "ontology.rule_inference")

    def test_integrated_service_exposes_rule_evidence(self):
        row = {
            "station_id": "Station_1",
            "paint_flow_ml_min": 115.0,
            "filter_diff_pressure_bar": 0.72,
            "air_pressure_bar": 3.2,
            "spray_width_mm": 120.0,
            "servo_torque_load_pct": 50.0,
            "path_error_mm": 0.05,
            "temperature_c": 25.0,
            "humidity_rh": 55.0,
        }

        result = IntegratedSprayLineService().derive_formal_metrics(row, "Station_1")

        self.assertEqual(result["station_state"], "fault")
        self.assertEqual(result["rule_engine"], "ontology.rule_inference")
        self.assertEqual(result["rule_source"], "ontology/sprayline_threshold.ttl")
        self.assertEqual(
            result["rule_evaluations"]["filter_diff_pressure_bar"]["cause_id"],
            "FILTER_CLOG",
        )

    def test_protege_ontology_matches_runtime_rules(self):
        rules = load_rules(ROOT / "ontology" / "sprayline_threshold.ttl")
        full_ontology = (ROOT / "ontology" / "sprayline_full_ontology.ttl").read_text(encoding="utf-8")

        self.assertEqual(full_ontology.count(" a sl:SensorThreshold"), len(rules))
        for metric, rule in rules.items():
            self.assertIn(f"sl:Threshold_{metric} a sl:SensorThreshold", full_ontology)
            if rule.cause_id:
                self.assertIn(f"sl:Cause_{rule.cause_id} a sl:Cause", full_ontology)
            for response_id in rule.response_ids:
                self.assertIn(f"sl:Action_{response_id} a sl:ResponseAction", full_ontology)


if __name__ == "__main__":
    unittest.main()
