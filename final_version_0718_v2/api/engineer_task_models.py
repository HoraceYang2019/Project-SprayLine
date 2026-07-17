"""Pydantic contracts for Manager UI engineer tasks."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


DeliveryStatus = Literal["pending", "sent", "failed", "acknowledged"]
AssigneeDeliveryStatus = Literal["pending", "sent", "failed"]
WorkflowStatus = Literal[
    "unacknowledged", "acknowledged", "in_progress", "completion_submitted", "completed"
]
ReportType = Literal[
    "standard", "correction", "post_submission_addendum", "post_completion_supplement"
]


class EngineerTaskAssigneeInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    station_assignment_id: UUID | None = Field(default=None, alias="stationAssignmentId")
    engineer_name: str = Field(min_length=1, max_length=128, alias="engineerName")
    engineer_email: str = Field(min_length=3, max_length=320, alias="engineerEmail")
    is_primary: bool = Field(default=False, alias="isPrimary")
    is_required_participant: bool = Field(default=False, alias="isRequiredParticipant")

    @field_validator("engineer_email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValueError("engineerEmail must be a valid email address")
        return email


class EngineerTaskCreateV2Request(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_alert_event_id: UUID | None = Field(default=None, alias="sourceAlertEventId")
    station_id: str = Field(min_length=1, max_length=64, alias="stationId")
    station_name: str = Field(min_length=1, max_length=128, alias="stationName")
    process_name: str = Field(min_length=1, max_length=128, alias="processName")
    batch_id: str | None = Field(default=None, max_length=64, alias="batchId")
    batch_label: str | None = Field(default=None, max_length=128, alias="batchLabel")
    data_date: date | None = Field(default=None, alias="dataDate")
    data_hour: str | None = Field(default=None, max_length=64, alias="dataHour")
    data_hour_index: int | None = Field(default=None, ge=0, le=23, alias="dataHourIndex")
    level: str = Field(default="warning", min_length=1, max_length=32)
    issue: str = Field(min_length=1, max_length=4000)
    issue_type: str | None = Field(default=None, max_length=64, alias="issueType")
    cause_id: str | None = Field(default=None, max_length=32, alias="causeId")
    recommendation: str = Field(min_length=1, max_length=4000)
    message_text: str | None = Field(default=None, max_length=12000, alias="messageText")
    assignees: list[EngineerTaskAssigneeInput] = Field(min_length=1, max_length=20)

    @field_validator("assignees")
    @classmethod
    def validate_assignees(cls, assignees: list[EngineerTaskAssigneeInput]):
        emails = [item.engineer_email for item in assignees]
        if len(set(emails)) != len(emails):
            raise ValueError("assignee emails must be unique")
        primary = [item for item in assignees if item.is_primary]
        if len(primary) != 1:
            raise ValueError("exactly one assignee must be primary")
        if not primary[0].is_required_participant:
            raise ValueError("primary assignee must be a required participant")
        return assignees


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


class StationEngineerAssignmentCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    station_id: str = Field(min_length=1, max_length=64, alias="stationId")
    engineer_name: str = Field(min_length=1, max_length=128, alias="engineerName")
    engineer_email: str = Field(min_length=3, max_length=320, alias="engineerEmail")
    assignment_role: str = Field(default="engineer", max_length=32, alias="assignmentRole")
    priority: int = Field(default=100, ge=0, le=10000)


class StationEngineerAssignmentUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    engineer_name: str | None = Field(default=None, min_length=1, max_length=128, alias="engineerName")
    engineer_email: str | None = Field(default=None, min_length=3, max_length=320, alias="engineerEmail")
    assignment_role: str | None = Field(default=None, max_length=32, alias="assignmentRole")
    priority: int | None = Field(default=None, ge=0, le=10000)
    is_active: bool | None = Field(default=None, alias="isActive")


class StationEngineerAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    assignment_id: UUID = Field(alias="assignmentId")
    station_id: str = Field(alias="stationId")
    engineer_name: str = Field(alias="engineerName")
    engineer_email: str = Field(alias="engineerEmail")
    assignment_role: str = Field(alias="assignmentRole")
    priority: int
    is_active: bool = Field(alias="isActive")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class EngineerTaskAssigneeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    assignee_id: UUID = Field(alias="assigneeId")
    task_id: UUID = Field(alias="taskId")
    assignment_round: int = Field(alias="assignmentRound")
    engineer_name_snapshot: str = Field(alias="engineerName")
    engineer_email_snapshot: str = Field(alias="engineerEmail")
    is_primary: bool = Field(alias="isPrimary")
    is_required_participant: bool = Field(alias="isRequiredParticipant")
    is_active: bool = Field(alias="isActive")
    delivery_status: AssigneeDeliveryStatus = Field(alias="deliveryStatus")
    delivery_error: str | None = Field(default=None, alias="deliveryError")
    sent_at: datetime | None = Field(default=None, alias="sentAt")
    acknowledged_at: datetime | None = Field(default=None, alias="acknowledgedAt")
    acknowledged_by: str | None = Field(default=None, alias="acknowledgedBy")
    acknowledged_email: str | None = Field(default=None, alias="acknowledgedEmail")
    ack_source: str | None = Field(default=None, alias="ackSource")
    ack_note: str | None = Field(default=None, alias="ackNote")
    supplementation_allowed: bool = Field(default=False, alias="supplementationAllowed")


class EngineerTaskEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    event_id: UUID = Field(alias="eventId")
    task_id: UUID = Field(alias="taskId")
    assignee_id: UUID | None = Field(default=None, alias="assigneeId")
    event_type: str = Field(alias="eventType")
    event_status: str | None = Field(default=None, alias="eventStatus")
    event_time: datetime = Field(alias="eventTime")
    actor_type: str = Field(alias="actorType")
    actor_name: str | None = Field(default=None, alias="actorName")
    message: str | None = None


class EngineerTaskReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    report_id: UUID = Field(alias="reportId")
    task_id: UUID = Field(alias="taskId")
    reported_by_assignee_id: UUID = Field(alias="reportedByAssigneeId")
    report_type: ReportType = Field(alias="reportType")
    observed_condition: str = Field(alias="observedCondition")
    confirmed_cause: str | None = Field(default=None, alias="confirmedCause")
    action_taken: str = Field(alias="actionTaken")
    result_description: str = Field(alias="resultDescription")
    remaining_issue: str | None = Field(default=None, alias="remainingIssue")
    note: str | None = None
    supersedes_report_id: UUID | None = Field(default=None, alias="supersedesReportId")
    reported_at: datetime = Field(alias="reportedAt")


class EngineerTaskAttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    attachment_id: UUID = Field(alias="attachmentId")
    task_id: UUID = Field(alias="taskId")
    report_id: UUID = Field(alias="reportId")
    original_filename: str = Field(alias="originalFilename")
    mime_type: str = Field(alias="mimeType")
    size_bytes: int = Field(alias="sizeBytes")
    attachment_status: str = Field(alias="attachmentStatus")
    created_at: datetime = Field(alias="createdAt")


class EngineerTaskDetailResponse(EngineerTaskResponse):
    workflow_status: WorkflowStatus = Field(default="unacknowledged", alias="workflowStatus")
    delivery_summary_status: str = Field(default="pending", alias="deliverySummaryStatus")
    current_assignment_round: int = Field(default=1, alias="currentAssignmentRound")
    completion_submitted_at: datetime | None = Field(default=None, alias="completionSubmittedAt")
    completion_submitted_by_assignee_id: UUID | None = Field(default=None, alias="completionSubmittedByAssigneeId")
    completed_at: datetime | None = Field(default=None, alias="completedAt")
    completed_by: str | None = Field(default=None, alias="completedBy")
    reopened_count: int = Field(default=0, alias="reopenedCount")
    supplementation_open: bool = Field(default=False, alias="supplementationOpen")
    supplementation_reason: str | None = Field(default=None, alias="supplementationReason")
    supplementation_opened_at: datetime | None = Field(default=None, alias="supplementationOpenedAt")
    supplementation_opened_by: str | None = Field(default=None, alias="supplementationOpenedBy")
    supplementation_closed_at: datetime | None = Field(default=None, alias="supplementationClosedAt")
    supplementation_closed_by: str | None = Field(default=None, alias="supplementationClosedBy")
    supplementation_conclusion: str | None = Field(default=None, alias="supplementationConclusion")
    legacy_ack_sync_required: bool = Field(default=False, alias="legacyAckSyncRequired")
    assignees: list[EngineerTaskAssigneeResponse] = Field(default_factory=list)
    reports: list[EngineerTaskReportResponse] = Field(default_factory=list)
    attachments: list[EngineerTaskAttachmentResponse] = Field(default_factory=list)


class EngineerTaskHistoryListResponse(BaseModel):
    items: list[EngineerTaskDetailResponse]
    count: int
    total: int
    limit: int
    offset: int


class EngineerTaskTimelineResponse(BaseModel):
    task_id: UUID = Field(alias="taskId")
    items: list[EngineerTaskEventResponse]
    count: int


class EngineerTaskResendRequest(BaseModel):
    assignee_ids: list[UUID] = Field(min_length=1, alias="assigneeIds")
    warning_confirmed: bool = Field(default=False, alias="warningConfirmed")


class EngineerTaskAssignmentUpdateRequest(BaseModel):
    assignees: list[EngineerTaskAssigneeInput] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_primary(self):
        primary = [item for item in self.assignees if item.is_primary]
        if len(primary) != 1 or not primary[0].is_required_participant:
            raise ValueError("exactly one primary required participant is required")
        return self


class EngineerTaskManagerReviewRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    action: Literal["accept", "reject"]
    manager_name: str = Field(min_length=1, max_length=128, alias="managerName")
    applicable_checks: list[str] = Field(min_length=1, alias="applicableChecks")
    confirmed_checks: list[str] = Field(min_length=1, alias="confirmedChecks")
    reason: str | None = Field(default=None, max_length=4000)
    notify_assignee_ids: list[UUID] = Field(default_factory=list, alias="notifyAssigneeIds")


class EngineerTaskReopenRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    batch_id: str | None = Field(default=None, max_length=64, alias="batchId")
    manager_name: str = Field(min_length=1, max_length=128, alias="managerName")
    reason: str = Field(min_length=1, max_length=4000)
    assignees: list[EngineerTaskAssigneeInput] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_primary(self):
        primary = [item for item in self.assignees if item.is_primary]
        if len(primary) != 1 or not primary[0].is_required_participant:
            raise ValueError("exactly one primary required participant is required")
        return self


class EngineerTaskSupplementationOpenRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    manager_name: str = Field(min_length=1, max_length=128, alias="managerName")
    reason: str = Field(min_length=1, max_length=4000)
    assignee_ids: list[UUID] = Field(min_length=1, alias="assigneeIds")


class EngineerTaskSupplementationCloseRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    manager_name: str = Field(min_length=1, max_length=128, alias="managerName")
    conclusion: str = Field(min_length=1, max_length=4000)


class EngineerTaskReportCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    observed_condition: str = Field(min_length=1, max_length=12000, alias="observedCondition")
    confirmed_cause: str | None = Field(default=None, max_length=12000, alias="confirmedCause")
    action_taken: str = Field(min_length=1, max_length=12000, alias="actionTaken")
    result_description: str = Field(min_length=1, max_length=12000, alias="resultDescription")
    remaining_issue: str | None = Field(default=None, max_length=12000, alias="remainingIssue")
    note: str | None = Field(default=None, max_length=12000)
    report_type: ReportType = Field(default="standard", alias="reportType")
    supersedes_report_id: UUID | None = Field(default=None, alias="supersedesReportId")


class EngineerTaskCompletionSubmitRequest(BaseModel):
    note: str | None = Field(default=None, max_length=4000)


class EngineerTaskTokenActionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=4000)


class EngineerTaskTokenAccessResponse(BaseModel):
    task: EngineerTaskDetailResponse
    current_assignee: EngineerTaskAssigneeResponse = Field(alias="currentAssignee")
    timeline: list[EngineerTaskEventResponse]


class NotificationDecisionEvaluateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    source_alert_event_id: UUID | None = Field(default=None, alias="sourceAlertEventId")
    station_id: str = Field(min_length=1, max_length=64, alias="stationId")
    batch_id: str | None = Field(default=None, max_length=64, alias="batchId")
    data_date: date | None = Field(default=None, alias="dataDate")
    data_hour: int | None = Field(default=None, ge=0, le=23, alias="dataHour")
    risk_level: str = Field(min_length=1, max_length=32, alias="riskLevel")
    cause_id: str | None = Field(default=None, max_length=32, alias="causeId")
    issue_type: str | None = Field(default=None, max_length=64, alias="issueType")
    email_requested: bool = Field(default=True, alias="emailRequested")


class NotificationDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    decision_id: UUID = Field(alias="decisionId")
    task_id: UUID | None = Field(default=None, alias="taskId")
    station_id: str = Field(alias="stationId")
    batch_id: str | None = Field(default=None, alias="batchId")
    risk_level: str = Field(alias="riskLevel")
    decision_type: str = Field(alias="decisionType")
    decision_reason: str | None = Field(default=None, alias="decisionReason")
    notification_fingerprint: str = Field(alias="notificationFingerprint")
    suppressed_count: int = Field(alias="suppressedCount")
    first_seen_at: datetime = Field(alias="firstSeenAt")
    last_seen_at: datetime = Field(alias="lastSeenAt")
    created_at: datetime = Field(alias="createdAt")


class NotificationDecisionListResponse(BaseModel):
    items: list[NotificationDecisionResponse]
    count: int
    total: int
