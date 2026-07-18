from __future__ import annotations

from typing import Any, Dict
from datetime import datetime, timezone
import logging

from fastapi import FastAPI, Body, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from shaoyu_ui_bridge import (
    build_integrated_request_from_ui,
    build_ui_summary_output,
    build_ui_station_detail_output,
    build_ui_component_detail_output,
    normalize_component_name,
)

from versionb_loader import get_versionb_status
from database_status import check_database_status
from versionb_alert_adapter import (
    get_alerts as VersionBGetAlerts,
    get_alert_card as VersionBGetAlertCard,
    get_responses_for_cause as VersionBGetResponsesForCause,
    get_unacknowledged_alerts as VersionBGetUnacknowledgedAlerts,
    acknowledge_alert as VersionBAcknowledgeAlert,
)

from service_orchestration_adapter import (
    get_service_orchestration_status,
    build_integrated_request as BuildOrchestrationIntegratedRequest,
    run_integrated_service_query,
    build_future_prediction_payload_for_api,
    save_future_prediction_payload_for_api,
    run_monitoring_once_for_api,
    get_troubleshooting_matrix_for_api,
    get_state_recommendations_for_api,
)
from event_rule_service.runtime_rule_classifier import classify_sensor_value
from integrated_service.quality_score_common import quality_score_from_formal_row
from manager_dashboard_service import build_manager_dashboard_payload
from engineer_task_router import router as engineer_task_router
from engineer_task_workflow_router import manager_workflow_router, token_access_router
from manager_date_service import (
    LINE_TO_STATION,
    STATION_TO_LINE,
    get_manager_available_dates,
    get_manager_distinct_batch_count_for_date,
    get_manager_sensor_rows_for_date,
    get_manager_station_hourly_aggregates,
    get_manager_station_rows_for_hour,
    resolve_manager_date_hour,
    ManagerDateSelectionError,
)


app = FastAPI(
    title="SprayLine API final_version_0718_v3",
    description=(
        "Unified API for SprayLine past/current/future UI query and "
        "Shaoyu service orchestration."
    ),
    version="0718.3",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(engineer_task_router)
app.include_router(manager_workflow_router)
app.include_router(token_access_router)

LOGGER = logging.getLogger(__name__)


def _json_error(stage: str, exc: BaseException) -> Dict[str, Any]:
    LOGGER.exception("API request failed at %s", stage)
    return {
        "success": False,
        "stage": stage,
        "error_type": exc.__class__.__name__,
        "error_message": str(exc),
    }


def _service_json_response(result: Dict[str, Any]) -> JSONResponse:
    """Turn adapter results into real HTTP success/error responses."""
    content = dict(result or {})
    status_code = int(content.pop("_http_status", 200 if content.get("success") is not False else 500))
    return JSONResponse(status_code=status_code, content=content)


def _run_integrated_for_ui(request: Dict[str, Any], fallback_to_demo: bool = False) -> Dict[str, Any]:
    """Run Shaoyu integrated service for formal UI/API endpoints only.

    Demo fallback is intentionally disabled. The fallback_to_demo argument is kept
    only to avoid breaking old callers, but it is ignored in formal DB mode.
    """
    formal_request = _force_integrated_request(request)
    integrated_request = build_integrated_request_from_ui(formal_request)
    try:
        result = run_integrated_service_query(request=integrated_request, write_back=False)
        if result.get("success") is True:
            data = result.get("data", {})
            if isinstance(data, dict):
                data.setdefault("source_mode", "integrated")
            return {
                "success": True,
                "source_mode": "integrated",
                "data": data,
            }
        if isinstance(result, dict):
            result.setdefault("source_mode", "integrated")
        return result
    except Exception as exc:
        err = _json_error("_run_integrated_for_ui", exc)
        err["source_mode"] = "integrated"
        return err


def _force_integrated_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of request that is guaranteed to use formal DB/integrated mode."""
    formal_request = dict(request or {})
    formal_request["source_mode"] = "integrated"
    return formal_request


def _formal_db_error(message: str, detail: Dict[str, Any] | None = None, status_code: int = 500) -> JSONResponse:
    content: Dict[str, Any] = {
        "success": False,
        "source_mode": "integrated",
        "error_type": "FormalDbOnlyError",
        "message": message,
    }
    if detail is not None:
        content["detail"] = detail
    return JSONResponse(status_code=status_code, content=content)


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


# Station-level production config (not in sensor_1min, sourced from line setup)
_STATION_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "line_1": {"utilization_pct": 78.0, "cycle_time_sec": 42.0, "recipe_name": "Primer_A",
               "baseline_utilization_pct": 80.0, "baseline_cycle_time_sec": 42.0},
    "line_2": {"utilization_pct": 72.0, "cycle_time_sec": 47.0, "recipe_name": "Topcoat_B",
               "baseline_utilization_pct": 78.0, "baseline_cycle_time_sec": 47.0},
    "line_3": {"utilization_pct": 61.0, "cycle_time_sec": 55.0, "recipe_name": "Gold_C",
               "baseline_utilization_pct": 75.0, "baseline_cycle_time_sec": 55.0},
}

# Formal DB step2 constants: use only spray0621verC/dataprocess fields.
_FILTER_FAULT_BAR = 0.70
_TARGET_FLOW_ML_MIN = 115.0
_TARGET_AIR_PRESSURE_BAR = 3.2
_STATION_TARGET_WIDTH_MM = {"line_1": 120.0, "line_2": 100.0, "line_3": 82.0}


def _quality_score_from_point(point: Dict[str, Any], line_id: str = "") -> float:
    """Estimate quality score (0-100) from formal DB available fields.

    It is based on process-condition deviations, not actual inspection yield.
    """
    existing = point.get("quality_score_pct") or point.get("quality_score")
    if existing is not None:
        return max(0.0, min(100.0, round(_number(existing), 1)))

    flow = point.get("paint_flow_ml_min")
    pressure = point.get("air_pressure_bar")
    width = point.get("spray_width_mm")
    path_err = point.get("path_error_mm")
    target_width = _STATION_TARGET_WIDTH_MM.get(line_id, _number(point.get("target_spray_width_mm"), 100.0))

    penalty = 0.0
    if flow is not None:
        penalty += min(30.0, abs(_number(flow) - _TARGET_FLOW_ML_MIN) / _TARGET_FLOW_ML_MIN * 100.0 * 2.0)
    if pressure is not None:
        penalty += min(25.0, abs(_number(pressure) - _TARGET_AIR_PRESSURE_BAR) / _TARGET_AIR_PRESSURE_BAR * 100.0 * 2.0)
    if width is not None and target_width:
        penalty += min(30.0, abs(_number(width) - target_width) / target_width * 100.0 * 2.0)
    if path_err is not None:
        penalty += min(20.0, _number(path_err) / 0.15 * 20.0)
    return max(0.0, min(100.0, round(100.0 - penalty, 1)))


def _state_for_component(component_key: str, metrics: Dict[str, Any]) -> str:
    component_metrics = {
        "filter_mesh": ["filter_diff_pressure_bar"],
        "robot_arm": ["servo_torque_load_pct", "path_error_mm"],
        "nozzle": ["paint_flow_ml_min"],
    }
    rank = {"normal": 1, "warning": 2, "fault": 3}
    states = []
    for metric in component_metrics.get(component_key, []):
        if metrics.get(metric) is None:
            continue
        state = classify_sensor_value(metric, metrics.get(metric)).get("state")
        if state in rank:
            states.append(str(state))
    return max(states, key=lambda item: rank[item]) if states else "normal"


def _diagnoses_for_station(station: Dict[str, Any], metrics: Dict[str, Any]) -> list[Dict[str, Any]]:
    diagnoses: list[Dict[str, Any]] = []
    rule_evaluations = (station.get("current_snapshot") or {}).get("rule_evaluations") or {}
    for metric, result in rule_evaluations.items():
        severity = result.get("state")
        if severity not in {"warning", "fault"}:
            continue
        responses = list(result.get("response_ids") or [])
        diagnoses.append({
            "category": result.get("component") or "sensor",
            "state_label": result.get("issue") or f"{metric} {severity}",
            "severity": severity,
            "confidence": 0.9,
            "evidence": f"{metric} = {result.get('value')}",
            "cause_id": result.get("cause_id"),
            "action": ", ".join(responses) if responses else "請檢查對應製程條件",
            "response_ids": responses,
            "rule_source": result.get("rule_source"),
            "rule_engine": result.get("rule_engine"),
        })
    if diagnoses:
        return diagnoses

    state = station.get("state", "normal")
    if state in {"warning", "fault"}:
        diagnoses.append({
            "category": "sensor",
            "state_label": "站點狀態異常" if state == "fault" else "站點狀態注意",
            "severity": state,
            "confidence": 0.9,
            "evidence": f"station state = {state}",
            "action": "請檢查站點感測值與維護建議",
        })

    filter_pressure = _number(metrics.get("filter_diff_pressure_bar"))
    if filter_pressure > 0.30:
        diagnoses.append({
            "category": "pdm",
            "state_label": "濾網壓差偏高",
            "severity": "fault" if filter_pressure > 0.50 else "warning",
            "confidence": 0.88,
            "evidence": f"filter_diff_pressure_bar = {filter_pressure:.2f}",
            "action": "建議檢查或更換濾網",
        })

    torque = _number(metrics.get("servo_torque_load_pct"))
    if torque > 60:
        diagnoses.append({
            "category": "pdm",
            "state_label": "機械手臂負載偏高",
            "severity": "fault" if torque > 80 else "warning",
            "confidence": 0.84,
            "evidence": f"servo_torque_load_pct = {torque:.1f}",
            "action": "建議檢查伺服馬達與路徑負載",
        })

    if not diagnoses:
        diagnoses.append({
            "category": "quality",
            "state_label": "正常",
            "severity": "normal",
            "confidence": 0.95,
            "evidence": "所有主要監控指標在可接受範圍",
            "action": "持續監控",
        })
    return diagnoses


def _trend_for_station(station: Dict[str, Any], trend_type: str, line_id: str = "") -> Dict[str, Any]:
    """Build trend in format expected by Manager dashboard.js.

    trend_type="quality"     → {actual_series: [{hour, quality_score_pct}], predicted_series: [], forecast_series: []}
    trend_type="utilization" → {series: [{hour, utilization_pct}]}
    trend_type="cycle_time"  → {series: [{hour, cycle_time_sec}]}
    """
    raw_points = (station.get("time_series") or {}).get("points", [])
    if not isinstance(raw_points, list):
        raw_points = []
    defaults = _STATION_DEFAULTS.get(line_id, {})

    parsed: list[tuple[datetime, Dict[str, Any]]] = []
    for pt in raw_points:
        ts_str = pt.get("timestamp")
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
        except Exception:
            continue
        parsed.append((ts, pt))

    # Bucket by actual wall-clock hour-of-day (0-23), not elapsed time since the
    # first row. The query window is exactly 24h ending at "now", so every
    # hour-of-day appears at most once; this keeps bucket indices aligned with
    # the UI's fixed 00:00-23:00 axis and its "Current HH:00" marker (which is
    # derived from the same anchor timestamp's hour-of-day).
    if trend_type == "quality":
        actual_series = []
        for ts, pt in parsed:
            actual_series.append({"hour": ts.hour, "quality_score_pct": _quality_score_from_point(pt, line_id)})
        return {"actual_series": actual_series, "predicted_series": [], "forecast_series": []}

    if trend_type == "utilization":
        util_val = defaults.get("utilization_pct", 72.0)
        series = []
        for ts, _pt in parsed:
            series.append({"hour": ts.hour, "utilization_pct": util_val})
        return {"series": series}

    if trend_type == "cycle_time":
        cycle_val = defaults.get("cycle_time_sec", 47.0)
        series = []
        for ts, _pt in parsed:
            series.append({"hour": ts.hour, "cycle_time_sec": cycle_val})
        return {"series": series}

    return {}


def _iso_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _current_batch_for_bundle() -> Dict[str, Any] | None:
    try:
        from integration_adapter.database_versionb_adapter import (
            get_connection,
            get_latest_batches,
            get_running_batches,
        )

        conn = get_connection()
        try:
            running_batches = get_running_batches(conn) or []
            batch = running_batches[0] if running_batches else None
            if batch is None:
                latest_batches = get_latest_batches(conn, limit=1) or []
                batch = latest_batches[0] if latest_batches else None
        finally:
            conn.close()
    except Exception:
        return None

    if not batch:
        return None

    return {
        "batchId": batch.get("batch_id"),
        "status": batch.get("status"),
        "startTime": _iso_or_none(batch.get("start_time")),
        "endedTime": _iso_or_none(batch.get("ended_time")),
    }


_MANAGER_FILTER_FAULT_BAR = 0.50


def _manager_quality_score_from_point(point: Dict[str, Any]) -> float:
    """Restore the 2026-06-29 Manager-only quality-score approximation."""
    filter_p = _number(point.get("filter_diff_pressure_bar"), 0.15)
    torque = _number(point.get("servo_torque_load_pct"), 40.0)
    path_err = _number(point.get("path_error_mm"), 0.0)
    filter_dev = max(0.0, (filter_p - 0.15) / 0.35)
    torque_dev = max(0.0, (torque - 40.0) / 40.0)
    path_dev = max(0.0, path_err / 2.0)
    score = 100.0 - filter_dev * 30.0 - torque_dev * 20.0 - path_dev * 10.0
    return max(50.0, min(100.0, round(score, 1)))


def _estimate_maintainability_pct(point: Dict[str, Any]) -> float:
    filter_p = _number(point.get("filter_diff_pressure_bar"), 0.15)
    torque = _number(point.get("servo_torque_load_pct"), 40.0)
    penalty = max(0.0, (filter_p - 0.15) / 0.35) * 25.0
    penalty += max(0.0, (torque - 40.0) / 40.0) * 18.0
    score = 100.0 - penalty
    return max(60.0, min(100.0, round(score, 1)))


def _derive_station_signal_state(metrics: Dict[str, Any]) -> str:
    levels = [
        _state_for_component("nozzle", metrics),
        _state_for_component("filter_mesh", metrics),
        _state_for_component("robot_arm", metrics),
    ]
    if "fault" in levels:
        return "fault"
    if "warning" in levels:
        return "warning"
    return "running"


def _estimate_hourly_utilization_pct(hourly_row: Dict[str, Any] | None) -> float:
    row_count = _number((hourly_row or {}).get("row_count"), 0.0)
    return max(0.0, min(100.0, round(row_count / 60.0 * 100.0, 1)))


def _estimate_station_hourly_ng_pcs(quality_score_pct: float, hourly_row: Dict[str, Any] | None) -> int:
    row_count = max(0, int(_number((hourly_row or {}).get("row_count"), 0.0)))
    return max(0, round(row_count * max(0.0, 100.0 - quality_score_pct) / 100.0))


def _build_selected_batch_payload(conn, batch_id: str | None) -> Dict[str, Any] | None:
    if not batch_id:
        return None

    from db_batch import get_batch_by_id

    batch = get_batch_by_id(conn, batch_id)
    if not batch:
        return {"batchId": batch_id, "status": None, "startTime": None, "endedTime": None}

    return {
        "batchId": batch.get("batch_id"),
        "status": batch.get("status"),
        "startTime": _iso_or_none(batch.get("start_time")),
        "endedTime": _iso_or_none(batch.get("ended_time")),
    }


def _build_manager_trends_for_station(
    line_id: str,
    hourly_rows: Dict[int, Dict[str, Any]],
) -> Dict[str, Dict[str, list[Dict[str, Any]]]]:
    defaults = _STATION_DEFAULTS.get(line_id, {})
    quality_series: list[Dict[str, Any]] = []
    utilization_series: list[Dict[str, Any]] = []
    cycle_series: list[Dict[str, Any]] = []

    for hour in sorted(hourly_rows.keys()):
        row = hourly_rows.get(hour) or {}
        pseudo_point = {
            "filter_diff_pressure_bar": row.get("avg_filter_diff_pressure_bar"),
            "servo_torque_load_pct": row.get("avg_servo_torque_load_pct"),
            "path_error_mm": row.get("max_path_error_mm") or row.get("avg_path_error_mm"),
        }
        quality_series.append({
            "hour": hour,
            "quality_score_pct": _manager_quality_score_from_point(pseudo_point),
        })
        utilization_series.append({
            "hour": hour,
            "utilization_pct": _estimate_hourly_utilization_pct(row),
        })
        cycle_series.append({
            "hour": hour,
            "cycle_time_sec": defaults.get("cycle_time_sec", 47.0),
        })

    return {
        "quality": {
            "actual_series": quality_series,
            "predicted_series": [],
            "forecast_series": [],
        },
        "utilization": {"series": utilization_series},
        "cycle": {"series": cycle_series},
    }


def _build_manager_bundle_from_database(
    conn,
    date: str | None = None,
    hour: int | None = None,
    batch_id: str | None = None,
) -> Dict[str, Any]:
    from db_alert import get_unacknowledged_alerts

    selection = resolve_manager_date_hour(conn, date=date, hour=hour)
    selected_batch_id = str(batch_id).strip() if batch_id not in (None, "") else None
    selection["selectedBatchId"] = selected_batch_id
    station_rows = get_manager_station_rows_for_hour(
        conn,
        selection["selectedDate"],
        selection["selectedHour"],
    )
    hourly_rows = get_manager_station_hourly_aggregates(conn, selection["selectedDate"])
    daily_sensor_rows = get_manager_sensor_rows_for_date(conn, selection["selectedDate"])
    daily_distinct_batch_count = get_manager_distinct_batch_count_for_date(conn, selection["selectedDate"])

    normalized_daily_rows: list[Dict[str, Any]] = []
    for row in daily_sensor_rows:
        station_id = str(row.get("station_id") or "")
        normalized_daily_rows.append(
            {
                "lineId": STATION_TO_LINE.get(station_id, ""),
                "stationId": station_id,
                "batchId": str(row.get("batch_id") or "").strip() or None,
                "timestamp": _iso_or_none(row.get("ts")),
                "dataHour": int(row.get("data_hour") or 0),
                "paint_flow_ml_min": _number(row.get("paint_flow_ml_min"), 0.0),
                "air_pressure_bar": _number(row.get("air_pressure_bar"), 0.0),
                "spray_width_mm": _number(row.get("spray_width_mm"), 0.0),
                "path_error_mm": _number(row.get("path_error_mm"), 0.0),
                "quality_score_pct": quality_score_from_formal_row(row, station_id),
            }
        )

    bundle: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Manager Dashboard API",
        "selectionMeta": selection,
        "currentBatch": _build_selected_batch_payload(conn, selection.get("anchorBatchId")),
        "stationLatest": {},
        "diagnosisLatest": {},
        "pendingAlerts": {},
        "kpiSummary": {},
        "predictionAccuracy": {},
        "qualityTrend": {},
        "utilizationTrend": {},
        "cycleTimeTrend": {},
        "managerDataset": {
            "selectedBatchId": selected_batch_id,
            "defaultBatchModeLabel": "全部批號 / 該小時累計",
            "dailyDistinctBatchCount": daily_distinct_batch_count,
            "dailySensorRows": normalized_daily_rows,
            "activeAlertsByLine": {},
        },
    }

    for line_id, station_id in LINE_TO_STATION.items():
        station_row = station_rows.get(station_id) or {}
        station_hourly_rows = hourly_rows.get(station_id, {})
        selected_hour_row = station_hourly_rows.get(selection["selectedHour"])
        defaults = _STATION_DEFAULTS.get(line_id, {})

        signal_metrics = {
            "filter_diff_pressure_bar": station_row.get("filter_diff_pressure_bar"),
            "servo_torque_load_pct": station_row.get("servo_torque_load_pct"),
            "path_error_mm": station_row.get("path_error_mm"),
            "spray_width_mm": station_row.get("spray_width_mm"),
            "target_spray_width_mm": station_row.get("spray_width_mm") or 116.0,
        }
        quality_score = _manager_quality_score_from_point(signal_metrics)
        utilization_pct = _estimate_hourly_utilization_pct(selected_hour_row)
        cycle_time_sec = defaults.get("cycle_time_sec", 47.0)
        filter_bar = _number(station_row.get("filter_diff_pressure_bar"), 0.15)
        clog_rate_pct = round(min(100.0, filter_bar / _MANAGER_FILTER_FAULT_BAR * 100.0), 1)
        signal_state = _derive_station_signal_state(signal_metrics)
        components = [
            {"component_key": "nozzle", "level": _state_for_component("nozzle", signal_metrics)},
            {"component_key": "filter_mesh", "level": _state_for_component("filter_mesh", signal_metrics)},
            {"component_key": "robot_arm", "level": _state_for_component("robot_arm", signal_metrics)},
        ]

        alert_items = []
        station_alerts = []
        try:
            station_alerts = get_unacknowledged_alerts(conn, station_id=station_id, limit=50) or []
            active_batch_id = selected_batch_id or selection.get("anchorBatchId")
            alert_items = [
                item for item in station_alerts
                if not active_batch_id or item.get("batch_id") == active_batch_id
            ]
        except Exception:
            station_alerts = []
            alert_items = []

        bundle["managerDataset"]["activeAlertsByLine"][line_id] = station_alerts

        bundle["stationLatest"][line_id] = {
            "timestamp": _iso_or_none(station_row.get("ts")),
            "signal": {
                "pressure_bar": _number(
                    station_row.get("air_pressure_bar"),
                    _number(selected_hour_row.get("avg_air_pressure_bar"), 0.0) if selected_hour_row else 0.0,
                ),
                "flow_rate_ml_min": _number(
                    station_row.get("paint_flow_ml_min"),
                    _number(selected_hour_row.get("avg_paint_flow_ml_min"), 0.0) if selected_hour_row else 0.0,
                ),
                "spray_width_mm": _number(
                    station_row.get("spray_width_mm"),
                    _number(selected_hour_row.get("avg_spray_width_mm"), 0.0) if selected_hour_row else 0.0,
                ),
                "temperature_c": 0.0,
                "state": signal_state,
                "recipe_name": defaults.get("recipe_name") or f"{station_id}_recipe",
            },
            "reference": {
                "target_min_mm": _number(station_row.get("spray_width_mm"), 110.0) * 0.95,
                "target_max_mm": _number(station_row.get("spray_width_mm"), 110.0) * 1.05,
                "baseline_pressure_bar": _number(
                    station_row.get("air_pressure_bar"),
                    _number(selected_hour_row.get("avg_air_pressure_bar"), 2.5) if selected_hour_row else 2.5,
                ),
                "baseline_flow_rate_ml_min": _number(
                    station_row.get("paint_flow_ml_min"),
                    _number(selected_hour_row.get("avg_paint_flow_ml_min"), 110.0) if selected_hour_row else 110.0,
                ),
                "baseline_quality_score_pct": 94.0,
                "baseline_utilization_pct": defaults.get("baseline_utilization_pct", 80.0),
                "baseline_cycle_time_sec": defaults.get("baseline_cycle_time_sec", cycle_time_sec),
            },
            "metric": {
                "quality_score_pct": quality_score,
                "utilization_pct": utilization_pct,
                "cycle_time_sec": cycle_time_sec,
                "clog_rate_pct": clog_rate_pct,
                "availability_pct": utilization_pct,
                "maintainability_pct": _estimate_maintainability_pct(signal_metrics),
            },
            "components": components,
        }

        bundle["diagnosisLatest"][line_id] = {
            "diagnoses": _diagnoses_for_station({"state": signal_state}, signal_metrics)
        }
        bundle["pendingAlerts"][line_id] = {
            "total": len(alert_items),
            "alerts": alert_items,
        }
        bundle["kpiSummary"][line_id] = {
            "predicted_ok_rate": quality_score,
            "line_utilization": utilization_pct,
            "avg_cycle_time_s": cycle_time_sec,
            "predicted_ng_pcs": _estimate_station_hourly_ng_pcs(quality_score, selected_hour_row),
        }
        bundle["predictionAccuracy"][line_id] = {"accuracy_pct": 88.0}

        trends = _build_manager_trends_for_station(line_id, station_hourly_rows)
        bundle["qualityTrend"][line_id] = trends["quality"]
        bundle["utilizationTrend"][line_id] = trends["utilization"]
        bundle["cycleTimeTrend"][line_id] = trends["cycle"]

    return bundle


@app.get("/api/v1/bundle")
def GetV1Bundle(date: str | None = None):
    # window_minutes=1440 (24h) so quality/utilization/cycle-time trend charts have
    # one data point per hour for the day; current snapshot still uses the latest row.
    result = _run_integrated_for_ui(
        _force_integrated_request({"slider_value": 0, "line_scope": "all", "window_minutes": 1440}),
        fallback_to_demo=False,
    )
    if not isinstance(result, dict) or result.get("success") is not True:
        return _formal_db_error("/api/v1/bundle requires formal DB data; demo fallback is disabled.", result if isinstance(result, dict) else None)
    data = result.get("data", {}) if isinstance(result, dict) else {}
    stations = data.get("stations", []) if isinstance(data, dict) else []
    if not isinstance(stations, list):
        stations = []

    bundle: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "currentBatch": _current_batch_for_bundle(),
        "stationLatest": {},
        "diagnosisLatest": {},
        "pendingAlerts": {},
        "kpiSummary": {},
        "predictionAccuracy": {},
        "qualityTrend": {},
        "utilizationTrend": {},
        "cycleTimeTrend": {},
    }

    for index, station in enumerate(stations, start=1):
        if not isinstance(station, dict):
            continue
        line_id = station.get("line_id") or f"line_{index}"
        metrics = station.get("metrics") or {}
        snapshot = station.get("current_snapshot") or {}
        future = station.get("future_prediction") or {}
        source = {**metrics, **snapshot}
        state = station.get("state", "normal")
        signal_state = "running" if state == "normal" else state
        st_defaults = _STATION_DEFAULTS.get(line_id, {})

        pressure = _number(source.get("air_pressure_bar") or source.get("pressure_bar"), 2.5)
        flow = _number(source.get("paint_flow_ml_min") or source.get("flow_rate_ml_min"), 0.0)
        width = _number(source.get("spray_width_mm"), 0.0)
        temp = _number(source.get("temperature_c"), 0.0)
        quality = _number(source.get("quality_score_pct") or future.get("quality_score"), _quality_score_from_point(source, line_id))
        # utilization and cycle_time are production line config, not in sensor_1min
        utilization = st_defaults.get("utilization_pct", 72.0)
        cycle_time = st_defaults.get("cycle_time_sec", 47.0)
        recipe_name = (station.get("recipe_name") or source.get("recipe_name")
                       or st_defaults.get("recipe_name") or f"Recipe_{index}")
        # Formal DB clog index: 0.10 bar healthy, 0.70 bar fault threshold.
        filter_bar = _number(source.get("filter_diff_pressure_bar"), 0.15)
        clog_rate = _number(source.get("filter_clog_index_pct"), round(min(100.0, max(0.0, (filter_bar - 0.10) / (_FILTER_FAULT_BAR - 0.10) * 100.0)), 1))

        components = [
            {"component_key": "nozzle", "level": _state_for_component("nozzle", source)},
            {"component_key": "filter_mesh", "level": _state_for_component("filter_mesh", source)},
            {"component_key": "robot_arm", "level": _state_for_component("robot_arm", source)},
        ]

        bundle["stationLatest"][line_id] = {
            "signal": {
                "pressure_bar": pressure,
                "flow_rate_ml_min": flow,
                "spray_width_mm": width,
                "temperature_c": temp,
                "state": signal_state,
                "recipe_name": recipe_name,
            },
            "reference": {
                "target_min_mm": _number(source.get("target_min_mm"), width * 0.9 if width else 95.0),
                "target_max_mm": _number(source.get("target_max_mm"), width * 1.1 if width else 125.0),
                "baseline_pressure_bar": pressure,
                "baseline_flow_rate_ml_min": flow,
                "baseline_quality_score_pct": 94.0,
                "baseline_utilization_pct": st_defaults.get("baseline_utilization_pct", 80.0),
                "baseline_cycle_time_sec": st_defaults.get("baseline_cycle_time_sec", cycle_time),
            },
            "metric": {
                "quality_score_pct": quality,
                "utilization_pct": utilization,
                "cycle_time_sec": cycle_time,
                "clog_rate_pct": clog_rate,
                "availability_pct": _number(source.get("availability_pct"), 95.0),
                "maintainability_pct": _number(source.get("maintainability_pct"), 90.0),
            },
            "components": components,
        }

        try:
            alerts = VersionBGetUnacknowledgedAlerts(station.get("station_id") or line_id)
            alert_items = alerts if isinstance(alerts, list) else []
        except Exception:
            alert_items = []

        bundle["diagnosisLatest"][line_id] = {"diagnoses": _diagnoses_for_station(station, source)}
        bundle["pendingAlerts"][line_id] = {"total": len(alert_items), "alerts": alert_items}
        bundle["kpiSummary"][line_id] = {
            "predicted_ok_rate": _number(future.get("predicted_ok_rate"), quality),
            "line_utilization": utilization,
            "avg_cycle_time_s": cycle_time,
            "predicted_ng_pcs": int(_number(future.get("predicted_ng_count"), 0)),
        }
        bundle["predictionAccuracy"][line_id] = {"accuracy_pct": _number(source.get("prediction_accuracy_pct"), 88.0)}
        bundle["qualityTrend"][line_id] = _trend_for_station(station, "quality", line_id)
        bundle["utilizationTrend"][line_id] = _trend_for_station(station, "utilization", line_id)
        bundle["cycleTimeTrend"][line_id] = _trend_for_station(station, "cycle_time", line_id)

    return bundle


@app.get("/api/manager/available-dates")
def GetManagerAvailableDates():
    from db_connection import get_connection

    try:
        conn = get_connection()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Manager API connection failed: {exc}") from exc

    try:
        return get_manager_available_dates(conn)
    finally:
        conn.close()


@app.get("/api/manager/dashboard")
def GetManagerDashboard(date: str | None = None, hour: int | None = None, batch_id: str | None = None):
    if hour is not None and date in (None, ""):
        raise HTTPException(status_code=400, detail="date is required when hour is provided")
    if batch_id not in (None, "") and (date in (None, "") or hour is None):
        raise HTTPException(status_code=400, detail="date and hour are required when batch_id is provided")

    from db_connection import get_connection

    try:
        conn = get_connection()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Manager API connection failed: {exc}") from exc

    try:
        bundle = _build_manager_bundle_from_database(conn, date=date, hour=hour, batch_id=batch_id)
    except ManagerDateSelectionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Manager dashboard query failed: {exc}") from exc
    finally:
        conn.close()

    return build_manager_dashboard_payload(bundle)


@app.get("/health")
def Health():
    return HealthCheck()


@app.get("/api/health")
def ApiHealth():
    return HealthCheck()


@app.get("/api/database/status")
def ApiDatabaseStatus():
    """Database connectivity contract used by Engineer UI V29."""
    return JSONResponse(content=check_database_status())


@app.post("/api/time-series")
def HandleTimeSeriesRequest(request: Dict[str, Any] = Body(default_factory=dict)):
    """UI core query.

    Formal DB mode: call IntegratedSprayLineService only.
    Empty request is rejected so it cannot silently create demo data.
    """
    if not request:
        return _formal_db_error(
            "Formal DB mode requires a request body. Provide line_scope/line_id, slider_value, and mode.",
            status_code=422,
        )
    request = _force_integrated_request(request)
    result = _run_integrated_for_ui(request, fallback_to_demo=False)
    if result.get("success") is True:
        data = result.get("data", {})
        if isinstance(data, dict):
            data["api_route"] = "POST /api/time-series"
            data["api_integration_mode"] = result.get("source_mode")
        return JSONResponse(content=data)
    return JSONResponse(status_code=500, content=result)


@app.post("/api/time-series/ui/summary")
def HandleTimeSeriesUiSummaryRequest(request: Dict[str, Any] = Body(default_factory=dict)):
    if "slider_value" not in request:
        request["slider_value"] = 0
    request = _force_integrated_request(request)
    result = _run_integrated_for_ui(request, fallback_to_demo=False)
    data = result.get("data", {})
    if result.get("source_mode") == "integrated":
        return JSONResponse(content=build_ui_summary_output(data))
    return JSONResponse(status_code=500, content=result)


@app.post("/api/time-series/ui/station-detail")
def HandleTimeSeriesUiStationDetailRequest(request: Dict[str, Any] = Body(default_factory=dict)):
    if "line_id" not in request and "station_id" not in request:
        return JSONResponse(status_code=422, content={
            "success": False,
            "error_type": "ValidationError",
            "message": "request must include line_id or station_id.",
        })
    if "slider_value" not in request:
        request["slider_value"] = 0
    line_id = request.get("line_id") or request.get("station_id")
    request.setdefault("line_scope", line_id)
    request = _force_integrated_request(request)
    result = _run_integrated_for_ui(request, fallback_to_demo=False)
    data = result.get("data", {})
    if result.get("source_mode") == "integrated":
        return JSONResponse(content=build_ui_station_detail_output(data, line_id=line_id))
    return JSONResponse(status_code=500, content=result)


@app.post("/api/time-series/ui/component-detail")
def HandleTimeSeriesUiComponentDetailRequest(request: Dict[str, Any] = Body(default_factory=dict)):
    if "line_id" not in request and "station_id" not in request:
        return JSONResponse(status_code=422, content={
            "success": False,
            "error_type": "ValidationError",
            "message": "request must include line_id or station_id.",
        })

    raw_component = (
        request.get("component_name")
        or request.get("component_key")
        or request.get("component_id")
    )
    component_name = normalize_component_name(raw_component)
    if not component_name:
        return JSONResponse(status_code=422, content={
            "success": False,
            "error_type": "ValidationError",
            "message": "request must include component_name, component_key, or component_id.",
        })

    request["component_name"] = component_name
    if "slider_value" not in request:
        request["slider_value"] = 0
    line_id = request.get("line_id") or request.get("station_id")
    request.setdefault("line_scope", line_id)
    request = _force_integrated_request(request)
    result = _run_integrated_for_ui(request, fallback_to_demo=False)
    data = result.get("data", {})
    if result.get("source_mode") == "integrated":
        return JSONResponse(content=build_ui_component_detail_output(data, line_id=line_id, component_name=component_name))
    return JSONResponse(status_code=500, content=result)


@app.get("/api/versionb/status")
def GetVersionBStatus():
    return JSONResponse(content={
        "schema_version": "v1.0",
        "service_name": "SprayLine_API_0718_v3",
        "output_type": "versionb_status",
        **get_versionb_status(),
        "integration_mode": "official Database/versionB first; packaged fallback only if official DB functions are unavailable.",
    })


@app.get("/api/alerts")
def GetVersionBAlerts(station_id: str | None = None, state: str | None = None, acknowledged: bool | None = None, days: int = 7, limit: int = 50):
    return JSONResponse(content=VersionBGetAlerts(station_id=station_id, state=state, acknowledged=acknowledged, days=days, limit=limit))


@app.get("/api/alerts/causes/{cause_id}/responses")
def GetVersionBResponsesForCause(cause_id: str):
    return JSONResponse(content=VersionBGetResponsesForCause(cause_id))


@app.get("/api/alerts/unacknowledged/{station_id}")
def GetVersionBUnacknowledgedAlerts(station_id: str, limit: int = 50):
    return JSONResponse(content=VersionBGetUnacknowledgedAlerts(station_id, limit=limit))


@app.get("/api/alerts/{event_id}")
def GetVersionBAlertCard(event_id: str):
    result = VersionBGetAlertCard(event_id)
    if result.get("db_available") is True and result.get("alert") is None:
        return JSONResponse(status_code=404, content=result)
    return JSONResponse(content=result)


@app.patch("/api/alerts/{event_id}/acknowledge")
def AcknowledgeVersionBAlert(event_id: str, body: Dict[str, Any] = Body(default_factory=dict)):
    return JSONResponse(content=VersionBAcknowledgeAlert(event_id=event_id, acknowledged_at=body.get("acknowledged_at")))


@app.get("/api/service-orchestration/status")
def GetServiceOrchestrationStatus():
    return JSONResponse(content=get_service_orchestration_status())


@app.post("/api/service-orchestration/integrated/query")
def RunIntegratedServiceQuery(request: Dict[str, Any] = Body(default_factory=dict)):
    write_back = bool(request.pop("write_back", False))
    if not request:
        request = BuildOrchestrationIntegratedRequest(slider_value=0, station_scope="Station_1", window_minutes=30)
    return _service_json_response(
        run_integrated_service_query(request=request, write_back=write_back)
    )


@app.post("/api/service-orchestration/integrated/run-once")
def RunIntegratedServiceOnce(request: Dict[str, Any] = Body(default_factory=dict)):
    request["write_back"] = True
    return RunIntegratedServiceQuery(request)


@app.post("/api/service-orchestration/future/payload")
def BuildFuturePredictionPayload(request: Dict[str, Any] = Body(default_factory=dict)):
    return _service_json_response(build_future_prediction_payload_for_api(request))


@app.post("/api/service-orchestration/future/save")
def SaveFuturePredictionPayload(request: Dict[str, Any] = Body(default_factory=dict)):
    commit = bool(request.pop("commit", True))
    return _service_json_response(
        save_future_prediction_payload_for_api(request, commit=commit)
    )


@app.post("/api/service-orchestration/monitoring/run")
def RunMonitoringOnce(request: Dict[str, Any] = Body(default_factory=dict)):
    return _service_json_response(
        run_monitoring_once_for_api(
            station=request.get("station") or request.get("station_id"),
            lookback_minutes=request.get("lookback_minutes", 30),
        )
    )


@app.get("/api/service-orchestration/troubleshooting/matrix")
def GetTroubleshootingMatrix(asset_type: str | None = None, state: str | None = None):
    return _service_json_response(
        get_troubleshooting_matrix_for_api(asset_type=asset_type, state=state)
    )


@app.get("/api/service-orchestration/troubleshooting/states/{state}/recommendations")
def GetStateRecommendations(state: str, station: str | None = None):
    return _service_json_response(
        get_state_recommendations_for_api(state=state, station=station)
    )


@app.get("/api/routes")
def GetRoutes():
    routes = []
    for route in app.routes:
        methods = sorted(getattr(route, "methods", []) or [])
        path = getattr(route, "path", None)
        if path and path.startswith("/api"):
            routes.append({"path": path, "methods": methods})
    return {"service_name": "SprayLine_API_0718_v3", "route_count": len(routes), "routes": routes}


@app.get("/")
def HealthCheck():
    return {
        "service_name": "SprayLine API final_version_0718_v3",
        "version": "0718.3",
        "status": "running",
        "note": "SprayLine only. Only SprayLine implementation is included.",
        "docs": "/docs",
        "two_api_lines": {
            "time_series_ui_line": {
                "purpose": "UI past/current/future query and display format",
                "endpoints": [
                    "POST /api/time-series",
                    "POST /api/time-series/ui/summary",
                    "POST /api/time-series/ui/station-detail",
                    "POST /api/time-series/ui/component-detail",
                ],
                "default_mode": "Formal DB only: IntegratedSprayLineService. Demo endpoints and demo fallback are removed.",
            },
            "service_orchestration_line": {
                "purpose": "Shaoyu formal service orchestration and DB write-back",
                "endpoints": [
                    "POST /api/service-orchestration/integrated/query",
                    "POST /api/service-orchestration/integrated/run-once",
                    "POST /api/service-orchestration/future/save",
                    "POST /api/service-orchestration/monitoring/run",
                    "GET /api/service-orchestration/troubleshooting/matrix",
                ],
                "db_persistence": "Database/versionB",
            },
        },
        "ui_rule": "UI slider query endpoints default to no DB write-back. Write-back is explicit only under /api/service-orchestration/* save/run endpoints.",
    }
