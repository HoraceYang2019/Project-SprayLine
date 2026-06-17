"""Smoke test Shaoyu0617 FastAPI endpoints.

Start the server first:
    python scripts/run_api_server.py

Then in another PowerShell:
    python scripts/run_api_smoke_test.py --base-url http://127.0.0.1:8001
"""
from __future__ import annotations

import argparse
import json
import urllib.request
import urllib.error


def request_json(method: str, url: str, payload=None):
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            body_json = json.loads(body)
        except Exception:
            body_json = body
        return exc.code, body_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    tests = [
        ("GET", "/", None),
        ("GET", "/api/routes", None),
        ("GET", "/api/versionb/status", None),
        ("GET", "/api/service-orchestration/status", None),
        ("POST", "/api/time-series", {"slider_value": 0, "line_scope": "line_1"}),
        ("POST", "/api/time-series/ui/summary", {"slider_value": 0, "line_scope": "all"}),
        ("POST", "/api/time-series/ui/station-detail", {"slider_value": 0, "line_id": "line_1"}),
        ("POST", "/api/time-series/ui/component-detail", {"slider_value": 0, "line_id": "line_1", "component_name": "nozzle"}),
        ("POST", "/api/service-orchestration/integrated/query", {"slider_value": 0, "station_scope": "Station_1", "window_minutes": 30}),
    ]

    for method, path, payload in tests:
        status, body = request_json(method, base + path, payload)
        ok = 200 <= status < 300
        print(f"[{ 'OK' if ok else 'NG' }] {method} {path} -> HTTP {status}")
        if not ok:
            print(json.dumps(body, ensure_ascii=False, indent=2)[:1500])


if __name__ == "__main__":
    main()
