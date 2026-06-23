from __future__ import annotations

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


def test_api_root_and_summary():
    client = TestClient(app)

    root = client.get("/")
    assert root.status_code == 200
    assert root.json().get("status") == "running"

    summary = client.post(
        "/api/time-series/ui/summary",
        json={"slider_value": 0, "line_scope": "all"},
    )
    assert summary.status_code == 200

    body = summary.json()
    stations = (
        body.get("stations")
        or body.get("data", {}).get("stations")
        or body.get("summary", {}).get("stations")
    )
    assert isinstance(stations, list)
    assert len(stations) > 0
