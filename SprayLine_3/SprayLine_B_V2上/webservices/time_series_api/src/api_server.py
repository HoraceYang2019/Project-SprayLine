from pathlib import Path
import random
from typing import Any, Dict

from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from time_series_service import TimeSeriesService
from ui_adapter import (
    BuildBaseRequestFromUiRequest,
    BuildUiSummaryOutput,
    BuildUiStationDetailOutput,
    BuildUiComponentDetailOutput,
    RemoveNoneOptionalFields,
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


app = FastAPI(title="SprayLine-B Integrated + TimeSeriesService API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_ROOT = Path(__file__).resolve().parents[1]

service = TimeSeriesService(
    processed_result_db_path=API_ROOT / "data" / "runtime" / "processed_result_database_demo.json"
)


def GetLatestOutput() -> Dict[str, Any]:
    if service.latest_output_json_path.exists():
        import json
        return json.loads(service.latest_output_json_path.read_text(encoding="utf-8"))
    request = BuildDemoRequest("current")
    return service.HandleTimeSeriesQuery(request)


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
            "maintainability_pct",
            "quality_score_pct",
            "risk_text",
            "spray_width_mm",
            "recipe_name",
            "temperature_c",
            "utilization_pct",
            "cycle_time_sec"
        ]
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


@app.post("/api/time-series")
def HandleTimeSeriesRequest(request: Dict[str, Any]):
    output = service.HandleTimeSeriesQuery(request)
    return JSONResponse(content=output)


@app.get("/api/time-series/demo/current")
def DemoCurrent():
    request = BuildDemoRequest("current")
    output = service.HandleTimeSeriesQuery(request)
    return JSONResponse(content=output)


@app.get("/api/time-series/demo/past")
def DemoPast():
    request = BuildDemoRequest("past")
    output = service.HandleTimeSeriesQuery(request)
    return JSONResponse(content=output)


@app.get("/api/time-series/demo/future")
def DemoFuture():
    request = BuildDemoRequest("future")
    output = service.HandleTimeSeriesQuery(request)
    return JSONResponse(content=output)


@app.get("/api/time-series/demo/random")
def DemoRandom():
    request = BuildDemoRequest("random")
    output = service.HandleTimeSeriesQuery(request)
    return JSONResponse(content=output)


@app.post("/api/time-series/ui/summary")
def HandleTimeSeriesUiSummaryRequest(request: Dict[str, Any]):
    """
    UI 初始化畫面用 API。

    UI 第一次進入 dashboard 或刷新總覽時呼叫。
    """

    core_request = RemoveNoneOptionalFields(
        BuildBaseRequestFromUiRequest(request)
    )

    core_output = service.HandleTimeSeriesQuery(core_request)

    ui_output = BuildUiSummaryOutput(core_output)

    return JSONResponse(content=ui_output)


@app.post("/api/time-series/ui/station-detail")
def HandleTimeSeriesUiStationDetailRequest(request: Dict[str, Any]):
    """
    UI 點開某一站詳細資料時呼叫。
    """

    if "line_id" not in request:
        raise ValueError("request must include line_id.")

    core_request = RemoveNoneOptionalFields(
        BuildBaseRequestFromUiRequest({
            **request,
            "line_scope": request["line_id"],
        })
    )

    core_output = service.HandleTimeSeriesQuery(core_request)

    ui_output = BuildUiStationDetailOutput(
        core_output=core_output,
        line_id=request["line_id"]
    )

    return JSONResponse(content=ui_output)


@app.post("/api/time-series/ui/component-detail")
def HandleTimeSeriesUiComponentDetailRequest(request: Dict[str, Any]):
    """
    UI 點開 nozzle / filter_mesh / spray_width 元件詳細資料時呼叫。
    """

    if "line_id" not in request:
        raise ValueError("request must include line_id.")

    if "component_name" not in request:
        raise ValueError("request must include component_name.")

    core_request = RemoveNoneOptionalFields(
        BuildBaseRequestFromUiRequest({
            **request,
            "line_scope": request["line_id"],
        })
    )

    core_output = service.HandleTimeSeriesQuery(core_request)

    ui_output = BuildUiComponentDetailOutput(
        core_output=core_output,
        line_id=request["line_id"],
        component_name=request["component_name"]
    )

    return JSONResponse(content=ui_output)


@app.get("/api/time-series/d/latest")
def GetDIntegrationLatest():
    """Return the latest D-stage payload groups."""
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
    })


@app.get("/api/time-series/d/alert-events")
def GetDAlertEvents():
    latest = GetLatestOutput()
    return JSONResponse(content={
        "output_type": "alert_events",
        "items": latest.get("d_integration", {}).get("alert_events", []),
    })


@app.get("/api/time-series/d/future-predictions")
def GetDFuturePredictions():
    latest = GetLatestOutput()
    return JSONResponse(content={
        "output_type": "future_prediction_results",
        "items": latest.get("d_integration", {}).get("future_prediction_results", []),
    })


@app.get("/api/time-series/d/troubleshooting")
def GetDTroubleshootingResults():
    latest = GetLatestOutput()
    return JSONResponse(content={
        "output_type": "troubleshooting_results",
        "items": latest.get("d_integration", {}).get("troubleshooting_results", []),
    })


@app.post("/api/time-series/d/alert-acknowledge")
def AcknowledgeAlertEvent(request: Dict[str, Any]):
    """Prototype acknowledge payload. Formal DB update can replace this endpoint later."""
    from datetime import datetime, timezone
    return JSONResponse(content={
        "schema_version": "v1.0",
        "service_name": "TimeSeriesService",
        "output_type": "alert_acknowledge",
        "event_id": request.get("event_id"),
        "acknowledged_by": request.get("acknowledged_by"),
        "acknowledged_at": datetime.now(timezone.utc).isoformat(),
        "status": "ack_payload_ready",
        "persistence_status": "pending_formal_db_api",
    })



@app.get("/api/versionb/status")
def GetVersionBStatus():
    """Check whether versionB DB modules and database connection layer are available."""
    return JSONResponse(content={
        "schema_version": "v1.0",
        "service_name": "TimeSeriesService",
        "output_type": "versionb_status",
        **get_versionb_status(),
        "integration_mode": "API contract ready; live DB query enabled only after PostgreSQL and psycopg2 are configured.",
    })


@app.get("/api/alerts")
def GetVersionBAlerts(
    station_id: str | None = None,
    state: str | None = None,
    acknowledged: bool | None = None,
    days: int = 7,
    limit: int = 50,
):
    """versionB Alert API: query alert list through db_alert.get_alerts_by_filters()."""
    return JSONResponse(content=VersionBGetAlerts(
        station_id=station_id,
        state=state,
        acknowledged=acknowledged,
        days=days,
        limit=limit,
    ))


@app.get("/api/alerts/causes/{cause_id}/responses")
def GetVersionBResponsesForCause(cause_id: str):
    """versionB Alert API: query suggested responses for a cause_id."""
    return JSONResponse(content=VersionBGetResponsesForCause(cause_id))


@app.get("/api/alerts/unacknowledged/{station_id}")
def GetVersionBUnacknowledgedAlerts(station_id: str, limit: int = 50):
    """versionB Alert API: query unacknowledged alerts for a station."""
    return JSONResponse(content=VersionBGetUnacknowledgedAlerts(station_id, limit=limit))


@app.get("/api/alerts/{event_id}")
def GetVersionBAlertCard(event_id: str):
    """versionB Alert API: query one alert UI card through db_alert.get_alert_ui_card()."""
    result = VersionBGetAlertCard(event_id)
    if result.get("db_available") is True and result.get("alert") is None:
        return JSONResponse(status_code=404, content=result)
    return JSONResponse(content=result)


@app.patch("/api/alerts/{event_id}/acknowledge")
def AcknowledgeVersionBAlert(event_id: str, body: Dict[str, Any] = Body(default_factory=dict)):
    """versionB Alert API: acknowledge one alert through db_alert.acknowledge_alert()."""
    return JSONResponse(content=VersionBAcknowledgeAlert(
        event_id=event_id,
        acknowledged_at=body.get("acknowledged_at"),
    ))


@app.get("/api/service-orchestration/status")
def GetServiceOrchestrationStatus():
    """Check whether FutureService / Monitoring / Troubleshooting functions can be imported."""
    return JSONResponse(content=get_service_orchestration_status())


@app.post("/api/service-orchestration/integrated/query")
def RunIntegratedServiceQuery(request: Dict[str, Any] = Body(default_factory=dict)):
    """Call integrated service IntegratedSprayLineService without DB write-back by default."""
    write_back = bool(request.pop("write_back", False))
    if not request:
        request = BuildOrchestrationIntegratedRequest(slider_value=0, station_scope="Station_1", window_minutes=30)
    return JSONResponse(content=run_integrated_service_query(request=request, write_back=write_back))


@app.get("/api/service-orchestration/integrated/demo/{time_type}")
def RunIntegratedServiceDemo(time_type: str, station_id: str = "Station_1", window_minutes: int = 30):
    """Call integrated service IntegratedSprayLineService demo for past/current/future. Requires DB sensor data."""
    return JSONResponse(content=run_integrated_service_demo(
        time_type=time_type,
        station_id=station_id,
        window_minutes=window_minutes,
    ))


@app.post("/api/service-orchestration/future/payload")
def BuildFuturePredictionPayload(request: Dict[str, Any] = Body(default_factory=dict)):
    """Call integrated service FutureService to build future_prediction_result payload. No DB write."""
    return JSONResponse(content=build_future_prediction_payload_for_api(request))


@app.post("/api/service-orchestration/future/save")
def SaveFuturePredictionPayload(request: Dict[str, Any] = Body(default_factory=dict)):
    """Call integrated service FutureService and save future_prediction_result through versionB DB function."""
    commit = bool(request.pop("commit", True))
    return JSONResponse(content=save_future_prediction_payload_for_api(request, commit=commit))


@app.post("/api/service-orchestration/monitoring/run")
def RunMonitoringOnce(request: Dict[str, Any] = Body(default_factory=dict)):
    """Call integrated service MonitoringWorker once. Requires PostgreSQL/versionB sensor data."""
    return JSONResponse(content=run_monitoring_once_for_api(
        station=request.get("station") or request.get("station_id"),
        lookback_minutes=int(request.get("lookback_minutes", 30)),
    ))


@app.get("/api/service-orchestration/troubleshooting/matrix")
def GetTroubleshootingMatrix(asset_type: str | None = None, state: str | None = None):
    """Call integrated service TroubleshootingService matrix query. Requires PostgreSQL/versionB."""
    return JSONResponse(content=get_troubleshooting_matrix_for_api(asset_type=asset_type, state=state))


@app.get("/api/service-orchestration/troubleshooting/states/{state}/recommendations")
def GetStateRecommendations(state: str, station: str | None = None):
    """Call integrated service TroubleshootingService recommendations query. Requires PostgreSQL/versionB."""
    return JSONResponse(content=get_state_recommendations_for_api(state=state, station=station))


@app.get("/")
def HealthCheck():
    return {
        "service_name": "SprayLine-B Integrated + TimeSeriesService",
        "status": "running",
        "official_endpoint": "POST /api/time-series",
        "ui_adapter_endpoints": [
            "POST /api/time-series/ui/summary",
            "POST /api/time-series/ui/station-detail",
            "POST /api/time-series/ui/component-detail"
        ],
        "demo_endpoints": [
            "GET /api/time-series/demo/current",
            "GET /api/time-series/demo/past",
            "GET /api/time-series/demo/future",
            "GET /api/time-series/demo/random"
        ],
        "d_integration_endpoints": [
            "GET /api/time-series/d/latest",
            "GET /api/time-series/d/alert-events",
            "GET /api/time-series/d/future-predictions",
            "GET /api/time-series/d/troubleshooting",
            "POST /api/time-series/d/alert-acknowledge"
        ],
        "versionb_alert_endpoints": [
            "GET /api/versionb/status",
            "GET /api/alerts",
            "GET /api/alerts/{event_id}",
            "PATCH /api/alerts/{event_id}/acknowledge",
            "GET /api/alerts/causes/{cause_id}/responses",
            "GET /api/alerts/unacknowledged/{station_id}"
        ],
        "service_orchestration_endpoints": [
            "GET /api/service-orchestration/status",
            "POST /api/service-orchestration/integrated/query",
            "GET /api/service-orchestration/integrated/demo/{time_type}",
            "POST /api/service-orchestration/future/payload",
            "POST /api/service-orchestration/future/save",
            "POST /api/service-orchestration/monitoring/run",
            "GET /api/service-orchestration/troubleshooting/matrix",
            "GET /api/service-orchestration/troubleshooting/states/{state}/recommendations"
        ]
    }
