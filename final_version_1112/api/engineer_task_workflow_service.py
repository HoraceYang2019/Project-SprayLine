"""Transactional Phase 2 engineer-task workflow and secure token handling."""

from __future__ import annotations

import hashlib
import io
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote
from uuid import UUID, uuid4

import httpx
from PIL import Image, UnidentifiedImageError


class WorkflowError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def hash_access_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_token() -> tuple[str, str]:
    plain = secrets.token_urlsafe(32)
    return plain, hash_access_token(plain)


def _base_url() -> str:
    value = os.getenv("ENGINEER_TASK_BASE_URL", "").strip().rstrip("/")
    if not value:
        raise WorkflowError("ENGINEER_TASK_BASE_URL is not configured", 503)
    if "localhost" in value.lower() or "127.0.0.1" in value:
        raise WorkflowError("ENGINEER_TASK_BASE_URL must be a LAN address, not localhost", 503)
    return value


def _app_script_url() -> str:
    value = os.getenv("ENGINEER_TASK_APP_SCRIPT_URL", "").strip()
    if not value:
        raise WorkflowError("ENGINEER_TASK_APP_SCRIPT_URL is not configured", 503)
    return value


def notification_fingerprint(station_id: str, cause_id: str | None, issue_type: str | None,
                             batch_id: str | None, data_date: Any) -> str:
    issue = (cause_id or issue_type or "unknown").strip().lower().replace(" ", "_")
    anchor = batch_id or str(data_date or "unknown-date")
    return f"{station_id.strip().lower()}|{issue}|{anchor.strip().lower()}"


def _mail_payload(task, assignee, plain_token, purpose="initial_assignment", base_url=None):
    base = (base_url or _base_url()).rstrip("/")
    task_url = f"{base}/engineer-task.html?token={quote(plain_token)}"
    return {
        "action": "send_task",
        "taskId": str(task["task_id"]),
        "engineerName": assignee["engineer_name_snapshot"],
        "engineerEmail": assignee["engineer_email_snapshot"],
        "title": f"{task['station_name']} / {task['process_name']}: {task['issue']}",
        "messageText": task["recommendation"],
        "ackUrl": f"{task_url}&action=ack",
        "taskUrl": task_url,
        "mailPurpose": purpose,
    }


async def _send_mail(url, payload, client_factory=httpx.AsyncClient):
    async with client_factory(timeout=httpx.Timeout(15.0, connect=5.0), follow_redirects=True) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        body = response.json()
    if body.get("success") is not True:
        raise WorkflowError(str(body.get("error") or "Apps Script did not confirm delivery"), 502)


async def create_v2_task(conn, request, *, repository=None, client_factory=httpx.AsyncClient,
                         apps_script_url=None, base_url=None):
    if repository is None:
        import db_engineer_task_workflow as repository
    task_data = request.model_dump(mode="python", by_alias=False)
    task_data["notification_fingerprint"] = notification_fingerprint(
        request.station_id, request.cause_id, request.issue_type, request.batch_id, request.data_date
    )
    prepared, plain_by_email = [], {}
    expires = datetime.now(timezone.utc) + timedelta(days=3650)
    for item in task_data.pop("assignees"):
        plain, digest = _new_token()
        item.update(token_hash=digest, token_expires_at=expires)
        prepared.append(item)
        plain_by_email[item["engineer_email"]] = plain
    try:
        task, assignees = repository.create_task_with_assignees(conn, task_data, prepared)
        repository.record_task_created_decision(conn, task)
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    url = (apps_script_url if apps_script_url is not None else os.getenv("ENGINEER_TASK_APP_SCRIPT_URL", "")).strip()
    try:
        for assignee in assignees:
            try:
                repository.append_event(conn, task["task_id"], "mail_send_requested", assignee_id=assignee["assignee_id"])
                payload = _mail_payload(task, assignee, plain_by_email[assignee["engineer_email_snapshot"]], base_url=base_url)
                await _send_mail(url, payload, client_factory)
                repository.update_assignee_delivery(conn, assignee["assignee_id"], "sent")
                repository.append_event(conn, task["task_id"], "mail_sent", assignee_id=assignee["assignee_id"])
            except Exception as exc:
                # Never include payload or URL because both contain the plain token.
                repository.update_assignee_delivery(conn, assignee["assignee_id"], "failed", error=str(exc)[:1000])
                repository.append_event(conn, task["task_id"], "mail_failed", assignee_id=assignee["assignee_id"], message="Apps Script delivery failed")
            repository.refresh_delivery_summary(conn, task["task_id"])
            conn.commit()
    finally:
        plain_by_email.clear()
    return repository.get_task_detail(conn, task["task_id"])


def authorize_token(conn, token: str, *, repository=None):
    if repository is None:
        import db_engineer_task_workflow as repository
    if not token or len(token) < 32:
        raise WorkflowError("Invalid access token", 403)
    assignee = repository.find_assignee_by_token_hash(conn, hash_access_token(token))
    if not assignee or not assignee.get("is_active") or assignee.get("token_revoked_at"):
        raise WorkflowError("Token is invalid or revoked", 403)
    now = datetime.now(timezone.utc)
    expires = assignee.get("token_expires_at")
    if expires and expires < now:
        raise WorkflowError("Token has expired", 403)
    completed = assignee.get("completed_at")
    if completed and completed + timedelta(days=7) < now:
        raise WorkflowError("Completed task access has expired", 403)
    return assignee


def get_token_access(conn, token, repository=None):
    if repository is None:
        import db_engineer_task_workflow as repository
    assignee = authorize_token(conn, token, repository=repository)
    return {
        "task": repository.get_task_detail(conn, assignee["task_id"]),
        "currentAssignee": assignee,
        "timeline": repository.get_timeline(conn, assignee["task_id"]),
    }


def direct_ack(conn, token, note=None, repository=None):
    if repository is None:
        import db_engineer_task_workflow as repository
    assignee = authorize_token(conn, token, repository=repository)
    try:
        result = repository.acknowledge_assignee(conn, assignee["assignee_id"], note)
        conn.commit()
    except Exception:
        conn.rollback(); raise
    return repository.get_task_detail(conn, assignee["task_id"]), result[0]


def start_processing(conn, token, repository=None):
    if repository is None:
        import db_engineer_task_workflow as repository
    assignee = authorize_token(conn, token, repository=repository)
    if not assignee.get("acknowledged_at"):
        raise WorkflowError("ACK is required before starting", 409)
    row = repository.start_processing(conn, assignee["task_id"], assignee["assignee_id"])
    if not row:
        current = repository.get_task_detail(conn, assignee["task_id"])
        conn.rollback()
        if current and current.get("workflow_status") == "in_progress":
            return current, assignee
        raise WorkflowError("Task cannot enter in_progress from its current state", 409)
    conn.commit()
    return repository.get_task_detail(conn, assignee["task_id"]), assignee


def add_report(conn, token, request, repository=None):
    if repository is None:
        import db_engineer_task_workflow as repository
    assignee = authorize_token(conn, token, repository=repository)
    status = assignee["workflow_status"]
    if status == "completed" and not (assignee.get("supplementation_open") and assignee.get("supplementation_allowed")):
        raise WorkflowError("Completed task is read-only", 409)
    report_type = request.report_type
    if status == "completion_submitted":
        report_type = "post_submission_addendum"
    elif status == "completed":
        report_type = "post_completion_supplement"
    values = request.model_dump(mode="python")
    try:
        row = repository.create_report(conn, assignee["task_id"], assignee["assignee_id"], values, report_type)
        conn.commit()
        return row
    except Exception:
        conn.rollback(); raise


def submit_completion(conn, token, note=None, repository=None):
    if repository is None:
        import db_engineer_task_workflow as repository
    assignee = authorize_token(conn, token, repository=repository)
    row = repository.submit_completion(conn, assignee["task_id"], assignee["assignee_id"], note)
    if not row:
        conn.rollback()
        raise WorkflowError("Only the primary may submit after all required participants ACK", 409)
    conn.commit()
    return repository.get_task_detail(conn, assignee["task_id"]), assignee


ALLOWED_IMAGE_FORMATS = {"JPEG": ("image/jpeg", ".jpg"), "PNG": ("image/png", ".png"), "WEBP": ("image/webp", ".webp")}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def validate_image(content: bytes) -> tuple[str, str]:
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise WorkflowError("Image must be between 1 byte and 5 MB", 413)
    try:
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
            result = ALLOWED_IMAGE_FORMATS.get(image.format or "")
    except (UnidentifiedImageError, OSError) as exc:
        raise WorkflowError("File is not a valid JPG, PNG or WEBP image", 415) from exc
    if not result:
        raise WorkflowError("Unsupported image format", 415)
    return result


def store_attachment(conn, token, report_id, filename, content, repository=None, root=None):
    if repository is None:
        import db_engineer_task_workflow as repository
    assignee = authorize_token(conn, token, repository=repository)
    report = next((r for r in repository.get_reports(conn, assignee["task_id"]) if str(r["report_id"]) == str(report_id)), None)
    if not report:
        raise WorkflowError("Report not found for this task", 404)
    if len(repository.get_attachments(conn, assignee["task_id"])) >= 30:
        raise WorkflowError("Task attachment limit is 30", 409)
    if repository.count_report_attachments(conn, report_id) >= 5:
        raise WorkflowError("Report attachment limit is 5", 409)
    mime, suffix = validate_image(content)
    attachment_id = uuid4()
    now = datetime.now(timezone.utc)
    relative = Path(f"{now.year:04d}") / f"{now.month:02d}" / str(assignee["task_id"]) / f"{attachment_id}{suffix}"
    root_path = Path(root or os.getenv("ENGINEER_TASK_ATTACHMENT_ROOT", "")).resolve()
    if not str(root_path) or str(root_path) == str(Path(".").resolve()):
        raise WorkflowError("ENGINEER_TASK_ATTACHMENT_ROOT is not configured", 503)
    final_path = root_path / relative
    temp_path = final_path.with_suffix(final_path.suffix + ".tmp")
    final_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_bytes(content)
    values = {"attachment_id": attachment_id, "task_id": assignee["task_id"], "report_id": report_id,
              "assignee_id": assignee["assignee_id"], "original_filename": Path(filename or "image").name,
              "stored_filename": final_path.name, "relative_path": relative.as_posix(), "mime_type": mime,
              "size_bytes": len(content), "sha256_hex": hashlib.sha256(content).hexdigest()}
    try:
        row = repository.create_attachment_metadata(conn, values)
        repository.append_event(conn, assignee["task_id"], "attachment_uploaded", assignee_id=assignee["assignee_id"], event_data={"attachmentId": str(attachment_id)})
        temp_path.replace(final_path)
        conn.commit()
        return row
    except Exception:
        conn.rollback()
        temp_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        raise


async def resend_assignees(conn, task_id, assignee_ids, *, repository=None,
                           client_factory=httpx.AsyncClient, apps_script_url=None, base_url=None,
                           purpose="resend"):
    if repository is None:
        import db_engineer_task_workflow as repository
    task = repository.get_task(conn, task_id)
    if not task:
        raise WorkflowError("Engineer task not found", 404)
    url = (apps_script_url if apps_script_url is not None else _app_script_url()).strip()
    expires = datetime.now(timezone.utc) + timedelta(days=3650)
    results = []
    for assignee_id in assignee_ids:
        assignee = repository.get_assignee(conn, assignee_id)
        if not assignee or str(assignee["task_id"]) != str(task_id) or not assignee["is_active"]:
            raise WorkflowError("Active assignee not found for task", 404)
        plain, digest = _new_token()
        repository.rotate_assignee_token(conn, assignee_id, digest, expires)
        try:
            await _send_mail(url, _mail_payload(task, assignee, plain, purpose, base_url=base_url), client_factory)
            row = repository.update_assignee_delivery(conn, assignee_id, "sent", resend=True)
            repository.append_event(conn, task_id, "mail_resent", assignee_id=assignee_id)
        except Exception as exc:
            row = repository.update_assignee_delivery(conn, assignee_id, "failed", error=str(exc)[:1000], resend=True)
            repository.append_event(conn, task_id, "mail_failed", assignee_id=assignee_id, message="Manual resend failed")
        finally:
            plain = ""
        results.append(row)
    repository.refresh_delivery_summary(conn, task_id)
    conn.commit()
    return repository.get_task_detail(conn, task_id), results


async def update_assignments(conn, task_id, request, repository=None, *,
                             client_factory=httpx.AsyncClient, apps_script_url=None, base_url=None):
    if repository is None:
        import db_engineer_task_workflow as repository
    task = repository.get_task(conn, task_id)
    if not task:
        raise WorkflowError("Engineer task not found", 404)
    if task["workflow_status"] == "completion_submitted":
        raise WorkflowError("Assignments are locked after completion submit", 409)
    expires = datetime.now(timezone.utc) + timedelta(days=3650)
    prepared, plain_by_email = [], {}
    old_emails = {
        row["engineer_email_snapshot"].lower()
        for row in repository.get_assignees(conn, task_id, active_only=True)
    }
    for item in request.assignees:
        data = item.model_dump(mode="python")
        plain, digest = _new_token()
        data.update(token_hash=digest, token_expires_at=expires)
        prepared.append(data)
        plain_by_email[data["engineer_email"]] = plain
    try:
        active, removed = repository.replace_active_assignees(conn, task_id, prepared, task["current_assignment_round"])
        for item in removed:
            repository.append_event(conn, task_id, "assignee_removed", assignee_id=item["assignee_id"])
        conn.commit()
    except Exception:
        conn.rollback(); raise
    new_assignees = [
        row for row in active
        if row["engineer_email_snapshot"].lower() not in old_emails
    ]
    if new_assignees:
        url = (apps_script_url if apps_script_url is not None else os.getenv("ENGINEER_TASK_APP_SCRIPT_URL", "")).strip()
        task = repository.get_task(conn, task_id)
        for assignee in new_assignees:
            try:
                await _send_mail(
                    url,
                    _mail_payload(task, assignee, plain_by_email[assignee["engineer_email_snapshot"]], base_url=base_url),
                    client_factory,
                )
                repository.update_assignee_delivery(conn, assignee["assignee_id"], "sent")
                repository.append_event(conn, task_id, "assignee_added", assignee_id=assignee["assignee_id"])
                repository.append_event(conn, task_id, "mail_sent", assignee_id=assignee["assignee_id"])
            except Exception as exc:
                repository.update_assignee_delivery(conn, assignee["assignee_id"], "failed", error=str(exc)[:1000])
                repository.append_event(conn, task_id, "mail_failed", assignee_id=assignee["assignee_id"], message="New assignee delivery failed")
        repository.refresh_delivery_summary(conn, task_id)
        conn.commit()
    plain_by_email.clear()
    return repository.get_task_detail(conn, task_id), active


def review_task(conn, task_id, request, repository=None):
    if repository is None:
        import db_engineer_task_workflow as repository
    if not set(request.applicable_checks).issubset(set(request.confirmed_checks)):
        raise WorkflowError("All applicable checks must be confirmed", 422)
    if request.action == "reject" and (not request.reason or not request.notify_assignee_ids):
        raise WorkflowError("Reject requires a reason and at least one recipient", 422)
    row = repository.manager_review(conn, task_id, request.action, request.manager_name,
                                    request.reason, request.confirmed_checks)
    if not row:
        conn.rollback(); raise WorkflowError("Task is not awaiting Manager review", 409)
    conn.commit()
    return repository.get_task_detail(conn, task_id)


def reopen_existing_task(conn, task_id, request, repository=None):
    if repository is None:
        import db_engineer_task_workflow as repository
    old = repository.get_task(conn, task_id)
    if not old:
        raise WorkflowError("Engineer task not found", 404)
    if request.batch_id and old.get("batch_id") and request.batch_id != old["batch_id"]:
        raise WorkflowError("Different batch requires a new task", 409)
    task = repository.reopen_task(conn, task_id, request.manager_name, request.reason, request.batch_id)
    expires = datetime.now(timezone.utc) + timedelta(days=3650)
    prepared = []
    for item in request.assignees:
        data = item.model_dump(mode="python")
        _plain, digest = _new_token()
        data.update(token_hash=digest, token_expires_at=expires)
        prepared.append(data)
    repository.replace_active_assignees(conn, task_id, prepared, task["current_assignment_round"])
    conn.commit()
    return repository.get_task_detail(conn, task_id)


def evaluate_notification(conn, request, repository=None):
    if repository is None:
        import db_engineer_task_workflow as repository
    values = request.model_dump(mode="python")
    fingerprint = notification_fingerprint(request.station_id, request.cause_id, request.issue_type,
                                           request.batch_id, request.data_date)
    values["notification_fingerprint"] = fingerprint
    same_source = repository.find_source_decision(conn, request.source_alert_event_id)
    if same_source:
        return same_source
    current = repository.find_cooldown_decision(conn, fingerprint)
    rank = {"normal": 0, "warning": 1, "fault": 2, "critical": 3}
    if current and rank.get(request.risk_level.lower(), 1) <= rank.get(str(current["risk_level"]).lower(), 1):
        row = repository.increment_suppressed_decision(conn, current["decision_id"])
    else:
        values["decision_type"] = "email_task_created" if request.email_requested else "dashboard_only"
        values["decision_reason"] = "severity escalation" if current else "notification policy evaluation"
        row = repository.create_notification_decision(conn, values)
    conn.commit()
    return row
