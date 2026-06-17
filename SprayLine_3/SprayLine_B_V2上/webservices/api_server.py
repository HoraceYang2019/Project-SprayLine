"""Unified FastAPI entry point for Shaoyu0616_B + TimeSeriesService API.

Run from project root:
    uvicorn webservices.api_server:app --host 0.0.0.0 --port 8001 --reload
"""
from __future__ import annotations

from pathlib import Path
import importlib.util
import sys

API_SRC = Path(__file__).resolve().parent / "time_series_api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

_spec = importlib.util.spec_from_file_location("time_series_api_server_impl", API_SRC / "api_server.py")
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load TimeSeriesService API from {API_SRC}")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

app = _module.app
