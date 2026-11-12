"""Manager and token-scoped routes for the Phase 2 engineer-task workflow."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from engineer_task_models import (
    EngineerTaskAssignmentUpdateRequest, EngineerTaskAttachmentResponse,
    EngineerTaskCompletionSubmitRequest, EngineerTaskDetailResponse,
    EngineerTaskManagerReviewRequest, EngineerTaskReopenRequest,
    EngineerTaskReportCreateRequest, EngineerTaskReportResponse,
    EngineerTaskResendRequest, EngineerTaskSupplementationCloseRequest,
    EngineerTaskSupplementationOpenRequest, EngineerTaskTimelineResponse,
    EngineerTaskTokenAccessResponse, EngineerTaskTokenActionRequest,
    NotificationDecisionEvaluateRequest, NotificationDecisionListResponse,
    NotificationDecisionResponse, StationEngineerAssignmentCreateRequest,
    StationEngineerAssignmentResponse, StationEngineerAssignmentUpdateRequest,
)
from engineer_task_workflow_service import (
    WorkflowError, add_report, authorize_token, direct_ack, evaluate_notification,
    get_token_access, reopen_existing_task, resend_assignees, review_task,
    start_processing, store_attachment, submit_completion, update_assignments,
)


manager_workflow_router = APIRouter(prefix="/api/manager", tags=["Manager Engineer Workflow"])
token_access_router = APIRouter(prefix="/api/engineer-task-access", tags=["Engineer Task Access"])


def _connection():
    from db_connection import get_connection
    try:
        return get_connection()
    except Exception as exc:
        raise HTTPException(500, f"Engineer workflow DB connection failed: {exc}") from exc


def _raise(exc: Exception):
    if isinstance(exc, WorkflowError):
        raise HTTPException(exc.status_code, str(exc)) from exc
    raise exc


def _bearer(authorization: str | None, token: str | None) -> str:
    if token:
        return token
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    raise HTTPException(403, "Access token is required")


@manager_workflow_router.get("/station-engineer-assignments", response_model=list[StationEngineerAssignmentResponse])
def ListStationAssignments(station_id: str | None = None, active_only: bool = True):
    from db_engineer_task_workflow import list_station_assignments
    conn = _connection()
    try: return list_station_assignments(conn, station_id, active_only)
    finally: conn.close()


@manager_workflow_router.post("/station-engineer-assignments", response_model=StationEngineerAssignmentResponse, status_code=201)
def CreateStationAssignment(request: StationEngineerAssignmentCreateRequest):
    from db_engineer_task_workflow import create_station_assignment
    conn = _connection()
    try:
        row = create_station_assignment(conn, request.model_dump(mode="python")); conn.commit(); return row
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


@manager_workflow_router.patch("/station-engineer-assignments/{assignment_id}", response_model=StationEngineerAssignmentResponse)
def UpdateStationAssignment(assignment_id: UUID, request: StationEngineerAssignmentUpdateRequest):
    from db_engineer_task_workflow import update_station_assignment
    conn = _connection()
    try:
        row = update_station_assignment(conn, assignment_id, request.model_dump(exclude_none=True))
        if not row: raise HTTPException(404, "Station assignment not found")
        conn.commit(); return row
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


@manager_workflow_router.get("/notification-decisions", response_model=NotificationDecisionListResponse)
def ListNotificationDecisions(date_from: date | None = None, station_id: str | None = None,
                              decision_type: str | None = None, limit: int = Query(50, ge=1, le=500),
                              offset: int = Query(0, ge=0)):
    from db_engineer_task_workflow import list_notification_decisions
    conn = _connection()
    try:
        rows, total = list_notification_decisions(conn, locals(), limit, offset)
        return {"items": rows, "count": len(rows), "total": total}
    finally: conn.close()


@manager_workflow_router.post("/notification-decisions/evaluate", response_model=NotificationDecisionResponse)
def EvaluateNotificationDecision(request: NotificationDecisionEvaluateRequest):
    conn = _connection()
    try:
        return evaluate_notification(conn, request)
    except Exception as exc: _raise(exc)
    finally: conn.close()


@manager_workflow_router.get("/engineer-tasks/{task_id}/timeline", response_model=EngineerTaskTimelineResponse)
def GetTaskTimeline(task_id: UUID):
    from db_engineer_task_workflow import get_task, get_timeline
    conn = _connection()
    try:
        if not get_task(conn, task_id): raise HTTPException(404, "Engineer task not found")
        items = get_timeline(conn, task_id)
        return {"taskId": task_id, "items": items, "count": len(items)}
    finally: conn.close()


@manager_workflow_router.post("/engineer-tasks/{task_id}/resend", response_model=EngineerTaskDetailResponse)
async def ResendTask(task_id: UUID, request: EngineerTaskResendRequest):
    if not request.warning_confirmed:
        raise HTTPException(422, "warningConfirmed must be true")
    conn = _connection()
    try:
        task, _ = await resend_assignees(conn, task_id, request.assignee_ids)
        return task
    except Exception as exc: _raise(exc)
    finally: conn.close()


@manager_workflow_router.patch("/engineer-tasks/{task_id}/assignees", response_model=EngineerTaskDetailResponse)
async def UpdateTaskAssignments(task_id: UUID, request: EngineerTaskAssignmentUpdateRequest):
    conn = _connection()
    try:
        task, _ = await update_assignments(conn, task_id, request); return task
    except Exception as exc: _raise(exc)
    finally: conn.close()


@manager_workflow_router.post("/engineer-tasks/{task_id}/review", response_model=EngineerTaskDetailResponse)
async def ReviewTask(task_id: UUID, request: EngineerTaskManagerReviewRequest):
    conn = _connection()
    try:
        task = review_task(conn, task_id, request)
        if request.action == "reject":
            task, _ = await resend_assignees(conn, task_id, request.notify_assignee_ids, purpose="manager_rejection")
        return task
    except Exception as exc: _raise(exc)
    finally: conn.close()


@manager_workflow_router.post("/engineer-tasks/{task_id}/reopen", response_model=EngineerTaskDetailResponse)
async def ReopenTask(task_id: UUID, request: EngineerTaskReopenRequest):
    conn = _connection()
    try:
        task = reopen_existing_task(conn, task_id, request)
        active_assignee_ids = [
            assignee["assignee_id"]
            for assignee in task.get("assignees", [])
            if assignee.get("is_active")
        ]
        if not active_assignee_ids:
            raise WorkflowError("Reopened task has no active assignee", 409)
        task, _ = await resend_assignees(conn, task_id, active_assignee_ids, purpose="reopen")
        return task
    except Exception as exc: _raise(exc)
    finally: conn.close()


@manager_workflow_router.post("/engineer-tasks/{task_id}/supplementation/open", response_model=EngineerTaskDetailResponse)
async def OpenSupplementation(task_id: UUID, request: EngineerTaskSupplementationOpenRequest):
    from db_engineer_task_workflow import get_task_detail, open_supplementation
    conn = _connection()
    try:
        row = open_supplementation(conn, task_id, request.manager_name, request.reason, request.assignee_ids)
        if not row: raise WorkflowError("Only a completed task may open supplementation", 409)
        conn.commit()
        task, _ = await resend_assignees(conn, task_id, request.assignee_ids, purpose="supplementation")
        return task
    except Exception as exc: _raise(exc)
    finally: conn.close()


@manager_workflow_router.post("/engineer-tasks/{task_id}/supplementation/close", response_model=EngineerTaskDetailResponse)
def CloseSupplementation(task_id: UUID, request: EngineerTaskSupplementationCloseRequest):
    from db_engineer_task_workflow import close_supplementation, get_task_detail
    conn = _connection()
    try:
        row = close_supplementation(conn, task_id, request.manager_name, request.conclusion)
        if not row: raise WorkflowError("Supplementation is not open", 409)
        conn.commit(); return get_task_detail(conn, task_id)
    except Exception as exc: _raise(exc)
    finally: conn.close()


@token_access_router.get("/task", response_model=EngineerTaskTokenAccessResponse)
def GetTokenTask(token: str | None = None, authorization: str | None = Header(default=None)):
    conn = _connection()
    try: return get_token_access(conn, _bearer(authorization, token))
    except Exception as exc: _raise(exc)
    finally: conn.close()


@token_access_router.post("/ack", response_model=EngineerTaskTokenAccessResponse)
def AckTokenTask(request: EngineerTaskTokenActionRequest, token: str | None = None,
                 authorization: str | None = Header(default=None)):
    conn = _connection()
    try:
        task, assignee = direct_ack(conn, _bearer(authorization, token), request.note)
        from db_engineer_task_workflow import get_timeline
        return {"task": task, "currentAssignee": assignee, "timeline": get_timeline(conn, task["task_id"])}
    except Exception as exc: _raise(exc)
    finally: conn.close()


@token_access_router.post("/start", response_model=EngineerTaskTokenAccessResponse)
def StartTokenTask(request: EngineerTaskTokenActionRequest, token: str | None = None,
                   authorization: str | None = Header(default=None)):
    conn = _connection()
    try:
        task, assignee = start_processing(conn, _bearer(authorization, token))
        from db_engineer_task_workflow import get_timeline
        return {"task": task, "currentAssignee": assignee, "timeline": get_timeline(conn, task["task_id"])}
    except Exception as exc: _raise(exc)
    finally: conn.close()


@token_access_router.post("/reports", response_model=EngineerTaskReportResponse, status_code=201)
def AddTokenReport(request: EngineerTaskReportCreateRequest, token: str | None = None,
                   authorization: str | None = Header(default=None)):
    conn = _connection()
    try: return add_report(conn, _bearer(authorization, token), request)
    except Exception as exc: _raise(exc)
    finally: conn.close()


@token_access_router.post("/completion-submit", response_model=EngineerTaskTokenAccessResponse)
def SubmitTokenTask(request: EngineerTaskCompletionSubmitRequest, token: str | None = None,
                    authorization: str | None = Header(default=None)):
    conn = _connection()
    try:
        task, assignee = submit_completion(conn, _bearer(authorization, token), request.note)
        from db_engineer_task_workflow import get_timeline
        return {"task": task, "currentAssignee": assignee, "timeline": get_timeline(conn, task["task_id"])}
    except Exception as exc: _raise(exc)
    finally: conn.close()


@token_access_router.post("/reports/{report_id}/attachments", response_model=list[EngineerTaskAttachmentResponse], status_code=201)
async def UploadAttachments(report_id: UUID, files: list[UploadFile] = File(...),
                            authorization: str | None = Header(default=None)):
    if len(files) > 5: raise HTTPException(422, "At most 5 files may be uploaded at once")
    conn = _connection()
    try:
        rows = []
        for upload in files:
            rows.append(store_attachment(conn, _bearer(authorization, None), report_id, upload.filename or "image", await upload.read()))
        return rows
    except Exception as exc: _raise(exc)
    finally: conn.close()


@token_access_router.get("/attachments/{attachment_id}", responses={200: {"content": {
    "image/jpeg": {"schema": {"type": "string", "format": "binary"}},
    "image/png": {"schema": {"type": "string", "format": "binary"}},
    "image/webp": {"schema": {"type": "string", "format": "binary"}},
}}})
def DownloadAttachment(attachment_id: UUID, token: str | None = None,
                       authorization: str | None = Header(default=None)):
    from db_engineer_task_workflow import get_attachment
    conn = _connection()
    try:
        assignee = authorize_token(conn, _bearer(authorization, token))
        attachment = get_attachment(conn, attachment_id)
        if not attachment or str(attachment["task_id"]) != str(assignee["task_id"]):
            raise HTTPException(404, "Attachment not found")
        if attachment["attachment_status"] == "deleted": raise HTTPException(410, "Attachment was deleted")
        root_value = os.environ.get("ENGINEER_TASK_ATTACHMENT_ROOT", "").strip()
        if not root_value: raise HTTPException(503, "ENGINEER_TASK_ATTACHMENT_ROOT is not configured")
        root = Path(root_value).resolve()
        path = (root / attachment["relative_path"]).resolve()
        if root not in path.parents or not path.is_file(): raise HTTPException(404, "Attachment file not found")
        return FileResponse(path, media_type=attachment["mime_type"], filename=attachment["original_filename"])
    finally: conn.close()


@manager_workflow_router.get("/engineer-task-attachments/{attachment_id}", responses={200: {"content": {
    "image/jpeg": {"schema": {"type": "string", "format": "binary"}},
    "image/png": {"schema": {"type": "string", "format": "binary"}},
    "image/webp": {"schema": {"type": "string", "format": "binary"}},
}}})
def DownloadManagerAttachment(attachment_id: UUID):
    from db_engineer_task_workflow import get_attachment
    conn = _connection()
    try:
        attachment = get_attachment(conn, attachment_id)
        if not attachment: raise HTTPException(404, "Attachment not found")
        if attachment["attachment_status"] == "deleted": raise HTTPException(410, "Attachment was deleted")
        root_value = os.environ.get("ENGINEER_TASK_ATTACHMENT_ROOT", "").strip()
        if not root_value: raise HTTPException(503, "ENGINEER_TASK_ATTACHMENT_ROOT is not configured")
        root = Path(root_value).resolve(); path = (root / attachment["relative_path"]).resolve()
        if root not in path.parents or not path.is_file(): raise HTTPException(404, "Attachment file not found")
        return FileResponse(path, media_type=attachment["mime_type"], filename=attachment["original_filename"],
                            content_disposition_type="inline")
    finally: conn.close()
