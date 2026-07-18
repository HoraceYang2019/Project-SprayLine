"""Repository operations for the Phase 2 engineer-task workflow.

Functions in this module never commit or roll back. The workflow service owns
the transaction so multi-row state changes remain atomic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from psycopg2.extras import Json

from db_connection import _fetch, _fetchone


def _id(value: UUID | str | None) -> str | None:
    return str(value) if value is not None else None


def list_station_assignments(conn, station_id=None, active_only=True):
    clauses, params = [], []
    if station_id:
        clauses.append("station_id = %s")
        params.append(station_id)
    if active_only:
        clauses.append("is_active = TRUE")
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    return _fetch(conn, f"""SELECT * FROM station_engineer_assignment{where}
        ORDER BY station_id, priority, engineer_name""", tuple(params))


def create_station_assignment(conn, values):
    return _fetchone(conn, """
        INSERT INTO station_engineer_assignment
            (station_id, engineer_name, engineer_email, assignment_role, priority)
        VALUES (%s, %s, LOWER(%s), %s, %s) RETURNING *
    """, (values["station_id"], values["engineer_name"], values["engineer_email"],
          values.get("assignment_role", "engineer"), values.get("priority", 100)))


def update_station_assignment(conn, assignment_id, values):
    allowed = {"engineer_name", "engineer_email", "assignment_role", "priority", "is_active"}
    changes = {key: value for key, value in values.items() if key in allowed and value is not None}
    if not changes:
        return _fetchone(conn, "SELECT * FROM station_engineer_assignment WHERE assignment_id=%s", (_id(assignment_id),))
    parts, params = [], []
    for key, value in changes.items():
        parts.append(f"{key} = LOWER(%s)" if key == "engineer_email" else f"{key} = %s")
        params.append(value)
    parts.append("updated_at = NOW()")
    if "is_active" in changes:
        parts.append("effective_to = CASE WHEN %s = FALSE THEN NOW() ELSE NULL END")
        params.append(changes["is_active"])
    params.append(_id(assignment_id))
    return _fetchone(conn, f"UPDATE station_engineer_assignment SET {', '.join(parts)} WHERE assignment_id=%s RETURNING *", tuple(params))


def append_event(conn, task_id, event_type, *, assignee_id=None, event_status=None,
                 actor_type="system", actor_name=None, actor_email=None, message=None,
                 event_data=None):
    # event_data must contain operational metadata only; never pass a plain token.
    safe_data = {k: v for k, v in (event_data or {}).items() if "token" not in k.lower()}
    return _fetchone(conn, """
        INSERT INTO engineer_task_event
            (task_id, assignee_id, event_type, event_status, actor_type,
             actor_name, actor_email, message, event_data, event_time)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,clock_timestamp()) RETURNING *
    """, (_id(task_id), _id(assignee_id), event_type, event_status, actor_type,
          actor_name, actor_email, message, Json(safe_data)))


def create_task_with_assignees(conn, task, assignees):
    task_id = str(uuid4())
    primary = next(item for item in assignees if item["is_primary"])
    row = _fetchone(conn, """
        INSERT INTO engineer_task (
            task_id, source_alert_event_id, station_id, station_name, process_name,
            batch_id, batch_label, data_date, data_hour, data_hour_index, level,
            issue, issue_type, cause_id, recommendation, engineer_name, engineer_email,
            delivery_status, workflow_status, delivery_summary_status,
            notification_fingerprint, payload_json
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                  'pending','unacknowledged','pending',%s,'{}'::jsonb) RETURNING *
    """, (task_id, _id(task.get("source_alert_event_id")), task["station_id"], task["station_name"],
          task["process_name"], task.get("batch_id"), task.get("batch_label"),
          str(task.get("data_date")) if task.get("data_date") else None, task.get("data_hour"),
          task.get("data_hour_index"), task.get("level", "warning"), task["issue"],
          task.get("issue_type"), task.get("cause_id"), task["recommendation"],
          primary["engineer_name"], primary["engineer_email"], task.get("notification_fingerprint")))
    created = []
    for item in assignees:
        assignee_id = str(uuid4())
        created.append(_fetchone(conn, """
            INSERT INTO engineer_task_assignee (
                assignee_id, task_id, assignment_round, station_assignment_id,
                engineer_name_snapshot, engineer_email_snapshot, assignment_role,
                is_primary, is_required_participant, access_token_hash, token_expires_at
            ) VALUES (%s,%s,1,%s,%s,LOWER(%s),%s,%s,%s,%s,%s) RETURNING *
        """, (assignee_id, task_id, _id(item.get("station_assignment_id")), item["engineer_name"],
              item["engineer_email"], "primary" if item["is_primary"] else "collaborator",
              item["is_primary"], item["is_required_participant"], item["token_hash"],
              item.get("token_expires_at"))))
    primary_row = next(item for item in created if item["is_primary"])
    row = _fetchone(conn, "UPDATE engineer_task SET primary_assignee_id=%s WHERE task_id=%s RETURNING *",
                    (_id(primary_row["assignee_id"]), task_id))
    append_event(conn, task_id, "task_created", message="Engineer task created")
    return row, created


def update_assignee_delivery(conn, assignee_id, status, *, error=None, resend=False):
    return _fetchone(conn, """
        UPDATE engineer_task_assignee SET delivery_status=%s, delivery_error=%s,
          sent_at=CASE WHEN %s='sent' THEN COALESCE(sent_at,NOW()) ELSE sent_at END,
          last_sent_at=CASE WHEN %s='sent' THEN NOW() ELSE last_sent_at END,
          resend_count=resend_count + %s, updated_at=NOW()
        WHERE assignee_id=%s RETURNING *
    """, (status, error, status, status, 1 if resend else 0, _id(assignee_id)))


def refresh_delivery_summary(conn, task_id):
    return _fetchone(conn, """
        UPDATE engineer_task task SET delivery_summary_status = summary.status,
            delivery_status = CASE WHEN summary.status='partial' THEN 'sent' ELSE summary.status END,
            delivery_error = CASE WHEN summary.status='failed' THEN 'One or more assignee deliveries failed' ELSE NULL END,
            sent_at = CASE WHEN summary.status IN ('sent','partial') THEN COALESCE(task.sent_at,NOW()) ELSE task.sent_at END,
            updated_at=NOW()
        FROM (SELECT task_id, CASE
          WHEN BOOL_AND(delivery_status='failed') THEN 'failed'
          WHEN BOOL_AND(delivery_status='sent') THEN 'sent'
          WHEN BOOL_OR(delivery_status='sent') THEN 'partial'
          ELSE 'pending' END status
          FROM engineer_task_assignee WHERE task_id=%s AND is_active=TRUE GROUP BY task_id) summary
        WHERE task.task_id=summary.task_id RETURNING task.*
    """, (_id(task_id),))


def get_task(conn, task_id):
    return _fetchone(conn, "SELECT * FROM engineer_task WHERE task_id=%s", (_id(task_id),))


def get_assignees(conn, task_id, active_only=False):
    active = " AND is_active=TRUE" if active_only else ""
    return _fetch(conn, f"SELECT * FROM engineer_task_assignee WHERE task_id=%s{active} ORDER BY assignment_round, is_primary DESC, assigned_at", (_id(task_id),))


def get_reports(conn, task_id):
    return _fetch(conn, "SELECT * FROM engineer_task_report WHERE task_id=%s ORDER BY reported_at, report_id", (_id(task_id),))


def get_attachments(conn, task_id):
    return _fetch(conn, "SELECT * FROM engineer_task_attachment WHERE task_id=%s ORDER BY created_at, attachment_id", (_id(task_id),))


def count_report_attachments(conn, report_id):
    row = _fetchone(conn, "SELECT COUNT(*) count FROM engineer_task_attachment WHERE report_id=%s AND attachment_status<>'deleted'", (_id(report_id),))
    return int(row["count"])


def get_timeline(conn, task_id):
    return _fetch(conn, "SELECT event_id,task_id,assignee_id,event_type,event_status,event_time,actor_type,actor_name,message FROM engineer_task_event WHERE task_id=%s ORDER BY event_time,event_id", (_id(task_id),))


def get_task_detail(conn, task_id):
    task = get_task(conn, task_id)
    if not task:
        return None
    task["assignees"] = get_assignees(conn, task_id)
    task["legacy_ack_sync_required"] = any(
        item.get("is_active") and not item.get("access_token_hash")
        for item in task["assignees"]
    )
    task["reports"] = get_reports(conn, task_id)
    task["attachments"] = get_attachments(conn, task_id)
    return task


def list_task_history(conn, filters, limit, offset):
    clauses, params = ["task.created_at >= COALESCE(%s::date, CURRENT_DATE - INTERVAL '6 days')"], [filters.get("date_from")]
    mapping = {"date_to": "task.created_at < (%s::date + INTERVAL '1 day')", "hour": "task.data_hour_index=%s",
               "station_id": "task.station_id=%s", "batch_id": "task.batch_id=%s",
               "delivery_status": "task.delivery_status=%s", "workflow_status": "task.workflow_status=%s",
               "task_id": "task.task_id=%s"}
    for key, clause in mapping.items():
        if filters.get(key) not in (None, ""):
            clauses.append(clause); params.append(filters[key])
    if filters.get("engineer_email"):
        clauses.append("EXISTS (SELECT 1 FROM engineer_task_assignee a WHERE a.task_id=task.task_id AND LOWER(a.engineer_email_snapshot)=LOWER(%s))")
        params.append(filters["engineer_email"])
    if filters.get("decision_type"):
        clauses.append("EXISTS (SELECT 1 FROM notification_decision d WHERE d.task_id=task.task_id AND d.decision_type=%s)")
        params.append(filters["decision_type"])
    where = " AND ".join(clauses)
    total = _fetchone(conn, f"SELECT COUNT(*) AS total FROM engineer_task task WHERE {where}", tuple(params))["total"]
    rows = _fetch(conn, f"SELECT task.* FROM engineer_task task WHERE {where} ORDER BY task.created_at DESC LIMIT %s OFFSET %s", tuple(params + [limit, offset]))
    for row in rows:
        row["assignees"] = get_assignees(conn, row["task_id"])
        row["legacy_ack_sync_required"] = any(
            item.get("is_active") and not item.get("access_token_hash")
            for item in row["assignees"]
        )
        row["reports"] = get_reports(conn, row["task_id"])
        row["attachments"] = get_attachments(conn, row["task_id"])
    return rows, int(total)


def find_assignee_by_token_hash(conn, token_hash):
    return _fetchone(conn, """
        SELECT assignee.*, task.workflow_status, task.completed_at, task.supplementation_open
        FROM engineer_task_assignee assignee JOIN engineer_task task USING(task_id)
        WHERE assignee.access_token_hash=%s
    """, (token_hash,))


def rotate_assignee_token(conn, assignee_id, token_hash, token_expires_at):
    return _fetchone(conn, """UPDATE engineer_task_assignee SET access_token_hash=%s,
      token_expires_at=%s,token_revoked_at=NULL,updated_at=NOW()
      WHERE assignee_id=%s AND is_active=TRUE RETURNING *""",
      (token_hash, token_expires_at, _id(assignee_id)))


def get_assignee(conn, assignee_id):
    return _fetchone(conn, "SELECT * FROM engineer_task_assignee WHERE assignee_id=%s", (_id(assignee_id),))


def replace_active_assignees(conn, task_id, assignees, assignment_round):
    current = get_assignees(conn, task_id, active_only=True)
    by_email = {row["engineer_email_snapshot"].lower(): row for row in current}
    requested = {item["engineer_email"].lower(): item for item in assignees}
    _fetch(conn, """UPDATE engineer_task_assignee SET is_primary=FALSE,
      assignment_role='collaborator',updated_at=NOW() WHERE task_id=%s AND is_active=TRUE
      RETURNING assignee_id""", (_id(task_id),))
    removed = []
    for email, row in by_email.items():
        if email not in requested:
            removed.append(_fetchone(conn, """UPDATE engineer_task_assignee SET is_active=FALSE,
              removed_at=NOW(),token_revoked_at=NOW(),updated_at=NOW() WHERE assignee_id=%s RETURNING *""", (_id(row["assignee_id"]),)))
    active = []
    for email, item in requested.items():
        existing = by_email.get(email)
        if existing:
            active.append(_fetchone(conn, """UPDATE engineer_task_assignee SET engineer_name_snapshot=%s,
              station_assignment_id=%s,is_primary=%s,assignment_role=%s,is_required_participant=%s,
              is_active=TRUE,removed_at=NULL,updated_at=NOW() WHERE assignee_id=%s RETURNING *""",
              (item["engineer_name"], _id(item.get("station_assignment_id")), item["is_primary"],
               "primary" if item["is_primary"] else "collaborator", item["is_required_participant"], _id(existing["assignee_id"]))))
        else:
            assignee_id = str(uuid4())
            active.append(_fetchone(conn, """INSERT INTO engineer_task_assignee
              (assignee_id,task_id,assignment_round,station_assignment_id,engineer_name_snapshot,
               engineer_email_snapshot,assignment_role,is_primary,is_required_participant,access_token_hash,token_expires_at)
              VALUES(%s,%s,%s,%s,%s,LOWER(%s),%s,%s,%s,%s,%s) RETURNING *""",
              (assignee_id,_id(task_id),assignment_round,_id(item.get("station_assignment_id")),item["engineer_name"],
               item["engineer_email"],"primary" if item["is_primary"] else "collaborator",item["is_primary"],
               item["is_required_participant"],item["token_hash"],item["token_expires_at"])))
    primary = next(row for row in active if row["is_primary"])
    _fetchone(conn, "UPDATE engineer_task SET primary_assignee_id=%s,engineer_name=%s,engineer_email=%s,updated_at=NOW() WHERE task_id=%s RETURNING *",
              (_id(primary["assignee_id"]),primary["engineer_name_snapshot"],primary["engineer_email_snapshot"],_id(task_id)))
    return active, removed


def reopen_task(conn, task_id, manager_name, reason, batch_id):
    task = _fetchone(conn, """UPDATE engineer_task SET current_assignment_round=current_assignment_round+1,
      workflow_status='unacknowledged',delivery_summary_status='pending',delivery_status='pending',
      completion_submitted_at=NULL,completion_submitted_by_assignee_id=NULL,completed_at=NULL,completed_by=NULL,
      reopened_count=reopened_count+1,batch_id=COALESCE(%s,batch_id),updated_at=NOW()
      WHERE task_id=%s RETURNING *""", (batch_id,_id(task_id)))
    if task:
        _fetch(conn, """UPDATE engineer_task_assignee SET is_active=FALSE,removed_at=NOW(),
          token_revoked_at=NOW(),updated_at=NOW() WHERE task_id=%s AND is_active=TRUE RETURNING assignee_id""", (_id(task_id),))
        append_event(conn, task_id, "reopened", actor_type="manager", actor_name=manager_name, message=reason,
                     event_data={"assignmentRound": task["current_assignment_round"]})
    return task


def acknowledge_assignee(conn, assignee_id, note=None):
    assignee = _fetchone(conn, """UPDATE engineer_task_assignee SET acknowledged_at=COALESCE(acknowledged_at,NOW()),
        acknowledged_by=engineer_name_snapshot, acknowledged_email=engineer_email_snapshot,
        ack_source='direct_db', ack_note=COALESCE(%s,ack_note), updated_at=NOW()
        WHERE assignee_id=%s AND is_active=TRUE RETURNING *""", (note, _id(assignee_id)))
    if not assignee:
        return None
    task = _fetchone(conn, """UPDATE engineer_task SET workflow_status='acknowledged', updated_at=NOW()
        WHERE task_id=%s AND workflow_status='unacknowledged' AND NOT EXISTS (
          SELECT 1 FROM engineer_task_assignee WHERE task_id=%s AND is_active=TRUE
          AND is_required_participant=TRUE AND acknowledged_at IS NULL) RETURNING *""",
        (_id(assignee["task_id"]), _id(assignee["task_id"])))
    append_event(conn, assignee["task_id"], "acknowledged", assignee_id=assignee_id,
                 actor_type="engineer", actor_name=assignee["engineer_name_snapshot"], message="Task acknowledged")
    return assignee, task


def start_processing(conn, task_id, assignee_id):
    row = _fetchone(conn, """UPDATE engineer_task SET workflow_status='in_progress',updated_at=NOW()
      WHERE task_id=%s AND workflow_status='acknowledged' RETURNING *""", (_id(task_id),))
    if row:
        append_event(conn, task_id, "in_progress", assignee_id=assignee_id, actor_type="engineer", message="Processing started")
    return row


def create_report(conn, task_id, assignee_id, values, report_type):
    row = _fetchone(conn, """INSERT INTO engineer_task_report
      (task_id,assignment_round,reported_by_assignee_id,report_type,observed_condition,
       confirmed_cause,action_taken,result_description,remaining_issue,note,supersedes_report_id)
      SELECT %s,current_assignment_round,%s,%s,%s,%s,%s,%s,%s,%s,%s FROM engineer_task WHERE task_id=%s RETURNING *""",
      (_id(task_id), _id(assignee_id), report_type, values["observed_condition"], values.get("confirmed_cause"),
       values["action_taken"], values["result_description"], values.get("remaining_issue"), values.get("note"),
       _id(values.get("supersedes_report_id")), _id(task_id)))
    event = "report_corrected" if report_type == "correction" else ("post_submission_addendum" if report_type == "post_submission_addendum" else ("post_completion_supplement" if report_type == "post_completion_supplement" else "onsite_report_submitted"))
    append_event(conn, task_id, event, assignee_id=assignee_id, actor_type="engineer", event_data={"reportId": str(row["report_id"])})
    return row


def submit_completion(conn, task_id, assignee_id, note=None):
    row = _fetchone(conn, """UPDATE engineer_task task SET workflow_status='completion_submitted',
      completion_submitted_at=NOW(),completion_submitted_by_assignee_id=%s,updated_at=NOW()
      WHERE task.task_id=%s AND task.workflow_status='in_progress'
      AND task.primary_assignee_id=%s AND NOT EXISTS (SELECT 1 FROM engineer_task_assignee a
        WHERE a.task_id=task.task_id AND a.is_active=TRUE AND a.is_required_participant=TRUE AND a.acknowledged_at IS NULL)
      RETURNING task.*""", (_id(assignee_id), _id(task_id), _id(assignee_id)))
    if row:
        append_event(conn, task_id, "completion_submitted", assignee_id=assignee_id, actor_type="engineer", message=note)
    return row


def manager_review(conn, task_id, action, manager_name, reason=None, checks=None):
    if action == "accept":
        row = _fetchone(conn, """UPDATE engineer_task SET workflow_status='completed',completed_at=NOW(),
          completed_by=%s,updated_at=NOW() WHERE task_id=%s AND workflow_status='completion_submitted' RETURNING *""",
          (manager_name, _id(task_id)))
        event = "manager_accepted_completion"
        if row:
            _fetch(conn, """UPDATE engineer_task_attachment SET retention_due_at=%s+INTERVAL '3 years'
              WHERE task_id=%s AND attachment_status='active' AND retention_due_at IS NULL
              RETURNING attachment_id""", (row["completed_at"], _id(task_id)))
    else:
        row = _fetchone(conn, """UPDATE engineer_task SET workflow_status='in_progress',updated_at=NOW()
          WHERE task_id=%s AND workflow_status='completion_submitted' RETURNING *""", (_id(task_id),))
        event = "manager_rejected_completion"
    if row:
        append_event(conn, task_id, event, actor_type="manager", actor_name=manager_name,
                     message=reason, event_data={"checks": checks or []})
    return row


def open_supplementation(conn, task_id, manager_name, reason, assignee_ids):
    row = _fetchone(conn, """UPDATE engineer_task SET supplementation_open=TRUE,supplementation_reason=%s,
      supplementation_opened_at=NOW(),supplementation_opened_by=%s,supplementation_closed_at=NULL,
      supplementation_closed_by=NULL,supplementation_conclusion=NULL,updated_at=NOW()
      WHERE task_id=%s AND workflow_status='completed' AND supplementation_open=FALSE RETURNING *""",
      (reason, manager_name, _id(task_id)))
    if row:
        _fetch(conn, "UPDATE engineer_task_assignee SET supplementation_allowed=(assignee_id=ANY(%s::uuid[])),updated_at=NOW() WHERE task_id=%s RETURNING assignee_id",
               ([str(v) for v in assignee_ids], _id(task_id)))
        append_event(conn, task_id, "supplementation_opened", actor_type="manager", actor_name=manager_name, message=reason)
    return row


def close_supplementation(conn, task_id, manager_name, conclusion):
    row = _fetchone(conn, """UPDATE engineer_task SET supplementation_open=FALSE,
      supplementation_closed_at=NOW(),supplementation_closed_by=%s,supplementation_conclusion=%s,updated_at=NOW()
      WHERE task_id=%s AND workflow_status='completed' AND supplementation_open=TRUE RETURNING *""",
      (manager_name, conclusion, _id(task_id)))
    if row:
        _fetch(conn, "UPDATE engineer_task_assignee SET supplementation_allowed=FALSE,updated_at=NOW() WHERE task_id=%s RETURNING assignee_id", (_id(task_id),))
        append_event(conn, task_id, "supplementation_closed", actor_type="manager", actor_name=manager_name, message=conclusion)
    return row


def list_notification_decisions(conn, filters, limit, offset):
    clauses, params = ["created_at >= COALESCE(%s::date,CURRENT_DATE-INTERVAL '6 days')"], [filters.get("date_from")]
    for key in ("station_id", "decision_type"):
        if filters.get(key): clauses.append(f"{key}=%s"); params.append(filters[key])
    where = " AND ".join(clauses)
    total = _fetchone(conn, f"SELECT COUNT(*) total FROM notification_decision WHERE {where}", tuple(params))["total"]
    rows = _fetch(conn, f"SELECT * FROM notification_decision WHERE {where} ORDER BY created_at DESC LIMIT %s OFFSET %s", tuple(params+[limit,offset]))
    return rows, int(total)


def find_cooldown_decision(conn, fingerprint):
    return _fetchone(conn, """SELECT * FROM notification_decision WHERE notification_fingerprint=%s
      AND cooldown_until>NOW() ORDER BY last_seen_at DESC LIMIT 1 FOR UPDATE""", (fingerprint,))


def find_source_decision(conn, source_alert_event_id):
    if not source_alert_event_id:
        return None
    return _fetchone(conn, """SELECT * FROM notification_decision
      WHERE source_alert_event_id=%s ORDER BY created_at DESC LIMIT 1""", (_id(source_alert_event_id),))


def create_notification_decision(conn, values):
    return _fetchone(conn, """INSERT INTO notification_decision
      (task_id,source_alert_event_id,station_id,batch_id,data_date,data_hour,risk_level,decision_type,
       decision_reason,notification_fingerprint,cooldown_window_start,cooldown_until,suppressed_count)
      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW()+INTERVAL '20 minutes',%s) RETURNING *""",
      (_id(values.get("task_id")), _id(values.get("source_alert_event_id")), values["station_id"], values.get("batch_id"), values.get("data_date"),
       values.get("data_hour"), values["risk_level"], values["decision_type"], values.get("decision_reason"),
       values["notification_fingerprint"], values.get("suppressed_count", 0)))


def record_task_created_decision(conn, task):
    existing = find_source_decision(conn, task.get("source_alert_event_id"))
    if existing:
        return _fetchone(conn, """UPDATE notification_decision SET task_id=%s,
          decision_type='email_task_created',updated_at=NOW() WHERE decision_id=%s RETURNING *""",
          (_id(task["task_id"]), _id(existing["decision_id"])))
    return create_notification_decision(conn, {
        "task_id": task["task_id"], "source_alert_event_id": task.get("source_alert_event_id"),
        "station_id": task["station_id"], "batch_id": task.get("batch_id"),
        "data_date": task.get("data_date"), "data_hour": task.get("data_hour_index"),
        "risk_level": task["level"], "decision_type": "email_task_created",
        "decision_reason": "Engineer task created", "notification_fingerprint": task["notification_fingerprint"],
    })


def increment_suppressed_decision(conn, decision_id):
    return _fetchone(conn, """UPDATE notification_decision SET decision_type='suppressed',
      suppressed_count=suppressed_count+1,last_seen_at=NOW(),updated_at=NOW()
      WHERE decision_id=%s RETURNING *""", (_id(decision_id),))


def create_attachment_metadata(conn, values):
    return _fetchone(conn, """INSERT INTO engineer_task_attachment
      (attachment_id,task_id,report_id,uploaded_by_assignee_id,original_filename,stored_filename,
       relative_path,mime_type,size_bytes,sha256_hex,retention_due_at)
      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
      (_id(values["attachment_id"]),_id(values["task_id"]),_id(values["report_id"]),_id(values["assignee_id"]),
       values["original_filename"],values["stored_filename"],values["relative_path"],values["mime_type"],
       values["size_bytes"],values["sha256_hex"],values.get("retention_due_at")))


def get_attachment(conn, attachment_id):
    return _fetchone(conn, "SELECT * FROM engineer_task_attachment WHERE attachment_id=%s", (_id(attachment_id),))
