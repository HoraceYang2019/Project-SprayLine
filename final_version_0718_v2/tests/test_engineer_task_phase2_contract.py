from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for rel in ("api", "database", "services"):
    sys.path.insert(0, str(ROOT / rel))

from api_server import app  # noqa: E402


class Phase2ContractTest(unittest.TestCase):
    def test_required_routes_have_openapi_contracts(self):
        schema = app.openapi(); paths = schema["paths"]
        expected = {
            "/api/manager/station-engineer-assignments", "/api/manager/station-engineer-assignments/{assignment_id}",
            "/api/manager/notification-decisions", "/api/manager/notification-decisions/evaluate",
            "/api/manager/engineer-tasks/{task_id}/timeline", "/api/manager/engineer-tasks/{task_id}/resend",
            "/api/manager/engineer-tasks/{task_id}/assignees", "/api/manager/engineer-tasks/{task_id}/review",
            "/api/manager/engineer-tasks/{task_id}/reopen", "/api/manager/engineer-tasks/{task_id}/supplementation/open",
            "/api/manager/engineer-tasks/{task_id}/supplementation/close", "/api/engineer-task-access/task",
            "/api/engineer-task-access/ack", "/api/engineer-task-access/start", "/api/engineer-task-access/reports",
            "/api/engineer-task-access/completion-submit", "/api/engineer-task-access/attachments/{attachment_id}",
        }
        self.assertFalse(expected - paths.keys())
        for path in expected:
            for operation in paths[path].values():
                self.assertTrue(operation.get("responses"))
                successful = [response for code, response in operation["responses"].items() if code.startswith("2")]
                self.assertTrue(any(any(item.get("schema") for item in response.get("content", {}).values()) for response in successful))
                if operation.get("requestBody"):
                    self.assertTrue(operation["requestBody"]["content"])

    def test_phase1_routes_remain_present(self):
        paths = app.openapi()["paths"]
        self.assertIn("post", paths["/api/manager/engineer-tasks"])
        self.assertIn("get", paths["/api/manager/engineer-tasks"])
        self.assertIn("get", paths["/api/manager/engineer-tasks/{task_id}"])
        self.assertIn("post", paths["/api/manager/engineer-tasks/{task_id}/sync-ack"])

    def test_migration_is_additive_and_has_required_objects(self):
        sql = (ROOT / "database" / "migrate_extend_engineer_task_workflow.sql").read_text(encoding="utf-8").upper()
        self.assertNotIn("DROP TABLE", sql); self.assertNotIn("TRUNCATE", sql); self.assertNotIn("DELETE FROM", sql)
        for table in ("STATION_ENGINEER_ASSIGNMENT","ENGINEER_TASK_ASSIGNEE","ENGINEER_TASK_EVENT","NOTIFICATION_DECISION","ENGINEER_TASK_REPORT","ENGINEER_TASK_ATTACHMENT"):
            self.assertIn(f"CREATE TABLE IF NOT EXISTS PUBLIC.{table}", sql)
        self.assertIn("CREATE UNIQUE INDEX IF NOT EXISTS UQ_ENGINEER_TASK_PRIMARY_PER_ROUND", sql)
        self.assertIn("ALTER COLUMN EVENT_TIME SET DEFAULT CLOCK_TIMESTAMP()", sql)

    def test_timeline_repository_uses_wall_clock_event_time(self):
        source = (ROOT / "database" / "db_engineer_task_workflow.py").read_text(encoding="utf-8")
        self.assertIn("clock_timestamp()", source)
        self.assertIn("WHERE task_id=%s AND workflow_status='acknowledged' RETURNING *", source)

    def test_task_detail_exposes_workflow_audit_fields(self):
        properties = app.openapi()["components"]["schemas"]["EngineerTaskDetailResponse"]["properties"]
        expected = {
            "completionSubmittedAt", "completionSubmittedByAssigneeId", "completedAt", "completedBy",
            "reopenedCount", "supplementationReason", "supplementationOpenedAt", "supplementationOpenedBy",
            "supplementationClosedAt", "supplementationClosedBy", "supplementationConclusion",
        }
        self.assertFalse(expected - properties.keys())

    def test_new_ui_uses_direct_api_and_visibility_polling(self):
        history = (ROOT / "ui" / "manager" / "notification-history.js").read_text(encoding="utf-8")
        task = (ROOT / "ui" / "manager" / "engineer-task.js").read_text(encoding="utf-8")
        self.assertIn("120000", history); self.assertIn("document.hidden", history)
        self.assertNotIn("ack_status_jsonp", history + task); self.assertNotIn("ENGINEER_TASK_APP_SCRIPT_URL", history + task)
        page = (ROOT / "ui" / "manager" / "notification-history.html").read_text(encoding="utf-8")
        self.assertIn("通知決策", page); self.assertIn("工程師任務", page)

    def test_manager_review_controls_are_guarded_by_workflow_status(self):
        history = (ROOT / "ui" / "manager" / "notification-history.js").read_text(encoding="utf-8")
        task = (ROOT / "ui" / "manager" / "engineer-task.js").read_text(encoding="utf-8")
        self.assertIn('task.workflowStatus === "completion_submitted"', history)
        self.assertIn('dialog.dataset.workflowStatus=task.workflowStatus', history)
        self.assertIn('只有等待 Manager 驗收的任務才能執行驗收或退回', history)
        self.assertIn('dialog.querySelectorAll("[data-review]")', history)
        self.assertIn('task.workflowStatus!=="acknowledged"', task)


if __name__ == "__main__": unittest.main()
