-- ============================================================================
-- SprayLine Manager Engineer Task workflow extension
-- Purpose:
--   Add Notification History, multiple assignees, timeline, reports,
--   attachments, workflow states and station-to-engineer assignments.
--
-- Safety:
--   - Additive migration only.
--   - No destructive table or row-removal statements.
--   - Existing engineer_task rows and Phase 1 endpoints remain compatible.
--   - Review on the real PostgreSQL machine before applying.
-- ============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- --------------------------------------------------------------------------
-- 1. Extend existing engineer_task without removing legacy fields.
-- --------------------------------------------------------------------------

ALTER TABLE public.engineer_task
    ADD COLUMN IF NOT EXISTS workflow_status VARCHAR(32) NOT NULL DEFAULT 'unacknowledged',
    ADD COLUMN IF NOT EXISTS delivery_summary_status VARCHAR(16) NOT NULL DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS current_assignment_round INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS data_hour_index SMALLINT NULL,
    ADD COLUMN IF NOT EXISTS cause_id VARCHAR(32) NULL,
    ADD COLUMN IF NOT EXISTS issue_type VARCHAR(64) NULL,
    ADD COLUMN IF NOT EXISTS notification_fingerprint VARCHAR(255) NULL,
    ADD COLUMN IF NOT EXISTS primary_assignee_id UUID NULL,
    ADD COLUMN IF NOT EXISTS completion_submitted_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS completion_submitted_by_assignee_id UUID NULL,
    ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS completed_by VARCHAR(128) NULL,
    ADD COLUMN IF NOT EXISTS reopened_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS supplementation_open BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS supplementation_reason TEXT NULL,
    ADD COLUMN IF NOT EXISTS supplementation_opened_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS supplementation_opened_by VARCHAR(128) NULL,
    ADD COLUMN IF NOT EXISTS supplementation_closed_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS supplementation_closed_by VARCHAR(128) NULL,
    ADD COLUMN IF NOT EXISTS supplementation_conclusion TEXT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'engineer_task_workflow_status_check'
    ) THEN
        ALTER TABLE public.engineer_task
            ADD CONSTRAINT engineer_task_workflow_status_check
            CHECK (
                workflow_status IN (
                    'unacknowledged',
                    'acknowledged',
                    'in_progress',
                    'completion_submitted',
                    'completed'
                )
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'engineer_task_delivery_summary_status_check'
    ) THEN
        ALTER TABLE public.engineer_task
            ADD CONSTRAINT engineer_task_delivery_summary_status_check
            CHECK (
                delivery_summary_status IN (
                    'pending',
                    'sent',
                    'partial',
                    'failed'
                )
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'engineer_task_data_hour_index_check'
    ) THEN
        ALTER TABLE public.engineer_task
            ADD CONSTRAINT engineer_task_data_hour_index_check
            CHECK (data_hour_index IS NULL OR data_hour_index BETWEEN 0 AND 23);
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_engineer_task_workflow_created
    ON public.engineer_task (workflow_status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_engineer_task_date_hour
    ON public.engineer_task (data_date, data_hour_index, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_engineer_task_batch_created
    ON public.engineer_task (batch_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_engineer_task_fingerprint_created
    ON public.engineer_task (notification_fingerprint, created_at DESC);

-- Preserve legacy ACK result as the initial workflow status.
UPDATE public.engineer_task
SET workflow_status = 'acknowledged'
WHERE workflow_status = 'unacknowledged'
  AND (
      acknowledged_at IS NOT NULL
      OR delivery_status = 'acknowledged'
  );

UPDATE public.engineer_task
SET delivery_summary_status = CASE
    WHEN delivery_status = 'failed' THEN 'failed'
    WHEN delivery_status IN ('sent', 'acknowledged') THEN 'sent'
    ELSE 'pending'
END
WHERE delivery_summary_status = 'pending';

UPDATE public.engineer_task
SET data_hour_index =
    CASE
        WHEN data_hour ~ '^([01][0-9]|2[0-3])'
        THEN SUBSTRING(data_hour FROM '^([0-9]{2})')::SMALLINT
        ELSE NULL
    END
WHERE data_hour_index IS NULL
  AND data_hour IS NOT NULL;

-- --------------------------------------------------------------------------
-- 2. Station-to-engineer directory.
-- --------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.station_engineer_assignment (
    assignment_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    station_id          VARCHAR(64) NOT NULL,
    engineer_name       VARCHAR(128) NOT NULL,
    engineer_email      VARCHAR(320) NOT NULL,
    assignment_role     VARCHAR(32) NOT NULL DEFAULT 'engineer',
    priority            INTEGER NOT NULL DEFAULT 100,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    effective_from      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    effective_to        TIMESTAMPTZ NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_station_engineer_active
    ON public.station_engineer_assignment
       (station_id, is_active, priority, engineer_name);

CREATE UNIQUE INDEX IF NOT EXISTS uq_station_engineer_active_email
    ON public.station_engineer_assignment
       (station_id, LOWER(engineer_email))
    WHERE is_active = TRUE;

-- --------------------------------------------------------------------------
-- 3. Per-task assignees, individual delivery and individual ACK.
-- --------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.engineer_task_assignee (
    assignee_id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id                       UUID NOT NULL
                                  REFERENCES public.engineer_task(task_id)
                                  ON DELETE CASCADE,
    assignment_round              INTEGER NOT NULL DEFAULT 1,
    station_assignment_id         UUID NULL
                                  REFERENCES public.station_engineer_assignment(assignment_id)
                                  ON DELETE SET NULL,
    engineer_name_snapshot        VARCHAR(128) NOT NULL,
    engineer_email_snapshot       VARCHAR(320) NOT NULL,
    assignment_role               VARCHAR(16) NOT NULL DEFAULT 'collaborator',
    is_primary                    BOOLEAN NOT NULL DEFAULT FALSE,
    is_required_participant       BOOLEAN NOT NULL DEFAULT FALSE,
    is_active                     BOOLEAN NOT NULL DEFAULT TRUE,
    delivery_status               VARCHAR(16) NOT NULL DEFAULT 'pending',
    delivery_error                TEXT NULL,
    sent_at                       TIMESTAMPTZ NULL,
    last_sent_at                  TIMESTAMPTZ NULL,
    resend_count                  INTEGER NOT NULL DEFAULT 0,
    apps_script_response_json     JSONB NULL,
    acknowledged_at               TIMESTAMPTZ NULL,
    acknowledged_by               VARCHAR(128) NULL,
    acknowledged_email            VARCHAR(320) NULL,
    ack_source                    VARCHAR(64) NULL,
    ack_note                      TEXT NULL,
    access_token_hash             CHAR(64) NULL,
    token_expires_at              TIMESTAMPTZ NULL,
    token_revoked_at              TIMESTAMPTZ NULL,
    supplementation_allowed       BOOLEAN NOT NULL DEFAULT FALSE,
    assigned_at                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    removed_at                    TIMESTAMPTZ NULL,
    created_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT engineer_task_assignee_role_check
        CHECK (assignment_role IN ('primary', 'collaborator')),
    CONSTRAINT engineer_task_assignee_delivery_check
        CHECK (delivery_status IN ('pending', 'sent', 'failed')),
    CONSTRAINT engineer_task_assignee_primary_required_check
        CHECK (NOT is_primary OR is_required_participant)
);

CREATE INDEX IF NOT EXISTS idx_engineer_task_assignee_task_round
    ON public.engineer_task_assignee
       (task_id, assignment_round, is_active, is_primary);

CREATE INDEX IF NOT EXISTS idx_engineer_task_assignee_email
    ON public.engineer_task_assignee
       (LOWER(engineer_email_snapshot), assigned_at DESC);

CREATE INDEX IF NOT EXISTS idx_engineer_task_assignee_ack
    ON public.engineer_task_assignee
       (task_id, acknowledged_at)
    WHERE is_active = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_engineer_task_assignee_round_email
    ON public.engineer_task_assignee
       (task_id, assignment_round, LOWER(engineer_email_snapshot));

CREATE UNIQUE INDEX IF NOT EXISTS uq_engineer_task_primary_per_round
    ON public.engineer_task_assignee
       (task_id, assignment_round)
    WHERE is_active = TRUE AND is_primary = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_engineer_task_access_token_hash
    ON public.engineer_task_assignee (access_token_hash)
    WHERE access_token_hash IS NOT NULL;

-- Backfill one legacy assignee per existing Phase 1 task.
INSERT INTO public.engineer_task_assignee (
    task_id,
    assignment_round,
    engineer_name_snapshot,
    engineer_email_snapshot,
    assignment_role,
    is_primary,
    is_required_participant,
    is_active,
    delivery_status,
    sent_at,
    last_sent_at,
    acknowledged_at,
    acknowledged_by,
    acknowledged_email,
    ack_source,
    ack_note,
    assigned_at,
    created_at,
    updated_at
)
SELECT
    task_id,
    1,
    COALESCE(NULLIF(engineer_name, ''), 'Legacy Engineer'),
    engineer_email,
    'primary',
    TRUE,
    TRUE,
    TRUE,
    CASE
        WHEN delivery_status = 'failed' THEN 'failed'
        WHEN delivery_status IN ('sent', 'acknowledged') THEN 'sent'
        ELSE 'pending'
    END,
    sent_at,
    sent_at,
    acknowledged_at,
    acknowledged_by,
    acknowledged_email,
    ack_source,
    ack_note,
    created_at,
    created_at,
    updated_at
FROM public.engineer_task task
WHERE engineer_email IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM public.engineer_task_assignee assignee
      WHERE assignee.task_id = task.task_id
        AND assignee.assignment_round = 1
        AND LOWER(assignee.engineer_email_snapshot) = LOWER(task.engineer_email)
  );

UPDATE public.engineer_task task
SET primary_assignee_id = assignee.assignee_id
FROM public.engineer_task_assignee assignee
WHERE task.primary_assignee_id IS NULL
  AND assignee.task_id = task.task_id
  AND assignee.assignment_round = task.current_assignment_round
  AND assignee.is_primary = TRUE
  AND assignee.is_active = TRUE;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'engineer_task_primary_assignee_fk'
    ) THEN
        ALTER TABLE public.engineer_task
            ADD CONSTRAINT engineer_task_primary_assignee_fk
            FOREIGN KEY (primary_assignee_id)
            REFERENCES public.engineer_task_assignee(assignee_id)
            ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'engineer_task_completion_assignee_fk'
    ) THEN
        ALTER TABLE public.engineer_task
            ADD CONSTRAINT engineer_task_completion_assignee_fk
            FOREIGN KEY (completion_submitted_by_assignee_id)
            REFERENCES public.engineer_task_assignee(assignee_id)
            ON DELETE SET NULL;
    END IF;
END
$$;

-- --------------------------------------------------------------------------
-- 4. Append-only task timeline.
-- --------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.engineer_task_event (
    event_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id               UUID NOT NULL
                          REFERENCES public.engineer_task(task_id)
                          ON DELETE CASCADE,
    assignee_id           UUID NULL
                          REFERENCES public.engineer_task_assignee(assignee_id)
                          ON DELETE SET NULL,
    event_type            VARCHAR(64) NOT NULL,
    event_status          VARCHAR(32) NULL,
    event_time            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_type            VARCHAR(32) NOT NULL DEFAULT 'system',
    actor_name            VARCHAR(128) NULL,
    actor_email           VARCHAR(320) NULL,
    message               TEXT NULL,
    error_message         TEXT NULL,
    event_data            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.engineer_task_event
    ALTER COLUMN event_time SET DEFAULT clock_timestamp();

CREATE INDEX IF NOT EXISTS idx_engineer_task_event_timeline
    ON public.engineer_task_event (task_id, event_time, event_id);

CREATE INDEX IF NOT EXISTS idx_engineer_task_event_type_time
    ON public.engineer_task_event (event_type, event_time DESC);

-- --------------------------------------------------------------------------
-- 5. Notification decisions, including aggregated suppression.
-- --------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.notification_decision (
    decision_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id                   UUID NULL
                              REFERENCES public.engineer_task(task_id)
                              ON DELETE SET NULL,
    source_alert_event_id     UUID NULL,
    station_id                VARCHAR(64) NOT NULL,
    batch_id                  VARCHAR(64) NULL,
    data_date                 DATE NULL,
    data_hour                 SMALLINT NULL,
    risk_level                VARCHAR(32) NOT NULL,
    decision_type             VARCHAR(32) NOT NULL,
    decision_reason           TEXT NULL,
    notification_fingerprint  VARCHAR(255) NOT NULL,
    cooldown_window_start     TIMESTAMPTZ NULL,
    cooldown_until            TIMESTAMPTZ NULL,
    suppressed_count          INTEGER NOT NULL DEFAULT 0,
    first_seen_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    evaluated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decision_data             JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT notification_decision_type_check
        CHECK (
            decision_type IN (
                'email_task_created',
                'dashboard_only',
                'suppressed',
                'cooldown_skipped'
            )
        ),
    CONSTRAINT notification_decision_hour_check
        CHECK (data_hour IS NULL OR data_hour BETWEEN 0 AND 23)
);

CREATE INDEX IF NOT EXISTS idx_notification_decision_created
    ON public.notification_decision (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_notification_decision_filter
    ON public.notification_decision
       (station_id, data_date, data_hour, decision_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_notification_decision_fingerprint
    ON public.notification_decision
       (notification_fingerprint, cooldown_until, last_seen_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_decision_source_email_task
    ON public.notification_decision (source_alert_event_id, decision_type)
    WHERE source_alert_event_id IS NOT NULL
      AND decision_type = 'email_task_created';

-- --------------------------------------------------------------------------
-- 6. Append-only structured engineer reports.
-- --------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.engineer_task_report (
    report_id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id                    UUID NOT NULL
                               REFERENCES public.engineer_task(task_id)
                               ON DELETE CASCADE,
    assignment_round           INTEGER NOT NULL DEFAULT 1,
    reported_by_assignee_id    UUID NOT NULL
                               REFERENCES public.engineer_task_assignee(assignee_id)
                               ON DELETE RESTRICT,
    report_type                VARCHAR(40) NOT NULL DEFAULT 'standard',
    observed_condition         TEXT NOT NULL,
    confirmed_cause            TEXT NULL,
    action_taken               TEXT NOT NULL,
    result_description         TEXT NOT NULL,
    remaining_issue            TEXT NULL,
    note                       TEXT NULL,
    supersedes_report_id       UUID NULL
                               REFERENCES public.engineer_task_report(report_id)
                               ON DELETE SET NULL,
    reported_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT engineer_task_report_type_check
        CHECK (
            report_type IN (
                'standard',
                'correction',
                'post_submission_addendum',
                'post_completion_supplement'
            )
        )
);

CREATE INDEX IF NOT EXISTS idx_engineer_task_report_task_time
    ON public.engineer_task_report (task_id, reported_at, report_id);

CREATE INDEX IF NOT EXISTS idx_engineer_task_report_assignee_time
    ON public.engineer_task_report
       (reported_by_assignee_id, reported_at DESC);

-- --------------------------------------------------------------------------
-- 7. Attachment metadata; physical files live in a persistent volume.
-- --------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.engineer_task_attachment (
    attachment_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id                   UUID NOT NULL
                              REFERENCES public.engineer_task(task_id)
                              ON DELETE CASCADE,
    report_id                 UUID NOT NULL
                              REFERENCES public.engineer_task_report(report_id)
                              ON DELETE CASCADE,
    uploaded_by_assignee_id   UUID NOT NULL
                              REFERENCES public.engineer_task_assignee(assignee_id)
                              ON DELETE RESTRICT,
    original_filename         VARCHAR(255) NOT NULL,
    stored_filename           VARCHAR(255) NOT NULL,
    relative_path             TEXT NOT NULL,
    mime_type                 VARCHAR(64) NOT NULL,
    size_bytes                BIGINT NOT NULL,
    sha256_hex                CHAR(64) NOT NULL,
    attachment_status         VARCHAR(32) NOT NULL DEFAULT 'active',
    retention_due_at          TIMESTAMPTZ NULL,
    deleted_at                TIMESTAMPTZ NULL,
    deleted_by                VARCHAR(128) NULL,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT engineer_task_attachment_size_check
        CHECK (size_bytes > 0 AND size_bytes <= 5242880),
    CONSTRAINT engineer_task_attachment_mime_check
        CHECK (
            mime_type IN (
                'image/jpeg',
                'image/png',
                'image/webp'
            )
        ),
    CONSTRAINT engineer_task_attachment_status_check
        CHECK (
            attachment_status IN (
                'active',
                'retention_due',
                'deleted'
            )
        )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_engineer_task_attachment_relative_path
    ON public.engineer_task_attachment (relative_path);

CREATE INDEX IF NOT EXISTS idx_engineer_task_attachment_task_created
    ON public.engineer_task_attachment (task_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_engineer_task_attachment_retention
    ON public.engineer_task_attachment
       (attachment_status, retention_due_at)
    WHERE attachment_status <> 'deleted';

COMMIT;
