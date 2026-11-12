-- Non-destructive migration for the Manager UI engineer notification workflow.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS engineer_task (
    task_id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_alert_event_id    UUID NULL,
    station_id               VARCHAR(64) NOT NULL,
    station_name             VARCHAR(128) NOT NULL,
    process_name             VARCHAR(128) NOT NULL,
    batch_id                 VARCHAR(64) NULL,
    batch_label              VARCHAR(128) NULL,
    data_date                VARCHAR(10) NULL,
    data_hour                VARCHAR(64) NULL,
    level                    VARCHAR(32) NOT NULL DEFAULT 'warning',
    issue                    TEXT NOT NULL,
    recommendation           TEXT NOT NULL,
    engineer_name            VARCHAR(128) NULL,
    engineer_email           VARCHAR(320) NOT NULL,
    delivery_status          VARCHAR(32) NOT NULL DEFAULT 'pending',
    delivery_error           TEXT NULL,
    sent_at                  TIMESTAMPTZ NULL,
    acknowledged_at          TIMESTAMPTZ NULL,
    acknowledged_by          VARCHAR(128) NULL,
    acknowledged_email       VARCHAR(320) NULL,
    ack_source               VARCHAR(64) NULL,
    ack_note                 TEXT NULL,
    payload_json             JSONB NOT NULL DEFAULT '{}'::jsonb,
    apps_script_response_json JSONB NULL,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT engineer_task_delivery_status_check
        CHECK (delivery_status IN ('pending', 'sent', 'failed', 'acknowledged'))
);

CREATE INDEX IF NOT EXISTS idx_engineer_task_created_at
    ON engineer_task (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_engineer_task_delivery_status
    ON engineer_task (delivery_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_engineer_task_station_id
    ON engineer_task (station_id, created_at DESC);

