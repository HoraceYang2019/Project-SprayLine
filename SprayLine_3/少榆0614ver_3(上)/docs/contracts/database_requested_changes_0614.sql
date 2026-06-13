-- 0614 requested DB changes for integration discussion, updated in 0614ver_3.
-- This file is a request note for Yu-Cheng / DB API owner, not the current official setup_db.sql.

-- 1) Store data quality flag in both aggregated sensor tables.
ALTER TABLE sensor_1min ADD COLUMN IF NOT EXISTS data_quality_flag VARCHAR(16)
  CHECK (data_quality_flag IN ('normal','interpolated'));

ALTER TABLE sensor_3min ADD COLUMN IF NOT EXISTS data_quality_flag VARCHAR(16)
  CHECK (data_quality_flag IN ('normal','interpolated'));

-- 2) Requested future prediction result table.
-- DB/API owner will confirm final naming and constraints.
CREATE TABLE IF NOT EXISTS future_prediction_result (
    prediction_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id            VARCHAR(32) NOT NULL REFERENCES batch_run(batch_id),
    station_id          VARCHAR(32),
    prediction_time     TIMESTAMPTZ NOT NULL,
    predicted_ok_rate   REAL,
    predicted_ng_count  INT,
    quality_score       REAL,
    risk_level          VARCHAR(8) CHECK (risk_level IN ('low','medium','high')),
    model_input_source  TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_future_prediction_batch ON future_prediction_result(batch_id, prediction_time DESC);
CREATE INDEX IF NOT EXISTS idx_future_prediction_station ON future_prediction_result(station_id, prediction_time DESC);
