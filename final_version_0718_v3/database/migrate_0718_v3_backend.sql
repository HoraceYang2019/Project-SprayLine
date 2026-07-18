-- ============================================================================
-- SprayLine 0718_v3 backend migration
-- Scope: Future/Ontology persistence, quality-score semantics and idempotency.
-- Safety: additive schema changes plus removal of already duplicated Future rows.
-- ============================================================================

ALTER TABLE future_prediction_result
    ADD COLUMN IF NOT EXISTS idempotency_key TEXT,
    ADD COLUMN IF NOT EXISTS estimated_defect_rate_pct REAL
        CHECK (estimated_defect_rate_pct BETWEEN 0 AND 100),
    ADD COLUMN IF NOT EXISTS quality_score_semantics VARCHAR(80)
        NOT NULL DEFAULT 'process_quality_score_not_measured_yield',
    ADD COLUMN IF NOT EXISTS rule_evaluations JSONB
        NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS cause_ids JSONB
        NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS response_ids JSONB
        NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS rule_sources JSONB
        NOT NULL DEFAULT '[]'::jsonb;

-- Existing rows receive a stable key derived from the same business identity
-- used by the V3 application: batch + station + prediction time + method.
UPDATE future_prediction_result
SET idempotency_key = md5(
    concat_ws(
        '|',
        batch_id,
        COALESCE(station_id, ''),
        EXTRACT(EPOCH FROM prediction_time)::text,
        COALESCE(prediction_method, '')
    )
)
WHERE idempotency_key IS NULL;

-- Keep the newest row when an older deployment has already written the same
-- logical prediction more than once. Related rows do not reference prediction_id.
WITH ranked_predictions AS (
    SELECT
        prediction_id,
        ROW_NUMBER() OVER (
            PARTITION BY idempotency_key
            ORDER BY created_at DESC, prediction_id DESC
        ) AS duplicate_rank
    FROM future_prediction_result
    WHERE idempotency_key IS NOT NULL
)
DELETE FROM future_prediction_result target
USING ranked_predictions ranked
WHERE target.prediction_id = ranked.prediction_id
  AND ranked.duplicate_rank > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_future_prediction_idempotency
    ON future_prediction_result (idempotency_key)
    WHERE idempotency_key IS NOT NULL;

COMMENT ON COLUMN future_prediction_result.quality_score IS
    'Derived process quality score (0-100); not measured product yield.';
COMMENT ON COLUMN future_prediction_result.predicted_ok_rate IS
    'Legacy compatibility field; current linear_trend_v1 writes the process-quality proxy, not measured yield.';
COMMENT ON COLUMN future_prediction_result.estimated_defect_rate_pct IS
    'Estimated process abnormal-risk percentage; not measured product defect rate.';
COMMENT ON COLUMN future_prediction_result.rule_evaluations IS
    'Future metric state/cause/response decisions produced by Ontology Runtime.';

