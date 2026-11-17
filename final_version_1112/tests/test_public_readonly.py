from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
for rel in ("api", "services", "database"):
    path = str(ROOT / rel)
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("VERSIONB_PATH", str(ROOT / "database"))

import api_server  # noqa: E402
from api_server import app as internal_app  # noqa: E402
from public_readonly import PUBLIC_ROUTE_ALLOWLIST  # noqa: E402


TEST_KEY = "test-public-key-123"
OK_ADAPTER_RESULT = {"success": True, "data": {"ok": True}}


def _load_server(module_name: str, env: dict):
    """Import api_server.py again as a separate module, with its own FastAPI app."""
    spec = importlib.util.spec_from_file_location(module_name, ROOT / "api" / "api_server.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(os.environ, env):
        spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def public_server():
    module = _load_server(
        "api_server_public_readonly_test",
        {"SPRAYLINE_API_MODE": "public_readonly", "SPRAYLINE_PUBLIC_API_KEYS": f"other-key, {TEST_KEY}"},
    )
    return module


def _api_routes(app):
    pairs = set()
    for route in app.routes:
        if isinstance(route, APIRoute):
            for method in route.methods:
                pairs.add((method, route.path))
    return pairs


# ── write_back / commit flag parsing ─────────────────────────────────────────

@pytest.mark.parametrize(
    "value, expected",
    [(False, False), ("false", False), ("False", False), (" FALSE ", False), ("0", False), (0, False), ("no", False),
     (True, True), ("true", True), ("TRUE", True), ("1", True), (1, True), ("yes", True)],
)
def test_integrated_query_write_back_parsing(value, expected):
    client = TestClient(internal_app)
    with patch("api_server.run_integrated_service_query", return_value=OK_ADAPTER_RESULT) as run:
        response = client.post(
            "/api/service-orchestration/integrated/query",
            json={"station_scope": ["Station_1"], "slider_value": 0, "write_back": value},
        )
    assert response.status_code == 200
    assert run.call_args.kwargs["write_back"] is expected


def test_integrated_query_write_back_defaults_to_false():
    client = TestClient(internal_app)
    with patch("api_server.run_integrated_service_query", return_value=OK_ADAPTER_RESULT) as run:
        response = client.post(
            "/api/service-orchestration/integrated/query",
            json={"station_scope": ["Station_1"], "slider_value": 0},
        )
    assert response.status_code == 200
    assert run.call_args.kwargs["write_back"] is False


@pytest.mark.parametrize("value", ["abc", "", "off", 2, -1, 0.0, [], {}])
def test_integrated_query_rejects_non_boolean_write_back(value):
    client = TestClient(internal_app)
    with patch("api_server.run_integrated_service_query", return_value=OK_ADAPTER_RESULT) as run:
        response = client.post(
            "/api/service-orchestration/integrated/query",
            json={"station_scope": ["Station_1"], "slider_value": 0, "write_back": value},
        )
    assert response.status_code == 422
    assert response.json()["error_code"] == "invalid_request"
    run.assert_not_called()


def test_run_once_still_writes_back():
    client = TestClient(internal_app)
    with patch("api_server.run_integrated_service_query", return_value=OK_ADAPTER_RESULT) as run:
        response = client.post(
            "/api/service-orchestration/integrated/run-once",
            json={"station_scope": ["Station_1"], "slider_value": 0, "write_back": "false"},
        )
    assert response.status_code == 200
    assert run.call_args.kwargs["write_back"] is True


@pytest.mark.parametrize("value, expected", [(None, True), (True, True), ("true", True), (False, False), ("false", False), ("0", False)])
def test_future_save_commit_parsing(value, expected):
    client = TestClient(internal_app)
    body = {"station": "Station_1"}
    if value is not None:
        body["commit"] = value
    with patch("api_server.save_future_prediction_payload_for_api", return_value=OK_ADAPTER_RESULT) as save:
        response = client.post("/api/service-orchestration/future/save", json=body)
    assert response.status_code == 200
    assert save.call_args.kwargs["commit"] is expected


def test_future_save_rejects_non_boolean_commit():
    client = TestClient(internal_app)
    with patch("api_server.save_future_prediction_payload_for_api", return_value=OK_ADAPTER_RESULT) as save:
        response = client.post("/api/service-orchestration/future/save", json={"commit": "maybe"})
    assert response.status_code == 422
    save.assert_not_called()


# ── internal mode is unchanged ───────────────────────────────────────────────

def test_internal_mode_keeps_write_routes_and_needs_no_key():
    routes = _api_routes(internal_app)
    for pair in [
        ("POST", "/api/service-orchestration/integrated/run-once"),
        ("POST", "/api/service-orchestration/future/save"),
        ("POST", "/api/service-orchestration/monitoring/run"),
        ("PATCH", "/api/alerts/{event_id}/acknowledge"),
        ("POST", "/api/manager/engineer-tasks"),
        ("POST", "/api/engineer-task-access/ack"),
    ]:
        assert pair in routes

    body = TestClient(internal_app).get("/api/routes").json()
    assert body["api_mode"] == "internal"
    assert body["route_count"] > len(PUBLIC_ROUTE_ALLOWLIST)


# ── public read-only mode ────────────────────────────────────────────────────

def test_public_mode_refuses_to_start_without_key():
    with pytest.raises(RuntimeError, match="SPRAYLINE_PUBLIC_API_KEYS"):
        _load_server(
            "api_server_public_no_key_test",
            {"SPRAYLINE_API_MODE": "public_readonly", "SPRAYLINE_PUBLIC_API_KEYS": " , "},
        )


def test_public_mode_keeps_only_allowlisted_routes(public_server):
    routes = _api_routes(public_server.app) - {("HEAD", path) for _, path in PUBLIC_ROUTE_ALLOWLIST}
    assert routes == set(PUBLIC_ROUTE_ALLOWLIST)
    # The allowlist must not name a route that does not exist.
    assert set(PUBLIC_ROUTE_ALLOWLIST) <= _api_routes(internal_app)


def test_public_mode_does_not_touch_internal_app(public_server):
    assert ("POST", "/api/service-orchestration/integrated/run-once") in _api_routes(internal_app)


@pytest.mark.parametrize(
    "method, path",
    [
        ("POST", "/api/service-orchestration/integrated/query"),
        ("POST", "/api/service-orchestration/integrated/run-once"),
        ("POST", "/api/service-orchestration/future/save"),
        ("POST", "/api/service-orchestration/future/payload"),
        ("POST", "/api/service-orchestration/monitoring/run"),
        ("PATCH", "/api/alerts/ALERT_1/acknowledge"),
        ("POST", "/api/manager/engineer-tasks"),
        ("GET", "/api/manager/engineer-tasks"),
        ("GET", "/api/manager/station-engineer-assignments"),
        ("GET", "/api/engineer-task-access/task"),
        ("POST", "/api/engineer-task-access/ack"),
        ("GET", "/api/database/status"),
        ("GET", "/api/service-orchestration/status"),
        ("POST", "/api/time-series"),
    ],
)
def test_public_mode_hides_write_and_internal_routes(public_server, method, path):
    client = TestClient(public_server.app)
    response = client.request(method, path, headers={"X-API-Key": TEST_KEY}, json={})
    assert response.status_code in (404, 405)


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}, {"X-API-Key": ""}])
def test_public_mode_requires_valid_key(public_server, headers):
    client = TestClient(public_server.app)
    response = client.get("/api/alerts/summary", headers=headers)
    assert response.status_code == 401
    assert response.json()["error_code"] == "api_key_required"


def test_public_mode_accepts_every_configured_key(public_server):
    client = TestClient(public_server.app)
    with patch.object(public_server, "AlertHistorySummary", return_value=(200, {"success": True})):
        for key in ("other-key", TEST_KEY):
            response = client.get("/api/alerts/summary", headers={"X-API-Key": key})
            assert response.status_code == 200


def test_public_mode_read_post_works_with_key(public_server):
    client = TestClient(public_server.app)
    with patch.object(public_server, "run_integrated_service_query", return_value=OK_ADAPTER_RESULT) as run:
        response = client.post(
            "/api/time-series/ui/summary",
            headers={"X-API-Key": TEST_KEY},
            json={"slider_value": 0, "line_scope": "all", "write_back": "true"},
        )
    assert response.status_code == 200
    assert run.call_args.kwargs["write_back"] is False


def test_public_mode_spec_and_health_need_no_key(public_server):
    client = TestClient(public_server.app)

    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["api_mode"] == "public_readonly"
    assert "run-once" not in root.text

    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 200

    routes = client.get("/api/routes").json()
    assert routes["api_mode"] == "public_readonly"
    listed = {(m, r["path"]) for r in routes["routes"] for m in r["methods"] if m != "HEAD"}
    assert listed == {pair for pair in PUBLIC_ROUTE_ALLOWLIST if pair[1].startswith("/api")}

    spec = client.get("/openapi.json").json()
    spec_pairs = {(m.upper(), p) for p, ops in spec["paths"].items() for m in ops}
    assert spec_pairs == set(PUBLIC_ROUTE_ALLOWLIST)
