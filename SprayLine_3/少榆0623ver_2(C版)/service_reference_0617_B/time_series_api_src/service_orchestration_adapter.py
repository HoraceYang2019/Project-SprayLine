"""Adapter layer that lets the TimeSeriesService FastAPI call integrated service modules.

This file intentionally does NOT re-implement the existing Future / Monitoring /
Troubleshooting logic.  It only imports the existing functions from:

- webservices.integrated_service.sprayline_integrated_service
- webservices.future_service.future_service
- webservices.monitoring_worker.monitoring_worker
- webservices.troubleshooting_service.troubleshooting_service
- webservices.integration_adapter.database_versionb_adapter

The public FastAPI routes call the functions in this adapter so DB errors or
missing local PostgreSQL setup are returned as JSON instead of crashing the API.
"""
from __future__ import annotations

from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, Optional
import traceback
import sys

# When api_server.py is loaded through importlib from webservices/time_series_api/src,
# make sure the project root is still importable as a package root.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _json_safe(value: Any) -> Any:
    """Recursively convert datetimes and non-JSON objects to safe values."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    try:
        import decimal
        if isinstance(value, decimal.Decimal):
            return float(value)
    except Exception:
        pass
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _ok(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _json_safe({"success": True, **payload})


def _error(stage: str, exc: BaseException) -> Dict[str, Any]:
    return _json_safe({
        "success": False,
        "stage": stage,
        "error_type": exc.__class__.__name__,
        "error_message": str(exc),
        "traceback_tail": traceback.format_exc(limit=3),
        "note": "This endpoint is wired to integrated service modules, but this action may require PostgreSQL/versionB setup.",
    })


def get_service_orchestration_status() -> Dict[str, Any]:
    """Return import status for integrated service modules and Database/versionB adapter."""
    status: Dict[str, Any] = {
        "output_type": "service_orchestration_adapter_status",
        "adapter_file": str(Path(__file__).resolve()),
        "project_root": str(PROJECT_ROOT),
        "modules": {},
    }

    checks = {
        "IntegratedSprayLineService": "webservices.integrated_service.sprayline_integrated_service",
        "FutureServiceFunctions": "webservices.future_service.future_service",
        "MonitoringWorker": "webservices.monitoring_worker.monitoring_worker",
        "TroubleshootingService": "webservices.troubleshooting_service.troubleshooting_service",
        "DatabaseVersionBAdapter": "webservices.integration_adapter.database_versionb_adapter",
    }

    for label, module_name in checks.items():
        try:
            module = __import__(module_name, fromlist=["*"])
            status["modules"][label] = {
                "available": True,
                "module": module_name,
                "file": getattr(module, "__file__", None),
            }
        except Exception as exc:
            status["modules"][label] = {
                "available": False,
                "module": module_name,
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
            }

    try:
        from webservices.integration_adapter.database_versionb_adapter import get_adapter_status
        status["database_versionb_adapter"] = get_adapter_status()
    except Exception as exc:
        status["database_versionb_adapter"] = {
            "available": False,
            "error_type": exc.__class__.__name__,
            "error_message": str(exc),
        }

    return _json_safe(status)


def build_integrated_request(
    slider_value: float = 0,
    station_scope: Any = "Station_1",
    window_minutes: int = 30,
    requested_metrics: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """Build a request shape accepted by IntegratedSprayLineService."""
    try:
        from webservices.integrated_service.sprayline_integrated_service import DEFAULT_REQUESTED_METRICS
    except Exception:
        DEFAULT_REQUESTED_METRICS = [
            "film_thickness_um",
            "paint_flow_ml_min",
            "air_pressure_bar",
            "spray_width_mm",
            "filter_diff_pressure_bar",
            "servo_torque_load_pct",
            "path_error_mm",
            "vibration_g",
            "temperature_c",
            "humidity_rh",
        ]

    return {
        "schema_version": "v1.0",
        "service_name": "IntegratedSprayLineService",
        "request_id": "REQ_API_SERVICE_ORCHESTRATION_INTEGRATED",
        "mode": "time",
        "window_type": "time_slider",
        "slider_value": slider_value,
        "window_minutes": window_minutes,
        "station_scope": station_scope,
        "requested_metrics": requested_metrics or DEFAULT_REQUESTED_METRICS,
    }


def run_integrated_service_query(request: Dict[str, Any], write_back: bool = False) -> Dict[str, Any]:
    """Run IntegratedSprayLineService through Database/versionB functions."""
    try:
        from webservices.integrated_service.sprayline_integrated_service import run_integrated_once
        result = run_integrated_once(request=request, write_back=write_back)
        return _ok({
            "output_type": "integrated_service_result",
            "write_back_requested": write_back,
            "data": result,
        })
    except Exception as exc:
        return _error("run_integrated_service_query", exc)


def run_integrated_service_demo(time_type: str, station_id: str = "Station_1", window_minutes: int = 30) -> Dict[str, Any]:
    """Run demo query for past/current/future. Requires DB sensor data."""
    slider_map = {
        "past": -60,
        "current": 0,
        "future": 30,
    }
    if time_type not in slider_map:
        return {
            "success": False,
            "stage": "run_integrated_service_demo",
            "error_type": "ValueError",
            "error_message": "time_type must be past, current, or future.",
        }
    request = build_integrated_request(
        slider_value=slider_map[time_type],
        station_scope=station_id,
        window_minutes=window_minutes,
    )
    return run_integrated_service_query(request=request, write_back=False)


def build_future_prediction_payload_for_api(data: Dict[str, Any]) -> Dict[str, Any]:
    """Call FutureService build_future_prediction_payload(). No DB connection required."""
    try:
        from webservices.future_service.future_service import build_future_prediction_payload
        payload = build_future_prediction_payload(
            batch_id=data.get("batch_id", "BATCH_UNKNOWN"),
            station_id=data.get("station_id"),
            prediction_time=data.get("prediction_time") or datetime.now().isoformat(),
            predicted_ok_rate=data.get("predicted_ok_rate"),
            predicted_ng_count=data.get("predicted_ng_count"),
            quality_score=data.get("quality_score"),
            model_input_source=data.get("model_input_source", "TimeSeriesService API request"),
            prediction_id=data.get("prediction_id"),
            created_at=data.get("created_at"),
        )
        return _ok({
            "output_type": "future_prediction_payload",
            "data": payload,
        })
    except Exception as exc:
        return _error("build_future_prediction_payload_for_api", exc)


def save_future_prediction_payload_for_api(data: Dict[str, Any], commit: bool = True) -> Dict[str, Any]:
    """Build and save a future_prediction_result through FutureService + versionB DB functions."""
    try:
        from webservices.integration_adapter.database_versionb_adapter import get_connection
        from webservices.future_service.future_service import (
            build_future_prediction_payload,
            save_future_prediction_result,
        )

        payload = build_future_prediction_payload(
            batch_id=data.get("batch_id", "BATCH_UNKNOWN"),
            station_id=data.get("station_id"),
            prediction_time=data.get("prediction_time") or datetime.now().isoformat(),
            predicted_ok_rate=data.get("predicted_ok_rate"),
            predicted_ng_count=data.get("predicted_ng_count"),
            quality_score=data.get("quality_score"),
            model_input_source=data.get("model_input_source", "TimeSeriesService API request"),
            prediction_id=data.get("prediction_id"),
            created_at=data.get("created_at"),
        )
        conn = get_connection()
        try:
            prediction_id = save_future_prediction_result(conn, payload, commit=commit)
        finally:
            conn.close()
        return _ok({
            "output_type": "future_prediction_saved",
            "prediction_id": prediction_id,
            "payload": payload,
        })
    except Exception as exc:
        return _error("save_future_prediction_payload_for_api", exc)


def run_monitoring_once_for_api(station: Optional[str] = None, lookback_minutes: int = 30) -> Dict[str, Any]:
    """Run MonitoringWorker once. Requires PostgreSQL/versionB sensor data."""
    try:
        from webservices.monitoring_worker.monitoring_worker import run_monitoring_once
        result = run_monitoring_once(station=station, lookback_minutes=lookback_minutes)
        return _ok({
            "output_type": "monitoring_once_result",
            "station": station,
            "lookback_minutes": lookback_minutes,
            "data": result,
        })
    except Exception as exc:
        return _error("run_monitoring_once_for_api", exc)


def get_troubleshooting_matrix_for_api(asset_type: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Any]:
    """Call TroubleshootingService matrix query. Requires PostgreSQL."""
    try:
        from webservices.integration_adapter.database_versionb_adapter import get_connection
        from webservices.troubleshooting_service.troubleshooting_service import get_troubleshooting_matrix
        conn = get_connection()
        try:
            result = get_troubleshooting_matrix(conn, asset_type=asset_type, state=state)
        finally:
            conn.close()
        return _ok({
            "output_type": "troubleshooting_matrix",
            "asset_type": asset_type,
            "state": state,
            "data": result,
        })
    except Exception as exc:
        return _error("get_troubleshooting_matrix_for_api", exc)


def get_state_recommendations_for_api(state: str, station: Optional[str] = None) -> Dict[str, Any]:
    """Call TroubleshootingService recommendation query. Requires PostgreSQL."""
    try:
        from webservices.integration_adapter.database_versionb_adapter import get_connection
        from webservices.troubleshooting_service.troubleshooting_service import get_state_recommendations
        conn = get_connection()
        try:
            result = get_state_recommendations(conn, state=state, station=station)
        finally:
            conn.close()
        return _ok({
            "output_type": "state_recommendations",
            "state": state,
            "station": station,
            "data": result,
        })
    except Exception as exc:
        return _error("get_state_recommendations_for_api", exc)
