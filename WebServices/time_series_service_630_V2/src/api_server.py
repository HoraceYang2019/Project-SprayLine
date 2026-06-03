from pathlib import Path
import random
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from time_series_service import TimeSeriesService


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


@app.get("/")
def HealthCheck():
    return {
        "service_name": "TimeSeriesService",
        "status": "running",
        "official_endpoint": "POST /api/time-series",
        "demo_endpoints": [
            "GET /api/time-series/demo/current",
            "GET /api/time-series/demo/past",
            "GET /api/time-series/demo/future",
            "GET /api/time-series/demo/random"
        ]
    }
