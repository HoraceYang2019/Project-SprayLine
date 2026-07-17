"""FastAPI routes dedicated to Manager UI engineer tasks."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from engineer_task_models import (
    EngineerTaskCreateRequest,
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


@router.post("", response_model=EngineerTaskResponse, status_code=201)
async def CreateEngineerTask(request: EngineerTaskCreateRequest):
    conn = _open_connection()
    try:
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


@router.get("", response_model=EngineerTaskListResponse)
def GetEngineerTasks(
    delivery_status: Literal["pending", "sent", "failed", "acknowledged"] | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    from db_engineer_task import get_engineer_tasks

    conn = _open_connection()
    try:
        items = get_engineer_tasks(conn, delivery_status=delivery_status, limit=limit, offset=offset)
        return {"items": items, "count": len(items)}
    finally:
        conn.close()


@router.get("/{task_id}", response_model=EngineerTaskResponse)
def GetEngineerTask(task_id: UUID):
    from db_engineer_task import get_engineer_task

    conn = _open_connection()
    try:
        task = get_engineer_task(conn, task_id)
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
