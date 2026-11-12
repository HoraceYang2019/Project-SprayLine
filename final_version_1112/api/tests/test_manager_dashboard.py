from __future__ import annotations

import importlib
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "api"
SERVICES_DIR = ROOT / "services"
DATABASE_DIR = ROOT / "database"

for path in (DATABASE_DIR, SERVICES_DIR, API_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from manager_dashboard_service import build_manager_dashboard_payload


def _build_sample_bundle() -> dict:
    manager_rows: list[dict] = []

    def add_manager_rows(station_id: str, line_id: str, batch_id: str, hour: int, row_count: int, quality_score: float) -> None:
        for _ in range(row_count):
            manager_rows.append(
                {
                    "stationId": station_id,
                    "lineId": line_id,
                    "batchId": batch_id,
                    "dataHour": hour,
                    "quality_score_pct": quality_score,
                }
            )

    def station_bundle(
        line_id: str,
        pressure_bar: float,
        flow_rate: float,
        spray_width: float,
        quality_score: float,
        utilization: float,
        cycle_time: float,
        clog_rate: float,
        predicted_ok_rate: float,
        predicted_ng_pcs: int,
        alert_total: int,
        state: str,
    ) -> tuple[dict, dict, dict, dict, dict, dict]:
        latest = {
            "signal": {
                "pressure_bar": pressure_bar,
                "flow_rate_ml_min": flow_rate,
                "spray_width_mm": spray_width,
                "temperature_c": 28.0,
                "state": state,
                "recipe_name": f"{line_id}_recipe",
            },
            "reference": {
                "target_min_mm": 176.0,
                "target_max_mm": 190.0,
                "baseline_pressure_bar": 2.2,
                "baseline_flow_rate_ml_min": 126.0,
                "baseline_quality_score_pct": 94.0,
                "baseline_utilization_pct": 85.0,
                "baseline_cycle_time_sec": 45.0,
            },
            "metric": {
                "quality_score_pct": quality_score,
                "utilization_pct": utilization,
                "cycle_time_sec": cycle_time,
                "clog_rate_pct": clog_rate,
                "availability_pct": 90.0,
                "maintainability_pct": 92.0,
            },
            "components": [
                {"component_key": "nozzle", "level": "warning" if clog_rate >= 10 else "normal"},
                {"component_key": "filter_mesh", "level": "warning" if clog_rate >= 10 else "normal"},
                {"component_key": "robot_arm", "level": "normal"},
            ],
        }
        diagnosis = {
            "diagnoses": [
                {
                    "category": "pdm",
                    "state_label": "Filter load high" if clog_rate >= 10 else "Stable",
                    "severity": "warning" if clog_rate >= 10 else "normal",
                    "confidence": 0.9,
                    "evidence": f"clog_rate_pct={clog_rate}",
                    "action": "Inspect nozzle and filter mesh",
                }
            ]
        }
        alerts = {
            "total": alert_total,
            "alerts": [{"event_id": f"{line_id}-alert-1", "severity": "warning"}] if alert_total else [],
        }
        kpi = {
            "predicted_ok_rate": predicted_ok_rate,
            "line_utilization": utilization,
            "avg_cycle_time_s": cycle_time,
            "predicted_ng_pcs": predicted_ng_pcs,
        }
        prediction_accuracy = {"accuracy_pct": 91.5}
        quality_trend = {
            "actual_series": [{"hour": hour, "quality_score_pct": quality_score - (0.2 if hour < 8 else 0.0)} for hour in range(24)]
        }
        single_series = {"series": [{"hour": hour, "utilization_pct": utilization} for hour in range(24)]}
        cycle_series = {"series": [{"hour": hour, "cycle_time_sec": cycle_time} for hour in range(24)]}
        return latest, diagnosis, alerts, kpi, prediction_accuracy, {
            "quality": quality_trend,
            "utilization": single_series,
            "cycle": cycle_series,
        }

    station_inputs = {
        "line_1": station_bundle("line_1", 2.18, 124.0, 182.0, 93.6, 82.5, 46.8, 6.8, 93.4, 128, 0, "running"),
        "line_2": station_bundle("line_2", 2.52, 111.0, 196.0, 89.1, 74.6, 52.4, 14.6, 90.2, 610, 1, "warning"),
        "line_3": station_bundle("line_3", 2.07, 119.0, 187.0, 92.0, 80.4, 48.1, 8.7, 92.1, 214, 0, "running"),
    }

    add_manager_rows("Station_1", "line_1", "BATCH-001", 9, 48, 93.5)
    add_manager_rows("Station_1", "line_1", "BATCH-002", 10, 46, 88.8)
    add_manager_rows("Station_1", "line_1", "BATCH-003", 10, 44, 90.2)
    add_manager_rows("Station_2", "line_2", "BATCH-001", 9, 45, 91.4)
    add_manager_rows("Station_2", "line_2", "BATCH-002", 10, 42, 86.5)
    add_manager_rows("Station_3", "line_3", "BATCH-004", 8, 50, 94.2)
    add_manager_rows("Station_3", "line_3", "BATCH-003", 10, 47, 92.8)

    return {
        "generated_at": "2026-06-27T10:20:00+08:00",
        "source": "Manager Dashboard API",
        "selectionMeta": {
            "selectedDate": "2026-06-27",
            "selectedHour": 10,
            "dateSource": "db_latest",
            "availableDates": ["2026-06-27", "2026-06-26"],
            "availableHours": list(range(0, 11)),
            "availableHoursByDate": {
                "2026-06-27": list(range(0, 11)),
                "2026-06-26": list(range(0, 24)),
            },
            "latestDate": "2026-06-27",
            "latestHour": 10,
            "anchorTime": "2026-06-27T10:20:00+08:00",
            "selectedHourStart": "2026-06-27T10:00:00+08:00",
            "selectedHourEnd": "2026-06-27T11:00:00+08:00",
        },
        "currentBatch": {
            "batchId": "BATCH-20260627-001",
            "status": "running",
            "startTime": "2026-06-27T08:00:00+08:00",
            "endedTime": None,
        },
        "stationLatest": {line_id: value[0] for line_id, value in station_inputs.items()},
        "diagnosisLatest": {line_id: value[1] for line_id, value in station_inputs.items()},
        "pendingAlerts": {line_id: value[2] for line_id, value in station_inputs.items()},
        "kpiSummary": {line_id: value[3] for line_id, value in station_inputs.items()},
        "predictionAccuracy": {line_id: value[4] for line_id, value in station_inputs.items()},
        "qualityTrend": {line_id: value[5]["quality"] for line_id, value in station_inputs.items()},
        "utilizationTrend": {line_id: value[5]["utilization"] for line_id, value in station_inputs.items()},
        "cycleTimeTrend": {line_id: value[5]["cycle"] for line_id, value in station_inputs.items()},
        "managerDataset": {
            "selectedBatchId": None,
            "defaultBatchModeLabel": "全部批號 / 該小時累計",
            "dailyDistinctBatchCount": 4,
            "dailySensorRows": manager_rows,
            "activeAlertsByLine": {
                "line_1": [],
                "line_2": [{"batch_id": "BATCH-002", "state": "warning"}],
                "line_3": [],
            },
        },
    }


class ManagerDashboardContractTests(unittest.TestCase):
    maxDiff = None

    def test_api_server_is_importable_with_workspace_paths(self) -> None:
        module = importlib.import_module("api_server")
        self.assertTrue(hasattr(module, "app"))

    def test_manager_endpoint_declared_in_api_server_source(self) -> None:
        source = (ROOT / "api" / "api_server.py").read_text(encoding="utf-8")
        self.assertIn('@app.get("/api/manager/dashboard")', source)
        self.assertIn('@app.get("/api/manager/available-dates")', source)
        self.assertIn("build_manager_dashboard_payload", source)
        self.assertIn("date is required when hour is provided", source)
        self.assertIn("date and hour are required when batch_id is provided", source)

    def test_manager_service_builds_ui_ready_payload(self) -> None:
        payload = build_manager_dashboard_payload(_build_sample_bundle())

        self.assertEqual(payload["responseMeta"]["source"], "Manager Dashboard API")
        self.assertEqual(payload["responseMeta"]["selectedDate"], "2026-06-27")
        self.assertEqual(payload["responseMeta"]["selectedHour"], 10)
        self.assertEqual(payload["responseMeta"]["latestDate"], "2026-06-27")
        self.assertEqual(payload["responseMeta"]["latestHour"], 10)
        self.assertEqual(payload["responseMeta"]["dateSource"], "db_latest")
        self.assertIn("2026-06-27", payload["responseMeta"]["availableDates"])
        self.assertEqual(payload["responseMeta"]["availableHoursByDate"]["2026-06-27"][-1], 10)
        self.assertIsNone(payload["responseMeta"]["selectedBatchId"])
        self.assertIn("managerSummary", payload)
        self.assertIn("managerView", payload)
        self.assertIn("stationTelemetry", payload)
        self.assertIn("productionKpi", payload)
        self.assertIn("qualityValidation", payload)
        self.assertIn("qualityHistory", payload)
        self.assertIn("forecastNoAction", payload)
        self.assertEqual(len(payload["stationTelemetry"]), 3)

        summary = payload["managerSummary"]
        self.assertEqual(summary["dataSource"], payload["responseMeta"]["source"])
        self.assertIn("mainStationRiskScore", summary)
        self.assertIn("mainStationComponents", summary)
        self.assertIn("stationEvaluations", summary)
        self.assertIn("assignments", summary)
        self.assertIn("acceptanceChecklist", summary)
        self.assertGreaterEqual(summary["mainStationRiskScore"], 0)
        self.assertGreaterEqual(len(summary["assignments"]), 1)
        self.assertGreaterEqual(len(summary["acceptanceChecklist"]), 1)

        manager_view = payload["managerView"]
        self.assertAlmostEqual(
            manager_view["kpis"]["estimatedNgRatePct"],
            round(100.0 - manager_view["kpis"]["estimatedOkRatePct"], 1),
        )
        self.assertEqual(manager_view["kpis"]["dailyProduction"]["batchSizePcs"], 264)
        self.assertEqual(manager_view["kpis"]["dailyProduction"]["dailyTargetPcs"], 20000)
        self.assertEqual(manager_view["kpis"]["dailyProduction"]["distinctBatchCount"], 4)
        self.assertEqual(manager_view["batchSelector"]["defaultModeLabel"], "全部批號 / 該小時累計")
        self.assertGreaterEqual(len(manager_view["batchSelector"]["availableBatches"]), 1)
        self.assertEqual(len(manager_view["stationComparison"]), 3)
        self.assertIn("trendDrawer", manager_view)
        self.assertIn("recommendations", manager_view)

    def test_manager_index_html_only_references_existing_scripts(self) -> None:
        html = (ROOT / "ui" / "manager" / "index.html").read_text(encoding="utf-8")
        scripts = re.findall(r'<script\s+src="([^"]+)"', html)
        self.assertGreaterEqual(len(scripts), 1)

        missing = [script for script in scripts if not (ROOT / "ui" / "manager" / script).exists()]
        self.assertEqual([], missing)

    def test_manager_dashboard_uses_dedicated_manager_endpoint(self) -> None:
        config_js = (ROOT / "ui" / "manager" / "main" / "config.js").read_text(encoding="utf-8")
        dashboard_js = (ROOT / "ui" / "manager" / "dashboard.js").read_text(encoding="utf-8")

        self.assertIn("MANAGER_DASHBOARD_API_URL", config_js)
        self.assertIn('DEFAULT_MANAGER_API_PORT = "8011"', config_js)
        self.assertIn("/api/manager/dashboard", config_js)
        self.assertIn("getManagerDashboardApiUrl()", dashboard_js)
        self.assertIn("isValidDateKeyForManagerRequest", dashboard_js)
        self.assertIn("isValidHourForManagerRequest", dashboard_js)
        self.assertNotIn("fetch(CONFIG.DB_API_URL)", dashboard_js)


if __name__ == "__main__":
    unittest.main()
