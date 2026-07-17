"""Pydantic contracts for Manager UI engineer tasks."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


DeliveryStatus = Literal["pending", "sent", "failed", "acknowledged"]


class EngineerTaskCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_alert_event_id: UUID | None = Field(default=None, alias="sourceAlertEventId")
    station_id: str = Field(min_length=1, max_length=64, alias="stationId")
    station_name: str = Field(min_length=1, max_length=128, alias="stationName")
    process_name: str = Field(min_length=1, max_length=128, alias="processName")
    batch_id: str | None = Field(default=None, max_length=64, alias="batchId")
    batch_label: str | None = Field(default=None, max_length=128, alias="batchLabel")
    data_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$", alias="dataDate")
    data_hour: str | None = Field(default=None, max_length=64, alias="dataHour")
    level: str = Field(default="warning", min_length=1, max_length=32)
    issue: str = Field(min_length=1, max_length=4000)
    recommendation: str = Field(min_length=1, max_length=4000)
    engineer_name: str | None = Field(default=None, max_length=128, alias="engineerName")
    engineer_email: str = Field(min_length=3, max_length=320, alias="engineerEmail")
    message_text: str | None = Field(default=None, max_length=12000, alias="messageText")

    @field_validator("engineer_email")
    @classmethod
    def validate_engineer_email(cls, value: str) -> str:
        email = value.strip()
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValueError("engineerEmail must be a valid email address")
        return email


class EngineerTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    task_id: UUID = Field(alias="taskId")
    source_alert_event_id: UUID | None = Field(default=None, alias="sourceAlertEventId")
    station_id: str = Field(alias="stationId")
    station_name: str = Field(alias="stationName")
    process_name: str = Field(alias="processName")
    batch_id: str | None = Field(default=None, alias="batchId")
    batch_label: str | None = Field(default=None, alias="batchLabel")
    data_date: str | None = Field(default=None, alias="dataDate")
    data_hour: str | None = Field(default=None, alias="dataHour")
    level: str
    issue: str
    recommendation: str
    engineer_name: str | None = Field(default=None, alias="engineerName")
    engineer_email: str = Field(alias="engineerEmail")
    delivery_status: DeliveryStatus = Field(alias="deliveryStatus")
    delivery_error: str | None = Field(default=None, alias="deliveryError")
    sent_at: datetime | None = Field(default=None, alias="sentAt")
    acknowledged_at: datetime | None = Field(default=None, alias="acknowledgedAt")
    acknowledged_by: str | None = Field(default=None, alias="acknowledgedBy")
    acknowledged_email: str | None = Field(default=None, alias="acknowledgedEmail")
    ack_source: str | None = Field(default=None, alias="ackSource")
    ack_note: str | None = Field(default=None, alias="ackNote")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class EngineerTaskListResponse(BaseModel):
    items: list[EngineerTaskResponse]
    count: int


class EngineerTaskSyncAckRequest(BaseModel):
    force: bool = False


class EngineerTaskDeliveryErrorResponse(BaseModel):
    detail: str
    task: EngineerTaskResponse | None = None
    apps_script_response: dict[str, Any] | None = Field(default=None, alias="appsScriptResponse")

