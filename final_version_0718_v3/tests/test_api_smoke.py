from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
for rel in ("api", "services", "database"):
    path = str(ROOT / rel)
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("VERSIONB_PATH", str(ROOT / "database"))

from api_server import app  # noqa: E402


def test_api_root_and_formal_db_mode():
    client = TestClient(app)

    root = client.get("/")
    assert root.status_code == 200
    assert root.json().get("status") == "running"

    empty = client.post("/api/time-series", json={})
    assert empty.status_code == 422
    assert empty.json().get("source_mode") == "integrated"

    summary = client.post(
        "/api/time-series/ui/summary",
        json={"slider_value": 0, "line_scope": "all", "source_mode": "integrated"},
    )
    assert summary.status_code in (200, 500)
    body_text = json.dumps(summary.json(), ensure_ascii=False)
    assert "demo_fallback" not in body_text
    assert "TimeSeriesService" not in body_text


def test_demo_routes_are_removed():
    client = TestClient(app)
    removed_routes = [
        "/api/time-series/demo/current",
        "/api/time-series/demo/past",
        "/api/time-series/demo/future",
        "/api/time-series/demo/random",
        "/api/service-orchestration/integrated/demo/current",
        "/api/time-series/d/latest",
        "/api/time-series/d/alert-events",
        "/api/time-series/d/future-predictions",
        "/api/time-series/d/troubleshooting",
    ]
    for route in removed_routes:
        response = client.get(route)
        assert response.status_code == 404


def test_service_orchestration_error_uses_real_http_status():
    client = TestClient(app)
    adapter_error = {
        "success": False,
        "stage": "run_integrated_service_query",
        "error_code": "database_unavailable",
        "error_type": "OperationalError",
        "error_message": "database unavailable",
        "_http_status": 503,
    }

    with patch("api_server.run_integrated_service_query", return_value=adapter_error):
        response = client.post(
            "/api/service-orchestration/integrated/query",
            json={"station_scope": "Station_1", "slider_value": 0},
        )

    assert response.status_code == 503
    assert response.json()["error_code"] == "database_unavailable"
    assert "_http_status" not in response.json()
    assert "traceback_tail" not in response.json()


def test_monitoring_validation_returns_422():
    client = TestClient(app)
    response = client.post(
        "/api/service-orchestration/monitoring/run",
        json={"lookback_minutes": "invalid"},
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "invalid_request"
