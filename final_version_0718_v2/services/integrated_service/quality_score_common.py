from __future__ import annotations

from typing import Any


TARGET_FLOW_ML_MIN = 115.0
TARGET_AIR_PRESSURE_BAR = 3.2

STATION_TARGET_SPRAY_WIDTH_MM = {
    "Station_1": 120.0,
    "Station_2": 100.0,
    "Station_3": 82.0,
}


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def target_width_for_station(station_id: str | None) -> float:
    return STATION_TARGET_SPRAY_WIDTH_MM.get(str(station_id), 100.0)


def quality_score_from_formal_row(row: dict[str, Any], station_id: str | None) -> float | None:
    flow = _to_float(row.get("paint_flow_ml_min"))
    pressure = _to_float(row.get("air_pressure_bar"))
    width = _to_float(row.get("spray_width_mm"))
    path_error = _to_float(row.get("path_error_mm"))

    if flow is None and pressure is None and width is None and path_error is None:
        return None

    penalty = 0.0
    if flow is not None:
        flow_error_pct = abs(flow - TARGET_FLOW_ML_MIN) / TARGET_FLOW_ML_MIN * 100.0
        penalty += min(30.0, flow_error_pct * 2.0)
    if pressure is not None:
        pressure_error_pct = abs(pressure - TARGET_AIR_PRESSURE_BAR) / TARGET_AIR_PRESSURE_BAR * 100.0
        penalty += min(25.0, pressure_error_pct * 2.0)
    if width is not None:
        target_width = target_width_for_station(station_id)
        width_error_pct = abs(width - target_width) / target_width * 100.0 if target_width > 0 else 0.0
        penalty += min(30.0, width_error_pct * 2.0)
    if path_error is not None:
        penalty += min(20.0, path_error / 0.15 * 20.0)

    return round(_clamp(100.0 - penalty), 2)
