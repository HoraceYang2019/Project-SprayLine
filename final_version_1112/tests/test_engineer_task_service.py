from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
for rel in ("api", "services", "database"):
    path = str(ROOT / rel)
    if path not in sys.path:
        sys.path.insert(0, path)

from engineer_task_models import EngineerTaskCreateRequest  # noqa: E402
from engineer_task_service import (  # noqa: E402
    EngineerTaskDeliveryError,
    create_and_send_engineer_task,
    sync_engineer_task_ack,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeClient:
    post_payload = None
    post_response = FakeResponse({"success": True})
    get_response = FakeResponse({"acknowledged": False})

    def __init__(self, **_kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, _url, json):
        type(self).post_payload = json
        return type(self).post_response

    async def get(self, _url, params):
        type(self).get_params = params
        return type(self).get_response


class FakeRepository:
    def __init__(self):
        now = datetime.now(timezone.utc)
        self.task = {
            "task_id": uuid4(),
            "station_id": "station_1",
            "station_name": "第一站",
            "process_name": "底漆",
            "batch_id": None,
            "batch_label": "全部批號",
            "data_date": "2026-07-17",
            "data_hour": "08:00-09:00",
            "level": "warning",
            "issue": "流量偏低",
            "recommendation": "檢查噴嘴",
            "engineer_name": "Process Engineer",
            "engineer_email": "engineer@example.com",
            "delivery_status": "pending",
            "delivery_error": None,
            "sent_at": None,
            "acknowledged_at": None,
            "acknowledged_by": None,
            "acknowledged_email": None,
            "ack_source": None,
            "ack_note": None,
            "source_alert_event_id": None,
            "created_at": now,
            "updated_at": now,
        }

    def create_engineer_task(self, _conn, _payload):
        return dict(self.task)

    def mark_engineer_task_sent(self, _conn, _task_id, response):
        self.task.update(delivery_status="sent", apps_script_response_json=response)
        return dict(self.task)

    def mark_engineer_task_failed(self, _conn, _task_id, error, response=None):
        self.task.update(delivery_status="failed", delivery_error=error, apps_script_response_json=response)
        return dict(self.task)

    def get_engineer_task(self, _conn, _task_id):
        return dict(self.task)

    def acknowledge_engineer_task(self, _conn, _task_id, **values):
        self.task.update(
            delivery_status="acknowledged",
            acknowledged_at=values["acknowledged_at"],
            acknowledged_by=values["acknowledged_by"],
            acknowledged_email=values["acknowledged_email"],
            ack_source=values["ack_source"],
            ack_note=values["ack_note"],
        )
        return dict(self.task)


def build_request():
    return EngineerTaskCreateRequest.model_validate(
        {
            "stationId": "station_1",
            "stationName": "第一站",
            "processName": "底漆",
            "dataDate": "2026-07-17",
            "dataHour": "08:00-09:00",
            "issue": "流量偏低",
            "recommendation": "檢查噴嘴",
            "engineerName": "Process Engineer",
            "engineerEmail": "engineer@example.com",
        }
    )


class EngineerTaskServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_create_uses_database_task_id_and_marks_sent(self):
        repository = FakeRepository()
        FakeClient.post_response = FakeResponse({"success": True, "sentAt": "2026-07-17T01:00:00Z"})

        result = await create_and_send_engineer_task(
            SimpleNamespace(),
            build_request(),
            apps_script_url="https://example.invalid/exec",
            client_factory=FakeClient,
            repository=repository,
        )

        self.assertEqual("sent", result["delivery_status"])
        self.assertEqual(str(repository.task["task_id"]), FakeClient.post_payload["taskId"])

    async def test_create_marks_failed_when_apps_script_rejects(self):
        repository = FakeRepository()
        FakeClient.post_response = FakeResponse({"success": False, "error": "Mail quota exceeded"})

        with self.assertRaises(EngineerTaskDeliveryError):
            await create_and_send_engineer_task(
                SimpleNamespace(),
                build_request(),
                apps_script_url="https://example.invalid/exec",
                client_factory=FakeClient,
                repository=repository,
            )

        self.assertEqual("failed", repository.task["delivery_status"])
        self.assertIn("Mail quota exceeded", repository.task["delivery_error"])

    async def test_sync_ack_updates_database_state(self):
        repository = FakeRepository()
        repository.task["delivery_status"] = "sent"
        FakeClient.get_response = FakeResponse(
            {
                "acknowledged": True,
                "ackAt": "2026-07-17T01:05:00Z",
                "ackBy": "Engineer A",
                "ackEmail": "engineer@example.com",
                "source": "apps_script",
            }
        )

        result = await sync_engineer_task_ack(
            SimpleNamespace(),
            str(repository.task["task_id"]),
            apps_script_url="https://example.invalid/exec",
            client_factory=FakeClient,
            repository=repository,
        )

        self.assertEqual("acknowledged", result["delivery_status"])
        self.assertEqual("Engineer A", result["acknowledged_by"])


if __name__ == "__main__":
    unittest.main()

