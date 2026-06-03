"""
Dashboard v15 service contract.

This module defines service functions required by Dashboard v15 / DB Schema v2.
It intentionally does not return fake runtime data. Real implementations must bind
these functions to PostgreSQL/TimescaleDB, Redis cache, and FastAPI routes.
"""

from typing import Any, Dict, List, Optional


class DashboardV15Service:
    """Service-layer contract for Dashboard v15."""

    def get_station_dashboard_status(self, line_id) -> Dict[str, Any]:
        """站點摘要卡.

        API route: /api/v1/lines/{line_id}/summary
        Response schema: line_summary.schema.json
        DB tables/sources: production_line; component_master; component_health_snapshot
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def get_latest_runtime_window(self, line_id) -> Dict[str, Any]:
        """站點卡片 6 元件健康面板.

        API route: /api/v1/lines/{line_id}/stations/latest
        Response schema: station_latest.schema.json
        DB tables/sources: runtime_window; runtime_signal; runtime_reference; runtime_metric; robot_pose
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def get_latest_diagnosis(self, line_id) -> Dict[str, Any]:
        """元件異常詳情面板.

        API route: /api/v1/lines/{line_id}/diagnosis/latest
        Response schema: diagnosis_latest.schema.json
        DB tables/sources: diagnosis_result; filter_threshold; nozzle_threshold; process_threshold
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def get_metric_trend(self, line_id, metric_name, start_time, end_time) -> Dict[str, Any]:
        """時序檢視器 metric range query.

        API route: /api/v1/lines/{line_id}/metrics/{metric_name}/trend
        Response schema: metric_trend.schema.json
        DB tables/sources: runtime_window; runtime_metric
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def get_overall_status(self, line_id, date) -> Dict[str, Any]:
        """狀態 banner.

        API route: /api/v1/lines/{line_id}/status
        Response schema: overall_status.schema.json
        DB tables/sources: component_health_snapshot; ml_prediction_result; alert_log
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def get_kpi_summary(self, line_id, date) -> Dict[str, Any]:
        """KPI 卡.

        API route: /api/v1/lines/{line_id}/kpi
        Response schema: kpi_summary.schema.json
        DB tables/sources: ml_prediction_result; runtime_metric; part_history; qc_result
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def get_yield_comparison(self, line_id, date) -> Dict[str, Any]:
        """良率趨勢昨日/今日並排.

        API route: /api/v1/lines/{line_id}/charts/yield-comparison
        Response schema: yield_comparison.schema.json
        DB tables/sources: qc_result; part_history; batch_run; ml_prediction_result
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def get_quality_trend(self, line_id, timestep) -> Dict[str, Any]:
        """品質風險趨勢.

        API route: /api/v1/lines/{line_id}/charts/quality-trend
        Response schema: quality_trend.schema.json
        DB tables/sources: qc_result; ml_prediction_result
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def get_utilization_trend(self, line_id, timestep) -> Dict[str, Any]:
        """各站稼動率趨勢.

        API route: /api/v1/lines/{line_id}/charts/utilization-trend
        Response schema: utilization_trend.schema.json
        DB tables/sources: runtime_metric
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def get_cycle_time_trend(self, line_id, timestep) -> Dict[str, Any]:
        """Cycle Time 趨勢.

        API route: /api/v1/lines/{line_id}/charts/cycle-time-trend
        Response schema: cycle_time_trend.schema.json
        DB tables/sources: part_history
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def list_batches_filtered(self, line_id, date, risk_levels, start_time, end_time) -> Dict[str, Any]:
        """Batch 彙整表含風險/時段篩選.

        API route: /api/v1/lines/{line_id}/batches
        Response schema: batches_filtered.schema.json
        DB tables/sources: batch_run; qc_result; ml_prediction_result
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def list_pending_alerts(self, line_id) -> Dict[str, Any]:
        """待處理警示 Drawer.

        API route: /api/v1/lines/{line_id}/alerts/pending
        Response schema: pending_alerts.schema.json
        DB tables/sources: alert_log; diagnosis_result; ml_prediction_result; qc_result
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def acknowledge_alert(self, alert_id, operator_id) -> Dict[str, Any]:
        """標記警示已處理.

        API route: /api/v1/alerts/{alert_id}/acknowledge
        Response schema: alert_acknowledge.schema.json
        DB tables/sources: alert_log
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def trigger_alert(self, source_type, source_id, line_id) -> Dict[str, Any]:
        """由 diagnosis engine / ML 觸發警示.

        API route: /api/v1/alerts/trigger
        Response schema: alert_trigger.schema.json
        DB tables/sources: alert_log; diagnosis_result; ml_prediction_result; qc_result
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def get_prediction_accuracy(self, line_id, date) -> Dict[str, Any]:
        """預測準確度 Drawer.

        API route: /api/v1/lines/{line_id}/prediction-accuracy
        Response schema: prediction_accuracy.schema.json
        DB tables/sources: qc_result; ml_prediction_result
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def get_diagnosis_timeline(self, line_id, category, start_time, end_time) -> Dict[str, Any]:
        """診斷時序 timeline.

        API route: /api/v1/lines/{line_id}/diagnosis/timeline
        Response schema: diagnosis_timeline.schema.json
        DB tables/sources: diagnosis_result; filter_threshold; nozzle_threshold; process_threshold
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def get_station_risk_detail(self, line_id) -> Dict[str, Any]:
        """站點風險詳情.

        API route: /api/v1/lines/{line_id}/risk-detail
        Response schema: station_risk_detail.schema.json
        DB tables/sources: diagnosis_result; ml_prediction_result; alert_log
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def get_ml_feature_input(self, part_uuid) -> Dict[str, Any]:
        """取得 ML input features.

        API route: /api/v1/parts/{part_uuid}/ml-features
        Response schema: ml_feature_input.schema.json
        DB tables/sources: ml_feature_snapshot
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def get_latest_prediction(self, part_uuid) -> Dict[str, Any]:
        """取得最新預測結果.

        API route: /api/v1/parts/{part_uuid}/prediction/latest
        Response schema: latest_prediction.schema.json
        DB tables/sources: ml_prediction_result
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")

    def get_omniverse_validation_result(self, part_uuid) -> Dict[str, Any]:
        """取得 Omniverse 驗證結果.

        API route: /api/v1/parts/{part_uuid}/omniverse/validation
        Response schema: omniverse_validation.schema.json
        DB tables/sources: omniverse_sync_log; trajectory_result
        """
        raise NotImplementedError("Bind this Dashboard v15 contract to DB/API implementation; do not return fake data.")
