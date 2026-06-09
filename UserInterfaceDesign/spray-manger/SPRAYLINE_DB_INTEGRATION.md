# Spray Manager UI - DB / Schema / Example Integration

這版前端已加入 Project-SprayLine Dashboard v15 / DB Schema v2 的資料整合層。

## 對應的 API / schema

- `/api/v1/lines/{line_id}/stations/latest` → `station_latest.schema.json` → 最新 runtime_signal、runtime_reference、runtime_metric、robot_pose。
- `/api/v1/lines/{line_id}/charts/quality-trend` → `quality_trend.schema.json` → QC / 品質分數 Past、Current、Future 曲線。
- `/api/v1/lines/{line_id}/charts/utilization-trend` → `utilization_trend.schema.json` → 稼動率 Past、Current、Future 曲線。
- `/api/v1/lines/{line_id}/charts/cycle-time-trend` → `cycle_time_trend.schema.json` → Cycle Time Past、Current、Future 曲線。
- `/api/v1/lines/{line_id}/diagnosis/latest` → `diagnosis_latest.schema.json` → 噴嘴、濾網、製程與 threshold 診斷。
- `/api/v1/lines/{line_id}/alerts/pending` → `pending_alerts.schema.json` → 待處理 warning / alarm，不正常才顯示。
- `/api/v1/lines/{line_id}/kpi` → `kpi_summary.schema.json` → 預測良率、預測 NG、line utilization、avg cycle time。
- `/api/v1/lines/{line_id}/prediction-accuracy` → `prediction_accuracy.schema.json` → 預測驗證。

## 使用方式

目前 `CONFIG.USE_MOCK_DATA = true`，UI 會用 `buildProjectSchemaMockBundle()` 模擬上述 schema 回傳。

未來真正接 API 時，修改 `dashboard.js`：

```js
const CONFIG = {
  USE_MOCK_DATA: false,
  API_USE_PROJECT_SCHEMA: true,
  API_BASE_URL: "http://127.0.0.1:5000",
  API_LINE_IDS: ["line_1", "line_2", "line_3"],
  API_TREND_TIMESTEP: "hour",
  API_DATE: "2026-06-09"
};
```

前端會自動呼叫各 route，把多個 schema response 合併成 Manager UI 需要的 `ManagerReport`。

## Manager UI 分析邏輯

- QC / 品質分數：主要使用 `quality_trend`、`kpi_summary`、`prediction_accuracy`、`station_latest.metric.quality_score_pct`。
- 稼動率：主要使用 `utilization_trend`、`station_latest.metric.utilization_pct`、`station_latest.metric.availability_pct`。
- Cycle Time：主要使用 `cycle_time_trend`、`station_latest.metric.cycle_time_sec`、`station_latest.reference.baseline_cycle_time_sec`。
- 可能原因：主要使用 `diagnosis_latest`、`pending_alerts`、`station_latest.components`、壓力、流量、堵塞率、噴幅目標範圍。

## 品質分數時間與資料來源補充

- 當天尚未完成 QC，因此當天畫面中的品質分數一律標示為「預測品質分數」。
- 隔天 QC 完成後，前一天的品質分數才可切換為「實際品質分數」。
- 每一個小時的品質分數不是單一 batch 的結果，而是該小時所有 batch 分數的平均值。
- 右側任務分派仍會顯示目前 API / DB 回傳的 batch ID，用來追蹤那一小時最需要回查的批次。

建議後端欄位：

```js
currentBatch: {
  batchId: "B20260612-011-S3",
  workOrderId: "WO-20260612-011",
  plannedPcs: 728,
  producedPcsToCurrent: 728,
  hourlyBatchCount: 3,
  qualityScoreSource: "hourly_all_batches_average",
  isPendingQc: true
}
```

## Actual QC rule

A production-day quality score is prediction-only until QC is completed. After the date is closed, historical review must query actual QC values from `qc_result` and should not reuse the stored prediction snapshot from the production day.

Recommended split:

- Current day: `ml_prediction_result.predicted_quality_score_pct`, aggregated by hour and all batches.
- Completed day: `qc_result.actual_quality_score_pct`, aggregated by hour and all batches.
- Batch impact: current batch ID comes from the runtime/batch API, but the displayed hourly quality score is still the average of all batches in that selected hour.
