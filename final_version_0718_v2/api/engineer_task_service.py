"""Engineer task orchestration between PostgreSQL and Apps Script."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Callable

import httpx

from engineer_task_models import EngineerTaskCreateRequest


class EngineerTaskConfigurationError(RuntimeError):
    pass


class EngineerTaskDeliveryError(RuntimeError):
    def __init__(self, message: str, task: dict[str, Any] | None = None, response: dict[str, Any] | None = None):
        super().__init__(message)
        self.task = task
        self.response = response


def _apps_script_url() -> str:
    return os.getenv("ENGINEER_TASK_APP_SCRIPT_URL", "").strip()


def _delivery_payload(task: dict[str, Any], request: EngineerTaskCreateRequest) -> dict[str, Any]:
    payload = request.model_dump(mode="json", by_alias=True)
    payload.update(
        {
            "action": "send_task",
            "taskId": str(task["task_id"]),
            "to": request.engineer_email,
            "title": f"{request.station_name} / {request.process_name}: {request.issue}",
            "task": request.recommendation,
        }
    )
    return payload


async def create_and_send_engineer_task(
    conn,
    request: EngineerTaskCreateRequest,
    *,
    apps_script_url: str | None = None,
    client_factory: Callable[..., Any] = httpx.AsyncClient,
    repository: Any | None = None,
) -> dict[str, Any]:
    if repository is None:
        import db_engineer_task as repository

    request_payload = request.model_dump(mode="json", by_alias=True)
    db_payload = request.model_dump(mode="python", exclude={"message_text"})
    db_payload["payload_json"] = request_payload
    task = repository.create_engineer_task(conn, db_payload)
    url = (apps_script_url if apps_script_url is not None else _apps_script_url()).strip()

    if not url:
        message = "ENGINEER_TASK_APP_SCRIPT_URL is not configured"
        repository.mark_engineer_task_failed(conn, task["task_id"], message)
        raise EngineerTaskConfigurationError(message)

    response_payload: dict[str, Any] | None = None
    try:
        async with client_factory(timeout=httpx.Timeout(15.0, connect=5.0), follow_redirects=True) as client:
            response = await client.post(url, json=_delivery_payload(task, request))
            response.raise_for_status()
            response_payload = response.json()
        if response_payload.get("success") is not True:
            raise ValueError(str(response_payload.get("error") or "Apps Script did not confirm delivery"))
    except Exception as exc:
        message = f"Apps Script delivery failed: {exc}"
        failed = repository.mark_engineer_task_failed(conn, task["task_id"], message, response_payload)
        raise EngineerTaskDeliveryError(message, failed, response_payload) from exc

    return repository.mark_engineer_task_sent(conn, task["task_id"], response_payload) or task


def _parse_ack_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


async def sync_engineer_task_ack(
    conn,
    task_id: str,
    *,
    apps_script_url: str | None = None,
    client_factory: Callable[..., Any] = httpx.AsyncClient,
    repository: Any | None = None,
) -> dict[str, Any] | None:
    if repository is None:
        import db_engineer_task as repository

    task = repository.get_engineer_task(conn, task_id)
    if task is None or task.get("delivery_status") == "acknowledged":
        return task

    url = (apps_script_url if apps_script_url is not None else _apps_script_url()).strip()
    if not url:
        raise EngineerTaskConfigurationError("ENGINEER_TASK_APP_SCRIPT_URL is not configured")

    try:
        async with client_factory(timeout=httpx.Timeout(10.0, connect=5.0), follow_redirects=True) as client:
            response = await client.get(url, params={"action": "ack_status", "taskId": task_id})
            response.raise_for_status()
            ack_payload = response.json()
    except Exception as exc:
        raise EngineerTaskDeliveryError(f"Apps Script ACK sync failed: {exc}", task) from exc

    if ack_payload.get("acknowledged") is not True:
        return task

    return repository.acknowledge_engineer_task(
        conn,
        task_id,
        acknowledged_at=_parse_ack_datetime(ack_payload.get("ackAt")),
        acknowledged_by=ack_payload.get("ackBy") or "Engineer",
        acknowledged_email=ack_payload.get("ackEmail"),
        ack_source=ack_payload.get("source") or "apps_script",
        ack_note=ack_payload.get("ackNote"),
        apps_script_response=ack_payload,
    )
