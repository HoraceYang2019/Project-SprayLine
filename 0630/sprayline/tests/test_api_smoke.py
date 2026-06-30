from __future__ import annotations

import json
import os
import sys
from pathlib import Path

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
