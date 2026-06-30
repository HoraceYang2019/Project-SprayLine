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


def quality_score_from_formal_row(row: dict[str, Any], station_id: str | None) -> float | None:  # 根據一筆 sensor/formal row 計算估算品質分數，也就是 OK rate
    flow = _to_float(row.get("paint_flow_ml_min"))  # 取得噴塗流量，並轉成 float
    pressure = _to_float(row.get("air_pressure_bar"))  # 取得空壓值，並轉成 float
    width = _to_float(row.get("spray_width_mm"))  # 取得噴幅寬度，並轉成 float
    path_error = _to_float(row.get("path_error_mm"))  # 取得路徑誤差，並轉成 float

    if flow is None and pressure is None and width is None and path_error is None:  # 如果四個感測欄位都沒有資料
        return None  # 回傳 None，代表這筆資料無法計算品質分數

    penalty = 0.0  # 初始化扣分值，品質分數會從 100 分開始扣
    if flow is not None:  # 如果有噴塗流量資料
        flow_error_pct = abs(flow - TARGET_FLOW_ML_MIN) / TARGET_FLOW_ML_MIN * 100.0  # 計算噴塗流量相對目標值的誤差百分比
        penalty += min(30.0, flow_error_pct * 2.0)  # 噴塗流量誤差扣分，最多扣 30 分
    if pressure is not None:  # 如果有空壓資料
        pressure_error_pct = abs(pressure - TARGET_AIR_PRESSURE_BAR) / TARGET_AIR_PRESSURE_BAR * 100.0  # 計算空壓相對目標值的誤差百分比
        penalty += min(25.0, pressure_error_pct * 2.0)  # 空壓誤差扣分，最多扣 25 分
    if width is not None:  # 如果有噴幅寬度資料
        target_width = target_width_for_station(station_id)  # 根據 station_id 取得該站目標噴幅寬度
        width_error_pct = abs(width - target_width) / target_width * 100.0 if target_width > 0 else 0.0  # 計算噴幅相對目標寬度的誤差百分比
        penalty += min(30.0, width_error_pct * 2.0)  # 噴幅誤差扣分，最多扣 30 分
    if path_error is not None:  # 如果有路徑誤差資料
        penalty += min(20.0, path_error / 0.15 * 20.0)  # 路徑誤差扣分；0.15 mm 對應扣滿 20 分

    return round(_clamp(100.0 - penalty), 2)  # 品質分數 = 100 - 總扣分，經 clamp 限制範圍後四捨五入到小數第 2 位
