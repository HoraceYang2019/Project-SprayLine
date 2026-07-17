from __future__ import annotations

import io
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
for rel in ("api", "database", "services"):
    sys.path.insert(0, str(ROOT / rel))

from engineer_task_models import (  # noqa: E402
    EngineerTaskAssignmentUpdateRequest, EngineerTaskCreateRequest,
    EngineerTaskCreateV2Request, EngineerTaskReopenRequest,
)
import engineer_task_workflow_router as workflow_router  # noqa: E402
from engineer_task_workflow_service import (  # noqa: E402
    WorkflowError, authorize_token, create_v2_task, hash_access_token, notification_fingerprint,
    start_processing, validate_image,
)


def assignee(name="A", email="a@example.com", primary=True, required=True):
    return {"engineerName": name, "engineerEmail": email, "isPrimary": primary, "isRequiredParticipant": required}


class TokenRepository:
    def __init__(self, token, **overrides):
        now = datetime.now(timezone.utc)
        self.digest = hash_access_token(token)
        self.row = {"assignee_id": uuid4(), "task_id": uuid4(), "is_active": True,
                    "token_revoked_at": None, "token_expires_at": now + timedelta(days=1),
                    "completed_at": None, **overrides}
        self.seen_hash = None

    def find_assignee_by_token_hash(self, _conn, digest):
        self.seen_hash = digest
        return self.row if digest == self.digest else None


class RepeatedStartRepository(TokenRepository):
    def start_processing(self, _conn, _task_id, _assignee_id): return None
    def get_task_detail(self, _conn, task_id):
        return {"task_id": task_id, "workflow_status": "in_progress"}


class FakeConnection:
    def __init__(self): self.commits = 0; self.rollbacks = 0
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1


class DeliveryClient:
    payloads = []
    def __init__(self, **_kwargs): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *_args): return None
    async def post(self, _url, json):
        type(self).payloads.append(json)
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"success": True})


class CreateRepository:
    def __init__(self): self.prepared = []; self.events = []
    def create_task_with_assignees(self, _conn, task, assignees):
        self.prepared = assignees
        task_row = {"task_id":uuid4(),"source_alert_event_id":None,"station_id":task["station_id"],"station_name":task["station_name"],"process_name":task["process_name"],"batch_id":None,"data_date":None,"data_hour_index":None,"level":"warning","issue":task["issue"],"recommendation":task["recommendation"],"notification_fingerprint":task["notification_fingerprint"]}
        rows=[]
        for item in assignees:
            rows.append({"assignee_id":uuid4(),"engineer_name_snapshot":item["engineer_name"],"engineer_email_snapshot":item["engineer_email"]})
        self.task, self.assignees = task_row, rows
        return task_row, rows
    def record_task_created_decision(self, _conn, _task): return {}
    def append_event(self, _conn, _task_id, event_type, **kwargs): self.events.append((event_type, kwargs)); return {}
    def update_assignee_delivery(self, _conn, _id, status, **_kwargs): return {"delivery_status":status}
    def refresh_delivery_summary(self, _conn, _task_id): return self.task
    def get_task_detail(self, _conn, _task_id): return self.task


class EngineerWorkflowTest(unittest.TestCase):
    def test_legacy_single_engineer_request_remains_valid(self):
        model = EngineerTaskCreateRequest.model_validate({"stationId":"Station_1","stationName":"S1","processName":"Primer","issue":"x","recommendation":"y","engineerEmail":"a@example.com"})
        self.assertEqual("a@example.com", model.engineer_email)

    def test_v2_requires_exactly_one_primary_and_primary_required(self):
        base = {"stationId":"Station_1","stationName":"S1","processName":"Primer","issue":"x","recommendation":"y"}
        with self.assertRaises(ValueError):
            EngineerTaskCreateV2Request.model_validate({**base, "assignees":[assignee(primary=False)]})
        with self.assertRaises(ValueError):
            EngineerTaskCreateV2Request.model_validate({**base, "assignees":[assignee(required=False)]})
        valid = EngineerTaskCreateV2Request.model_validate({**base, "assignees":[assignee(),assignee("B","b@example.com",False,True)]})
        self.assertEqual(2, len(valid.assignees))

    def test_assignment_update_applies_same_primary_rule(self):
        with self.assertRaises(ValueError):
            EngineerTaskAssignmentUpdateRequest.model_validate({"assignees":[assignee(primary=False)]})

    def test_token_lookup_only_receives_sha256(self):
        token = "x" * 43
        repository = TokenRepository(token)
        result = authorize_token(SimpleNamespace(), token, repository=repository)
        self.assertEqual(repository.row, result)
        self.assertEqual(64, len(repository.seen_hash))
        self.assertNotEqual(token, repository.seen_hash)

    def test_invalid_revoked_and_expired_token_are_forbidden(self):
        token = "y" * 43
        with self.assertRaises(WorkflowError): authorize_token(None, "bad", repository=TokenRepository(token))
        with self.assertRaises(WorkflowError): authorize_token(None, token, repository=TokenRepository(token, token_revoked_at=datetime.now(timezone.utc)))
        with self.assertRaises(WorkflowError): authorize_token(None, token, repository=TokenRepository(token, token_expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)))

    def test_completed_token_expires_after_seven_days(self):
        token = "z" * 43
        repository = TokenRepository(token, completed_at=datetime.now(timezone.utc)-timedelta(days=8), token_expires_at=datetime.now(timezone.utc)+timedelta(days=1))
        with self.assertRaises(WorkflowError): authorize_token(None, token, repository=repository)

    def test_repeated_start_is_idempotent_without_new_transition(self):
        token = "s" * 43
        repository = RepeatedStartRepository(token, acknowledged_at=datetime.now(timezone.utc))
        connection = FakeConnection()
        task, current = start_processing(connection, token, repository=repository)
        self.assertEqual("in_progress", task["workflow_status"])
        self.assertEqual(repository.row, current)
        self.assertEqual(1, connection.rollbacks)
        self.assertEqual(0, connection.commits)

    def test_fingerprint_uses_batch_or_date(self):
        self.assertEqual("station_1|cause-1|batch-9", notification_fingerprint("Station_1","CAUSE-1",None,"BATCH-9",None))
        self.assertEqual("station_1|low_flow|2026-07-17", notification_fingerprint("Station_1",None,"Low Flow",None,"2026-07-17"))

    def test_image_is_actually_decoded(self):
        stream = io.BytesIO(); Image.new("RGB", (2, 2), "red").save(stream, format="PNG")
        self.assertEqual(("image/png", ".png"), validate_image(stream.getvalue()))
        with self.assertRaises(WorkflowError): validate_image(b"not an image")
        with self.assertRaises(WorkflowError): validate_image(b"x" * (5 * 1024 * 1024 + 1))


class EngineerWorkflowAsyncTest(unittest.IsolatedAsyncioTestCase):
    async def test_v2_database_stores_hash_and_mail_gets_ephemeral_url(self):
        request = EngineerTaskCreateV2Request.model_validate({"stationId":"Station_1","stationName":"S1","processName":"Primer","issue":"x","recommendation":"y","assignees":[assignee()]})
        repository = CreateRepository(); connection = FakeConnection(); DeliveryClient.payloads = []
        await create_v2_task(connection, request, repository=repository, client_factory=DeliveryClient,
                             apps_script_url="https://example.invalid/exec", base_url="http://192.168.1.20:8012")
        stored = repository.prepared[0]
        self.assertEqual(64, len(stored["token_hash"]))
        self.assertNotIn("token", repository.task)
        self.assertIn("token=", DeliveryClient.payloads[0]["taskUrl"])
        self.assertNotIn("token", str(repository.events).lower())
        self.assertIn("mail_send_requested", [item[0] for item in repository.events])

    async def test_reopen_sends_fresh_links_to_active_assignees(self):
        task_id, active_id, removed_id = uuid4(), uuid4(), uuid4()
        request = EngineerTaskReopenRequest.model_validate({
            "batchId": "BATCH-1",
            "managerName": "Manager",
            "reason": "Issue recurred",
            "assignees": [assignee()],
        })
        reopened = {
            "assignees": [
                {"assignee_id": active_id, "is_active": True},
                {"assignee_id": removed_id, "is_active": False},
            ]
        }
        delivered = {"workflow_status": "unacknowledged", "delivery_summary_status": "sent"}
        connection = SimpleNamespace(close=Mock())
        resend = AsyncMock(return_value=(delivered, []))

        with (
            patch.object(workflow_router, "_connection", return_value=connection),
            patch.object(workflow_router, "reopen_existing_task", return_value=reopened),
            patch.object(workflow_router, "resend_assignees", resend),
        ):
            result = await workflow_router.ReopenTask(task_id, request)

        self.assertEqual(delivered, result)
        resend.assert_awaited_once_with(connection, task_id, [active_id], purpose="reopen")
        connection.close.assert_called_once_with()


if __name__ == "__main__": unittest.main()
