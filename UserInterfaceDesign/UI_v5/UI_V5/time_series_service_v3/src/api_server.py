from pathlib import Path
import random
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from time_series_service import TimeSeriesService
from ui_adapter import (
    BuildBaseRequestFromUiRequest,
    BuildUiSummaryOutput,
    BuildUiStationDetailOutput,
    BuildUiComponentDetailOutput,
    RemoveNoneOptionalFields,
)


app = FastAPI(title="TimeSeriesService API")

service = TimeSeriesService(
    processed_result_db_path=Path("../examples/processed_result_database_demo.json")
)


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


@app.get("/")
def HealthCheck():
    return {
        "service_name": "TimeSeriesService",
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
        ]
    }
