"""API-backed data service for Engineer UI."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx


API_BASE = os.getenv("SPRAYLINE_API_BASE", "").rstrip("/")

STATION_IDS = {"M1": "Station_1", "M2": "Station_2", "M3": "Station_3"}
LINE_IDS = {"M1": "line_1", "M2": "line_2", "M3": "line_3"}

METRIC_TO_COMPONENT = {
    "servo_torque_load_pct": "robot_arm",
    "paint_flow_ml_min": "nozzle",
    "air_pressure_bar": "air_compressor",
    "spray_width_mm": "spray_width",
    "filter_diff_pressure_bar": "filter_mesh",
    "film_thickness_um": "quality_module",
}


def _post(path: str, payload: dict) -> dict:
    if not API_BASE:
        raise RuntimeError("SPRAYLINE_API_BASE is not configured")
    with httpx.Client(timeout=5.0) as client:
        response = client.post(f"{API_BASE}{path}", json=payload)
        response.raise_for_status()
        return response.json()


def _flatten_component_metrics(component_metrics: dict) -> dict:
    """Flatten nested component_metrics groups into a single key→value dict."""
    flat: dict[str, Any] = {}
    for _group, values in component_metrics.items():
        if isinstance(values, dict):
            for k, v in values.items():
                if not isinstance(v, dict) and k not in flat:
                    flat[k] = v
    return flat


class ApiDataService:
    """LocalDataService-compatible adapter that reads from the time-series API."""

    refresh_seconds = 15

    def station_at(
        self,
        station_ui_id: str,
        slider_value: float = 0,
        mode: str = "time",
    ) -> tuple[datetime, dict[str, Any]]:
        line_id = LINE_IDS.get(station_ui_id, station_ui_id)
        data = _post(
            "/api/time-series/ui/station-detail",
            {"line_id": line_id, "slider_value": slider_value, "mode": mode},
        )
        snapshot = data.get("current_snapshot") or {}
        if not snapshot:
            cm_flat = _flatten_component_metrics(data.get("component_metrics") or {})
            top_metrics = data.get("metrics") or {}
            snapshot = {**cm_flat, **top_metrics}
        ts_str = snapshot.get("timestamp") or data.get("generated_at") or datetime.now(timezone.utc).isoformat()
        try:
            ts = datetime.fromisoformat(str(ts_str))
        except Exception:
            ts = datetime.now(timezone.utc)

        point: dict[str, Any] = {
            "timestamp": ts.isoformat(),
            "station_ui_id": station_ui_id,
            "station_id": STATION_IDS.get(station_ui_id, station_ui_id),
            "data_quality_flag": "api",
        }
        for key in (
            "film_thickness_um",
            "paint_flow_ml_min",
            "air_pressure_bar",
            "spray_width_mm",
            "filter_diff_pressure_bar",
            "servo_torque_load_pct",
            "path_error_mm",
            "vibration_g",
            "gearbox_temperature_c",
            "temperature_c",
            "humidity_rh",
        ):
            if key in snapshot:
                point[key] = snapshot[key]
        return ts, point

    def trend_points(
        self,
        station_id: str,
        metric: str,
        past_hours: float = 6.0,
        future_hours: float = 2.0,
        step_minutes: int = 15,
    ) -> tuple[datetime, list[dict[str, Any]]]:
        """Return LocalDataService-compatible trend points from Shaoyu API.

        0620ver_1 fix:
        station-detail returns time_series as {points: [...]}, not {metric: [...]}.
        Convert those points into [{timestamp, value, ...}] so /api/trend-data
        does not fail for quality / film_thickness_um and other component metrics.
        """
        line_id = LINE_IDS.get(station_id, station_id)
        ts = datetime.now(timezone.utc)

        data = _post("/api/time-series/ui/station-detail", {"line_id": line_id, "slider_value": 0})
        raw_points = (data.get("time_series") or {}).get("points", [])

        # Fallback: component-detail may include a more focused time series.
        if not raw_points:
            component_name = METRIC_TO_COMPONENT.get(metric)
            if component_name:
                detail = _post("/api/time-series/ui/component-detail", {
                    "line_id": line_id,
                    "component_name": component_name,
                    "slider_value": 0,
                })
                raw_points = (detail.get("time_series") or {}).get("points", [])

        series: list[dict[str, Any]] = []
        if isinstance(raw_points, list):
            for pt in raw_points:
                if not isinstance(pt, dict):
                    continue
                value = pt.get(metric)
                if value is None and metric == "film_thickness_um":
                    value = pt.get("quality_score_pct") or pt.get("quality_score")
                if value is None:
                    continue
                series.append({
                    "timestamp": pt.get("timestamp"),
                    "value": value,
                    "selected_snapshot": pt.get("selected_snapshot", False),
                    "time_type": pt.get("time_type"),
                })

        return ts, series

    def ensure_current(self) -> datetime:
        return datetime.now(timezone.utc)

    def current_snapshot(self) -> tuple[datetime, dict[str, dict[str, Any]]]:
        now = datetime.now(timezone.utc)
        result = {}
        for ui_id in ("M1", "M2", "M3"):
            _, point = self.station_at(ui_id)
            result[ui_id] = point
        return now, result
