-- ============================================================
-- Patch: service metrics and prediction method write-back fields
-- Purpose:
--   Add fields used by IntegratedSprayLineService write_back=True without
--   rebuilding the whole PostgreSQL database.
-- ============================================================

ALTER TABLE batch_station_status
    ADD COLUMN IF NOT EXISTS quality_score_pct REAL CHECK (quality_score_pct BETWEEN 0 AND 100),
    ADD COLUMN IF NOT EXISTS qc_pct REAL CHECK (qc_pct BETWEEN 0 AND 100),
    ADD COLUMN IF NOT EXISTS estimated_defect_rate_pct REAL CHECK (estimated_defect_rate_pct BETWEEN 0 AND 100),
    ADD COLUMN IF NOT EXISTS estimated_film_thickness_um REAL,
    ADD COLUMN IF NOT EXISTS metric_updated_at TIMESTAMPTZ;

ALTER TABLE future_prediction_result
    ADD COLUMN IF NOT EXISTS prediction_method TEXT;

