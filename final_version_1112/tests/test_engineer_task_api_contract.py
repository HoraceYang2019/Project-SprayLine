from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for rel in ("api", "services", "database"):
    path = str(ROOT / rel)
    if path not in sys.path:
        sys.path.insert(0, path)

from api_server import app  # noqa: E402
from engineer_task_models import EngineerTaskCreateRequest  # noqa: E402


class EngineerTaskApiContractTest(unittest.TestCase):
    def test_create_request_rejects_missing_email(self):
        with self.assertRaises(ValueError):
            EngineerTaskCreateRequest.model_validate(
                {
                    "stationId": "station_1",
                    "stationName": "第一站",
                    "processName": "底漆",
                    "issue": "流量偏低",
                    "recommendation": "檢查噴嘴",
                }
            )

    def test_openapi_has_non_empty_engineer_task_contracts(self):
        schema = app.openapi()
        paths = schema["paths"]
        self.assertIn("/api/manager/engineer-tasks", paths)
        self.assertIn("/api/manager/engineer-tasks/{task_id}/sync-ack", paths)
        request_schema = paths["/api/manager/engineer-tasks"]["post"]["requestBody"]
        self.assertTrue(request_schema["content"]["application/json"]["schema"])


if __name__ == "__main__":
    unittest.main()
