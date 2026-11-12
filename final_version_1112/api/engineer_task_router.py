"""FastAPI routes dedicated to Manager UI engineer tasks."""

from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from engineer_task_models import (
    EngineerTaskCreateRequest,
    EngineerTaskCreateV2Request,
    EngineerTaskDetailResponse,
    EngineerTaskHistoryListResponse,
    EngineerTaskListResponse,
    EngineerTaskResponse,
    EngineerTaskSyncAckRequest,
)
from engineer_task_service import (
    EngineerTaskConfigurationError,
    EngineerTaskDeliveryError,
    create_and_send_engineer_task,
    sync_engineer_task_ack,
)


router = APIRouter(prefix="/api/manager/engineer-tasks", tags=["Manager Engineer Tasks"])


def _open_connection():
    from db_connection import get_connection

    try:
        return get_connection()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Engineer task DB connection failed: {exc}") from exc


@router.post("", response_model=EngineerTaskResponse | EngineerTaskDetailResponse, status_code=201)
async def CreateEngineerTask(request: EngineerTaskCreateV2Request | EngineerTaskCreateRequest):
    conn = _open_connection()
    try:
        if isinstance(request, EngineerTaskCreateV2Request):
            from engineer_task_workflow_service import create_v2_task
            return await create_v2_task(conn, request)
        return await create_and_send_engineer_task(conn, request)
    except EngineerTaskConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EngineerTaskDeliveryError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Engineer task creation failed: {exc}") from exc
    finally:
        conn.close()


@router.get("", response_model=EngineerTaskHistoryListResponse)
def GetEngineerTasks(
    delivery_status: Literal["pending", "sent", "failed", "acknowledged"] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    hour: int | None = Query(default=None, ge=0, le=23),
    station_id: str | None = Query(default=None),
    batch_id: str | None = Query(default=None),
    decision_type: str | None = Query(default=None),
    workflow_status: str | None = Query(default=None),
    engineer_email: str | None = Query(default=None),
    task_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    from db_engineer_task_workflow import list_task_history

    conn = _open_connection()
    try:
        filters = locals().copy()
        items, total = list_task_history(conn, filters, limit, offset)
        return {"items": items, "count": len(items), "total": total, "limit": limit, "offset": offset}
    finally:
        conn.close()


@router.get("/{task_id}", response_model=EngineerTaskDetailResponse)
def GetEngineerTask(task_id: UUID):
    from db_engineer_task_workflow import get_task_detail

    conn = _open_connection()
    try:
        task = get_task_detail(conn, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Engineer task not found")
        return task
    finally:
        conn.close()


@router.post("/{task_id}/sync-ack", response_model=EngineerTaskResponse)
async def SyncEngineerTaskAck(task_id: UUID, _request: EngineerTaskSyncAckRequest | None = None):
    conn = _open_connection()
    try:
        task = await sync_engineer_task_ack(conn, str(task_id))
        if task is None:
            raise HTTPException(status_code=404, detail="Engineer task not found")
        return task
    except EngineerTaskConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EngineerTaskDeliveryError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        conn.close()
