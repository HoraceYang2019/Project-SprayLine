from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any


STATIONS: dict[str, dict[str, Any]] = {
    "M1": {
        "station_id": "Station_1",
        "name": "底漆站",
        "english_name": "PrimerStation",
        "recipe": "Primer_A",
        "utilization": 78,
        "cycle_time_sec": 42,
        "phase": 0.2,
        "bases": {
            "film_thickness_um": 15.4,
            "paint_flow_ml_min": 116.0,
            "air_pressure_bar": 2.50,
            "spray_width_mm": 116.0,
            "filter_diff_pressure_bar": 0.30,
            "servo_torque_load_pct": 52.0,
            "path_error_mm": 0.060,
            "vibration_g": 0.05,
            "gearbox_temperature_c": 39.0,
            "temperature_c": 26.0,
            "humidity_rh": 55.0,
        },
        "slopes": {
            "filter_diff_pressure_bar": 0.010,
            "servo_torque_load_pct": 0.30,
            "path_error_mm": 0.002,
        },
    },
    "M2": {
        "station_id": "Station_2",
        "name": "面漆站",
        "english_name": "TopcoatStation",
        "recipe": "Topcoat_B",
        "utilization": 72,
        "cycle_time_sec": 47,
        "phase": 1.5,
        "bases": {
            "film_thickness_um": 14.7,
            "paint_flow_ml_min": 103.0,
            "air_pressure_bar": 2.36,
            "spray_width_mm": 103.0,
            "filter_diff_pressure_bar": 0.57,
            "servo_torque_load_pct": 58.0,
            "path_error_mm": 0.085,
            "vibration_g": 0.09,
            "gearbox_temperature_c": 44.0,
            "temperature_c": 29.0,
            "humidity_rh": 63.0,
        },
        "slopes": {
            "filter_diff_pressure_bar": 0.025,
            "servo_torque_load_pct": 0.60,
            "air_pressure_bar": -0.015,
            "spray_width_mm": -0.80,
        },
    },
    "M3": {
        "station_id": "Station_3",
        "name": "金漆站",
        "english_name": "GoldPaintStation",
        "recipe": "Gold_C",
        "utilization": 61,
        "cycle_time_sec": 55,
        "phase": 2.8,
        "bases": {
            "film_thickness_um": 12.4,
            "paint_flow_ml_min": 92.0,
            "air_pressure_bar": 2.24,
            "spray_width_mm": 92.0,
            "filter_diff_pressure_bar": 0.72,
            "servo_torque_load_pct": 71.0,
            "path_error_mm": 0.135,
            "vibration_g": 0.18,
            "gearbox_temperature_c": 53.0,
            "temperature_c": 32.0,
            "humidity_rh": 70.0,
        },
        "slopes": {
            "filter_diff_pressure_bar": 0.035,
            "servo_torque_load_pct": 0.90,
            "path_error_mm": 0.006,
            "air_pressure_bar": -0.030,
            "spray_width_mm": -1.50,
            "temperature_c": 0.25,
        },
    },
}


AMPLITUDES = {
    "film_thickness_um": 0.45,
    "paint_flow_ml_min": 3.8,
    "air_pressure_bar": 0.035,
    "spray_width_mm": 2.6,
    "filter_diff_pressure_bar": 0.025,
    "servo_torque_load_pct": 2.3,
    "path_error_mm": 0.008,
    "vibration_g": 0.015,
    "gearbox_temperature_c": 1.2,
    "temperature_c": 0.8,
    "humidity_rh": 2.2,
}


METRIC_PHASE = {name: index * 0.61 for index, name in enumerate(AMPLITUDES)}


class LocalDataService:
    """本機資料來源。

    以 15 秒 bucket 固定目前快照，避免總覽與 Detail 在同一更新週期拿到不同數值。
    """

    def __init__(self, refresh_seconds: int = 15) -> None:
        self.refresh_seconds = refresh_seconds
        self._lock = RLock()
        self._bucket: int | None = None
        self._anchor: datetime | None = None
        self._current: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    def _bucket_time(self) -> tuple[int, datetime]:
        now = self._utc_now()
        bucket = int(now.timestamp()) // self.refresh_seconds
        anchor = datetime.fromtimestamp(bucket * self.refresh_seconds, tz=timezone.utc)
        return bucket, anchor

    def ensure_current(self) -> datetime:
        bucket, anchor = self._bucket_time()
        with self._lock:
            if self._bucket != bucket:
                self._bucket = bucket
                self._anchor = anchor
                self._current = {
                    station_id: self.generate_station_point(station_id, anchor, anchor)
                    for station_id in STATIONS
                }
            return self._anchor or anchor

    def current_snapshot(self) -> tuple[datetime, dict[str, dict[str, Any]]]:
        anchor = self.ensure_current()
        with self._lock:
            return anchor, {key: dict(value) for key, value in self._current.items()}

    def station_at(self, station_id: str, slider_value: float = 0, mode: str = "time") -> tuple[datetime, dict[str, Any]]:
        anchor = self.ensure_current()
        if mode == "batch":
            # 本機版把每一批視為 18 分鐘，僅模擬 UI 行為。
            hours = float(slider_value) * 18.0 / 60.0
        elif slider_value > 0:
            # 沿用 UI_V5：正值每格為未來 0.5 小時。
            hours = float(slider_value) * 0.5
        else:
            hours = float(slider_value)

        if abs(hours) < 1e-9:
            with self._lock:
                return anchor, dict(self._current[station_id])
        target = anchor + timedelta(hours=hours)
        return target, self.generate_station_point(station_id, target, anchor)

    def generate_station_point(self, station_id: str, timestamp: datetime, anchor: datetime) -> dict[str, Any]:
        station = STATIONS[station_id]
        hours_from_now = (timestamp - anchor).total_seconds() / 3600.0
        absolute_hours = timestamp.timestamp() / 3600.0
        point: dict[str, Any] = {
            "timestamp": timestamp.isoformat(),
            "station_ui_id": station_id,
            "station_id": station["station_id"],
            "data_quality_flag": "normal",
        }

        for metric, base in station["bases"].items():
            amplitude = AMPLITUDES.get(metric, 0.0)
            wave = math.sin(absolute_hours * 1.15 + station["phase"] + METRIC_PHASE.get(metric, 0.0))
            secondary = 0.35 * math.sin(absolute_hours * 2.4 + station["phase"] * 0.5)
            slope = station.get("slopes", {}).get(metric, 0.0)
            value = float(base) + amplitude * (0.75 * wave + secondary) + slope * hours_from_now
            if metric in {"path_error_mm", "vibration_g", "filter_diff_pressure_bar"}:
                value = max(0.0, value)
            digits = 3 if metric in {"path_error_mm", "vibration_g", "filter_diff_pressure_bar"} else 2
            point[metric] = round(value, digits)

        return point

    def trend_points(
        self,
        station_id: str,
        metric: str,
        past_hours: float = 6.0,
        future_hours: float = 2.0,
        step_minutes: int = 15,
    ) -> tuple[datetime, list[dict[str, Any]]]:
        anchor = self.ensure_current()
        points: list[dict[str, Any]] = []
        start = anchor - timedelta(hours=past_hours)
        end = anchor + timedelta(hours=future_hours)
        current = start
        while current <= end:
            raw = self.generate_station_point(station_id, current, anchor)
            delta = (current - anchor).total_seconds()
            time_type = "current" if abs(delta) < step_minutes * 30 else ("past" if delta < 0 else "future")
            points.append(
                {
                    "timestamp": current.isoformat(),
                    "value": raw.get(metric),
                    "time_type": time_type,
                }
            )
            current += timedelta(minutes=step_minutes)
        return anchor, points
