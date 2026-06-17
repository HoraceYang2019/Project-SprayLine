"""Unified FastAPI entry point for Shaoyu0617ver_1.

Run from project root:
    uvicorn webservices.api_server:app --host 0.0.0.0 --port 8001 --reload

This file keeps one public API entry for UI members.  The real route
implementation is placed under webservices/time_series_api/src/api_server.py.
"""
from __future__ import annotations

from pathlib import Path
import importlib.util
import sys

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
API_SRC = Path(__file__).resolve().parent / "time_series_api" / "src"

for path in (PACKAGE_ROOT, API_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

_spec = importlib.util.spec_from_file_location(
    "shaoyu_0617_time_series_api_server_impl",
    API_SRC / "api_server.py",
)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load API implementation from {API_SRC}")

_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

app = _module.app
