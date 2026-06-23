from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import random
import traceback

from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from time_series_service import TimeSeriesService
from ui_adapter import (
    BuildBaseRequestFromUiRequest,
    BuildUiSummaryOutput as DemoBuildUiSummaryOutput,
    BuildUiStationDetailOutput as DemoBuildUiStationDetailOutput,
    BuildUiComponentDetailOutput as DemoBuildUiComponentDetailOutput,
    RemoveNoneOptionalFields,
)
from shaoyu_ui_bridge import (
    build_integrated_request_from_ui,
    build_ui_summary_output,
    build_ui_station_detail_output,
    build_ui_component_detail_output,
)

from versionb_loader import get_versionb_status
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
    run_integrated_service_demo,
    build_future_prediction_payload_for_api,
    save_future_prediction_payload_for_api,
    run_monitoring_once_for_api,
    get_troubleshooting_matrix_for_api,
    get_state_recommendations_for_api,
)


app = FastAPI(
    title="Shaoyu0617 SprayLine API",
    description=(
        "Unified API for SprayLine past/current/future UI query and "
        "Shaoyu service orchestration."
    ),
    version="0617ver_1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_ROOT = Path(__file__).resolve().parents[1]

# Demo fallback service. This keeps UI endpoints runnable even before PostgreSQL is available.
demo_service = TimeSeriesService(
    processed_result_db_path=API_ROOT / "data" / "runtime" / "processed_result_database_demo.json"
)


def _json_error(stage: str, exc: BaseException) -> Dict[str, Any]:
    return {
        "success": False,
        "stage": stage,
        "error_type": exc.__class__.__name__,
        "error_message": str(exc),
        "traceback_tail": traceback.format_exc(limit=3),
    }


def BuildDemoRequest(time_type: str) -> Dict[str, Any]:
    base_request = {
        "schema_version": "v1.0",
        "service_name": "TimeSeriesService",
        "request_id": f"demo_{time_type}_001",
        "mode": "time",
        "line_scope": "all",
        "requested_metrics": [
            "availability_pct",
            "clog_rate_pct",
            "pressure_bar",
            "flow_rate_ml_min",
            "paint_flow_ml_min",
            "air_pressure_bar",
            "maintainability_pct",
            "quality_score_pct",
            "risk_text",
            "spray_width_mm",
            "film_thickness_um",
            "recipe_name",
            "temperature_c",
            "humidity_rh",
            "utilization_pct",
            "cycle_time_sec",
        ],
    }
    if time_type == "random":
        time_type = random.choice(["past", "current", "future"])
        base_request["request_id"] = f"demo_random_{time_type}_001"
    if time_type == "past":
        base_request["window_type"] = "2hour"
        base_request["slider_value"] = random.choice([-1, -2, -3, -4, -5])
    elif time_type == "current":
        base_request["window_type"] = "current"
        base_request["slider_value"] = 0
    elif time_type == "future":
        base_request["window_type"] = "2hour"
        base_request["slider_value"] = random.choice([1, 2, 3, 4, 5])
    else:
        raise ValueError("time_type must be past, current, future, or random.")
    return base_request


def _run_integrated_for_ui(request: Dict[str, Any], fallback_to_demo: bool = True) -> Dict[str, Any]:
    """Run Shaoyu integrated service first; use demo fallback only when DB is unavailable.

    Request option:
        source_mode = integrated | demo | auto

    - integrated: requires Database/versionB + PostgreSQL.
    - demo: uses TimeSeriesService demo provider.
    - auto: try integrated, fallback demo when DB fails.
    """
    source_mode = request.get("source_mode", "auto")
    if source_mode == "demo":
        core_request = RemoveNoneOptionalFields(BuildBaseRequestFromUiRequest(request))
        return {
            "success": True,
            "source_mode": "demo",
            "data": demo_service.HandleTimeSeriesQuery(core_request),
        }

    integrated_request = build_integrated_request_from_ui(request)
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
        if source_mode == "integrated" or not fallback_to_demo:
            return result
        integrated_error = result
    except Exception as exc:
        if source_mode == "integrated" or not fallback_to_demo:
            return _json_error("_run_integrated_for_ui", exc)
        integrated_error = _json_error("_run_integrated_for_ui", exc)

    # Fallback keeps UI API from breaking when PostgreSQL is not ready.
    try:
        core_request = RemoveNoneOptionalFields(BuildBaseRequestFromUiRequest(request))
        fallback = demo_service.HandleTimeSeriesQuery(core_request)
        fallback["source_mode"] = "demo_fallback"
        fallback["integrated_error"] = integrated_error
        return {
            "success": True,
            "source_mode": "demo_fallback",
            "data": fallback,
        }
    except Exception as exc:
        return {
            "success": False,
            "source_mode": "failed",
            "integrated_error": integrated_error,
            "demo_error": _json_error("demo_fallback", exc),
        }


def GetLatestOutput() -> Dict[str, Any]:
    if demo_service.latest_output_json_path.exists():
        import json
        return json.loads(demo_service.latest_output_json_path.read_text(encoding="utf-8"))
    request = BuildDemoRequest("current")
    return demo_service.HandleTimeSeriesQuery(request)


@app.get("/health")
def Health():
    return HealthCheck()


@app.get("/api/health")
def ApiHealth():
    return HealthCheck()


@app.post("/api/time-series")
def HandleTimeSeriesRequest(request: Dict[str, Any] = Body(default_factory=dict)):
    """UI core query.

    0617ver_1 default: call IntegratedSprayLineService first. If DB is not ready,
    fallback to TimeSeriesService demo output so the UI endpoint still works.
    """
    if not request:
        request = BuildDemoRequest("current")
    result = _run_integrated_for_ui(request, fallback_to_demo=True)
    if result.get("success") is True:
        data = result.get("data", {})
        if isinstance(data, dict):
            data["api_route"] = "POST /api/time-series"
            data["api_integration_mode"] = result.get("source_mode")
        return JSONResponse(content=data)
    return JSONResponse(status_code=500, content=result)


@app.get("/api/time-series/demo/current")
def DemoCurrent():
    return HandleTimeSeriesRequest(BuildDemoRequest("current"))


@app.get("/api/time-series/demo/past")
def DemoPast():
    return HandleTimeSeriesRequest(BuildDemoRequest("past"))


@app.get("/api/time-series/demo/future")
def DemoFuture():
    return HandleTimeSeriesRequest(BuildDemoRequest("future"))


@app.get("/api/time-series/demo/random")
def DemoRandom():
    return HandleTimeSeriesRequest(BuildDemoRequest("random"))


@app.post("/api/time-series/ui/summary")
def HandleTimeSeriesUiSummaryRequest(request: Dict[str, Any] = Body(default_factory=dict)):
    if "slider_value" not in request:
        request["slider_value"] = 0
    result = _run_integrated_for_ui(request, fallback_to_demo=True)
    data = result.get("data", {})
    if result.get("source_mode") == "integrated":
        return JSONResponse(content=build_ui_summary_output(data))
    if result.get("success") is True:
        return JSONResponse(content=DemoBuildUiSummaryOutput(data))
    return JSONResponse(status_code=500, content=result)


@app.post("/api/time-series/ui/station-detail")
def HandleTimeSeriesUiStationDetailRequest(request: Dict[str, Any] = Body(default_factory=dict)):
    if "line_id" not in request and "station_id" not in request:
        raise ValueError("request must include line_id or station_id.")
    if "slider_value" not in request:
        request["slider_value"] = 0
    line_id = request.get("line_id") or request.get("station_id")
    request.setdefault("line_scope", line_id)
    result = _run_integrated_for_ui(request, fallback_to_demo=True)
    data = result.get("data", {})
    if result.get("source_mode") == "integrated":
        return JSONResponse(content=build_ui_station_detail_output(data, line_id=line_id))
    if result.get("success") is True:
        return JSONResponse(content=DemoBuildUiStationDetailOutput(data, line_id=line_id))
    return JSONResponse(status_code=500, content=result)


@app.post("/api/time-series/ui/component-detail")
def HandleTimeSeriesUiComponentDetailRequest(request: Dict[str, Any] = Body(default_factory=dict)):
    if "line_id" not in request and "station_id" not in request:
        raise ValueError("request must include line_id or station_id.")
    if "component_name" not in request:
        raise ValueError("request must include component_name.")
    if "slider_value" not in request:
        request["slider_value"] = 0
    line_id = request.get("line_id") or request.get("station_id")
    request.setdefault("line_scope", line_id)
    result = _run_integrated_for_ui(request, fallback_to_demo=True)
    data = result.get("data", {})
    if result.get("source_mode") == "integrated":
        return JSONResponse(content=build_ui_component_detail_output(data, line_id=line_id, component_name=request["component_name"]))
    if result.get("success") is True:
        return JSONResponse(content=DemoBuildUiComponentDetailOutput(data, line_id=line_id, component_name=request["component_name"]))
    return JSONResponse(status_code=500, content=result)


# Legacy D integration endpoints are kept for UI compatibility, but marked as demo/runtime JSON.
@app.get("/api/time-series/d/latest")
def GetDIntegrationLatest():
    latest = GetLatestOutput()
    return JSONResponse(content={
        "schema_version": latest.get("schema_version"),
        "service_name": "TimeSeriesService",
        "output_type": "d_integration_latest",
        "generated_at": latest.get("generated_at"),
        "request_id": latest.get("request_id"),
        "viewer_state": latest.get("viewer_state", {}),
        "summary": latest.get("summary", {}),
        "d_integration": latest.get("d_integration", {}),
        "note": "Legacy demo/runtime JSON endpoint; formal DB write-back uses /api/service-orchestration/*.",
    })


@app.get("/api/time-series/d/alert-events")
def GetDAlertEvents():
    latest = GetLatestOutput()
    return JSONResponse(content={"output_type": "alert_events", "items": latest.get("d_integration", {}).get("alert_events", [])})


@app.get("/api/time-series/d/future-predictions")
def GetDFuturePredictions():
    latest = GetLatestOutput()
    return JSONResponse(content={"output_type": "future_prediction_results", "items": latest.get("d_integration", {}).get("future_prediction_results", [])})


@app.get("/api/time-series/d/troubleshooting")
def GetDTroubleshootingResults():
    latest = GetLatestOutput()
    return JSONResponse(content={"output_type": "troubleshooting_results", "items": latest.get("d_integration", {}).get("troubleshooting_results", [])})


@app.post("/api/time-series/d/alert-acknowledge")
def AcknowledgeAlertEvent(request: Dict[str, Any] = Body(default_factory=dict)):
    from datetime import datetime, timezone
    return JSONResponse(content={
        "schema_version": "v1.0",
        "service_name": "TimeSeriesService",
        "output_type": "alert_acknowledge",
        "event_id": request.get("event_id"),
        "acknowledged_by": request.get("acknowledged_by"),
        "acknowledged_at": datetime.now(timezone.utc).isoformat(),
        "status": "ack_payload_ready",
        "persistence_status": "demo_only_use_/api/alerts/{event_id}/acknowledge_for_formal_db",
    })


@app.get("/api/versionb/status")
def GetVersionBStatus():
    return JSONResponse(content={
        "schema_version": "v1.0",
        "service_name": "Shaoyu0617_API",
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
    return JSONResponse(content=run_integrated_service_query(request=request, write_back=write_back))


@app.post("/api/service-orchestration/integrated/run-once")
def RunIntegratedServiceOnce(request: Dict[str, Any] = Body(default_factory=dict)):
    request["write_back"] = True
    return RunIntegratedServiceQuery(request)


@app.get("/api/service-orchestration/integrated/demo/{time_type}")
def RunIntegratedServiceDemo(time_type: str, station_id: str = "Station_1", window_minutes: int = 30):
    return JSONResponse(content=run_integrated_service_demo(time_type=time_type, station_id=station_id, window_minutes=window_minutes))


@app.post("/api/service-orchestration/future/payload")
def BuildFuturePredictionPayload(request: Dict[str, Any] = Body(default_factory=dict)):
    return JSONResponse(content=build_future_prediction_payload_for_api(request))


@app.post("/api/service-orchestration/future/save")
def SaveFuturePredictionPayload(request: Dict[str, Any] = Body(default_factory=dict)):
    commit = bool(request.pop("commit", True))
    return JSONResponse(content=save_future_prediction_payload_for_api(request, commit=commit))


@app.post("/api/service-orchestration/monitoring/run")
def RunMonitoringOnce(request: Dict[str, Any] = Body(default_factory=dict)):
    return JSONResponse(content=run_monitoring_once_for_api(station=request.get("station") or request.get("station_id"), lookback_minutes=int(request.get("lookback_minutes", 30))))


@app.get("/api/service-orchestration/troubleshooting/matrix")
def GetTroubleshootingMatrix(asset_type: str | None = None, state: str | None = None):
    return JSONResponse(content=get_troubleshooting_matrix_for_api(asset_type=asset_type, state=state))


@app.get("/api/service-orchestration/troubleshooting/states/{state}/recommendations")
def GetStateRecommendations(state: str, station: str | None = None):
    return JSONResponse(content=get_state_recommendations_for_api(state=state, station=station))


@app.get("/api/routes")
def GetRoutes():
    routes = []
    for route in app.routes:
        methods = sorted(getattr(route, "methods", []) or [])
        path = getattr(route, "path", None)
        if path and path.startswith("/api"):
            routes.append({"path": path, "methods": methods})
    return {"service_name": "Shaoyu0617_API", "route_count": len(routes), "routes": routes}


@app.get("/")
def HealthCheck():
    return {
        "service_name": "Shaoyu0617 SprayLine API",
        "version": "0617ver_1",
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
                "default_mode": "IntegratedSprayLineService first; demo fallback when PostgreSQL is not ready.",
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
