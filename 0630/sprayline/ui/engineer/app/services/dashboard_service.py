from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from app.services.diagnosis_service import DiagnosisService
from app.services.local_data_service import LocalDataService, STATIONS
from app.services.rules_service import LEVEL_RANK, RulesService


COMPONENTS: list[dict[str, Any]] = [
    {
        "key": "arm",
        "component_id": "ROBOT_ARM",
        "icon": "🦾",
        "name": "機械手臂",
        "en": "RobotArm",
        "primary_metric": "servo_torque_load_pct",
        "status_metrics": ["servo_torque_load_pct", "path_error_mm"],
        "value_label": "伺服負載",
        "unit": "%",
    },
    {
        "key": "nozzle",
        "component_id": "NOZZLE",
        "icon": "💧",
        "name": "噴嘴",
        "en": "Nozzle",
        "primary_metric": "paint_flow_ml_min",
        "status_metrics": ["paint_flow_ml_min"],
        "value_label": "塗料流量",
        "unit": "ml/min",
    },
    {
        "key": "air",
        "component_id": "AIR_COMPRESSOR",
        "icon": "⚙️",
        "name": "空壓機",
        "en": "AirCompressor",
        "primary_metric": "air_pressure_bar",
        "status_metrics": ["air_pressure_bar"],
        "value_label": "壓力",
        "unit": "bar",
    },
    {
        "key": "width",
        "component_id": "SPRAY_WIDTH",
        "icon": "↔️",
        "name": "噴幅",
        "en": "SprayWidth",
        "primary_metric": "spray_width_mm",
        "status_metrics": ["spray_width_mm"],
        "value_label": "噴幅",
        "unit": "mm",
    },
    {
        "key": "filter",
        "component_id": "FILTER",
        "icon": "🧽",
        "name": "濾網",
        "en": "FilterMesh",
        "primary_metric": "filter_diff_pressure_bar",
        "status_metrics": ["filter_diff_pressure_bar"],
        "value_label": "濾網壓差",
        "unit": "bar",
    },
    {
        "key": "quality",
        "component_id": "QUALITY",
        "icon": "📊",
        "name": "品質",
        "en": "Quality",
        "primary_metric": "quality_score_pct",
        "status_metrics": ["quality_score_pct"],
        "value_label": "品質分數",
        "unit": "%",
    },
]

COMPONENT_BY_KEY = {item["key"]: item for item in COMPONENTS}


class DashboardService:
    def __init__(
        self,
        data_service: LocalDataService,
        rules_service: RulesService,
        diagnosis_service: DiagnosisService,
    ) -> None:
        self.data = data_service
        self.rules = rules_service
        self.diagnosis = diagnosis_service

    @staticmethod
    def _format_number(value: Any, metric: str) -> str:
        if value is None:
            return "--"
        if metric in {"filter_diff_pressure_bar", "path_error_mm", "vibration_g"}:
            return f"{float(value):.3f}".rstrip("0").rstrip(".")
        if metric in {"air_pressure_bar"}:
            return f"{float(value):.2f}".rstrip("0").rstrip(".")
        return f"{float(value):.1f}".rstrip("0").rstrip(".")

    def _component_state(self, raw: dict[str, Any], spec: dict[str, Any]) -> tuple[str, str | None]:
        classified: list[tuple[str, str]] = []
        for sensor in spec["status_metrics"]:
            state = self.rules.classify(sensor, raw.get(sensor))
            classified.append((sensor, state))
        if not classified:
            return "normal", None
        source_sensor, state = max(classified, key=lambda item: LEVEL_RANK.get(item[1], 0))
        return state, source_sensor

    def build_component(self, raw: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
        state, source_sensor = self._component_state(raw, spec)
        level = self.rules.ui_level(state)
        primary_metric = spec["primary_metric"]
        primary_value = raw.get(primary_metric)
        mapping = self.rules.sensor_mapping(source_sensor or primary_metric)
        component = {
            "key": spec["key"],
            "component_id": spec["component_id"],
            "icon": spec["icon"],
            "name": spec["name"],
            "en": spec["en"],
            "level": level,
            "state": state,
            "status_text": {"ok": "正常", "warn": "注意", "bad": "異常"}.get(level, "監控"),
            "value": f"{spec['value_label']} {self._format_number(primary_value, primary_metric)} {spec['unit']}",
            "raw_value": primary_value,
            "unit": spec["unit"],
            "primary_metric": primary_metric,
            "trend_metric": primary_metric,
            "status_source_sensor": source_sensor,
            "status_source_value": raw.get(source_sensor) if source_sensor else None,
            "mapping": {
                "issue_state": mapping.get("issue_state"),
                "cause_id": mapping.get("cause_id"),
                "response_ids": mapping.get("response_ids", []),
            },
        }
        component.update(self.diagnosis.build_detail(component, source_sensor, mapping))
        return component

    def build_station(self, ui_station_id: str, raw: dict[str, Any]) -> dict[str, Any]:
        info = STATIONS[ui_station_id]
        components = [self.build_component(raw, spec) for spec in COMPONENTS]
        worst = max(components, key=lambda item: {"ok": 1, "warn": 2, "bad": 3}.get(item["level"], 0))
        if worst["level"] == "bad":
            overall = "Alarm"
            risk_text = "高風險"
        elif worst["level"] == "warn":
            overall = "Maintenance"
            risk_text = "中風險"
        else:
            overall = "Running"
            risk_text = "低風險"

        spray_rule = self.rules.rule("spray_width_mm") or {}
        spray_normal = spray_rule.get("normal", {})
        return {
            "id": ui_station_id,
            "station_id": info["station_id"],
            "name": info["name"],
            "englishName": info["english_name"],
            "overall": overall,
            "riskText": risk_text,
            "recipe": info["recipe"],
            "temperature": raw.get("temperature_c"),
            "humidity": raw.get("humidity_rh"),
            "utilization": info["utilization"],
            "cycle": info["cycle_time_sec"],
            "sprayWidth": raw.get("spray_width_mm"),
            "targetMin": spray_normal.get("min", 105),
            "targetMax": spray_normal.get("max", 125),
            "timestamp": raw.get("timestamp"),
            "components": components,
            "raw": raw,
        }

    def dashboard_payload(self, slider_value: float = 0, mode: str = "time", anchor_batch_id: str | None = None) -> dict[str, Any]:
        stations = []
        selected_time: datetime | None = None
        first_backend_viewer: dict[str, Any] | None = None
        first_backend_batch_axis: dict[str, Any] | None = None

        for station_id in STATIONS:
            timestamp, raw = self.data.station_at(station_id, slider_value=slider_value, mode=mode, anchor_batch_id=anchor_batch_id)
            selected_time = selected_time or timestamp
            if first_backend_viewer is None and isinstance(raw.get("backend_viewer_state"), dict):
                first_backend_viewer = raw.get("backend_viewer_state")
            if first_backend_batch_axis is None and isinstance(raw.get("backend_batch_axis"), dict):
                first_backend_batch_axis = raw.get("backend_batch_axis")
            stations.append(self.build_station(station_id, raw))

        normal_count = sum(1 for item in stations if item["overall"] == "Running")
        warning_count = len(stations) - normal_count
        risk_count = sum(1 for item in stations if item["riskText"] != "低風險")
        time_type = "current" if slider_value == 0 else ("past" if slider_value < 0 else "future")
        if mode == "batch":
            display_label = (first_backend_viewer or {}).get("display_label") or ("目前批次" if slider_value == 0 else (f"過去第{abs(int(slider_value))}批" if slider_value < 0 else f"未來第{int(slider_value)}批"))
        else:
            display_label = "現在" if slider_value == 0 else (f"過去{abs(slider_value):g}小時" if slider_value < 0 else f"未來{slider_value * 0.5:g}小時")

        anchor = self.data.ensure_current()
        backend_viewer = first_backend_viewer or {}
        backend_anchor = backend_viewer.get("anchor_time")
        backend_future_time = backend_viewer.get("future_time")
        backend_window_start = backend_viewer.get("window_start")
        backend_window_end = backend_viewer.get("window_end")
        viewer_time_type = backend_viewer.get("time_type", time_type)

        # UI time mode uses selected_time as the single point shown under the slider.
        # For future mode, IntegratedSprayLineService intentionally keeps
        # anchor_time/window_end at the latest available DB sample and puts the
        # predicted target point in future_time.  The UI must therefore display
        # future_time, not anchor_time, otherwise the Future chip still appears
        # to point at "now".
        if mode != "batch" and viewer_time_type == "future" and backend_future_time:
            selected_time_iso = backend_future_time
        else:
            selected_time_iso = backend_anchor or (selected_time.isoformat() if selected_time else None)

        viewer_state = {
            "mode": mode,
            "slider_value": slider_value,
            "time_type": viewer_time_type,
            "display_label": display_label,
            "selected_time": selected_time_iso,
            "anchor_time": backend_anchor or anchor.isoformat(),
            "future_time": backend_future_time,
            "window_start": backend_window_start,
            "window_end": backend_window_end,
            "axis_type": (first_backend_viewer or {}).get("axis_type", "batch" if mode == "batch" else "time"),
            "batch_offset": (first_backend_viewer or {}).get("batch_offset"),
            "selected_batch_id": (first_backend_viewer or {}).get("selected_batch_id"),
            "selected_batch": (first_backend_viewer or {}).get("selected_batch"),
            "batch_axis": first_backend_batch_axis,
            "requested_anchor_batch_id": anchor_batch_id,
        }

        return {
            "schema_version": "ui_v6_formal_db_v2",
            "service_name": "UI_V6_FormalDbIntegratedService",
            "generated_at": datetime.now().astimezone().isoformat(),
            "source_type": "FormalDbIntegratedService",
            "update_interval_sec": self.data.refresh_seconds,
            "viewer_state": viewer_state,
            "summary": {
                "total_station_count": len(stations),
                "normal_count": normal_count,
                "warning_count": warning_count,
                "predict_risk_count": risk_count,
            },
            "stations": stations,
            "integration": {
                "database_enabled": bool(os.getenv("SPRAYLINE_API_BASE", "")),
                "used_from_shao_yu_b": [
                    "Station_1/2/3 對應",
                    "Past/Current/Future time slider contract",
                    "sensor_thresholds.json",
                    "sensor_event_mapping.json",
                    "time_series.points / current_snapshot 概念",
                ],
                "added_in_ui_v6": [
                    "正式 DB API current_snapshot",
                    "每15秒更新",
                    "單一時間點檢視",
                    "過去/現在/未來趨勢圖",
                ],
            },
        }

    def component_detail(self, station_id: str, component_key: str, slider_value: float = 0, mode: str = "time", anchor_batch_id: str | None = None) -> dict[str, Any]:
        _, raw = self.data.station_at(station_id, slider_value=slider_value, mode=mode, anchor_batch_id=anchor_batch_id)
        station = self.build_station(station_id, raw)
        component = next(item for item in station["components"] if item["key"] == component_key)
        return {
            "station": {"id": station["id"], "name": station["name"], "englishName": station["englishName"]},
            "component": component,
            "detail_function": "UI_V6FormalDbComponentDetail",
            "detail_source": "Formal DB API + threshold/mapping + UI_V6 diagnosis catalog",
        }

    def station_detail(self, station_id: str, slider_value: float = 0, mode: str = "time", anchor_batch_id: str | None = None) -> dict[str, Any]:
        _, raw = self.data.station_at(station_id, slider_value=slider_value, mode=mode, anchor_batch_id=anchor_batch_id)
        station = self.build_station(station_id, raw)
        issues = [item for item in station["components"] if item["level"] != "ok"]
        return {
            "station": {"id": station["id"], "name": station["name"], "englishName": station["englishName"], "overall": station["overall"]},
            "issues": issues,
            "detail_function": "UI_V6FormalDbStationDetail",
            "detail_source": "Formal DB API + threshold/mapping + UI_V6 diagnosis catalog",
        }

    def trend_payload(self, station_id: str, component_key: str) -> dict[str, Any]:
        spec = COMPONENT_BY_KEY[component_key]
        metric = spec["primary_metric"]
        anchor, points = self.data.trend_points(station_id, metric)
        for point in points:
            state = self.rules.classify(metric, point.get("value"))
            point["state"] = state
            point["level"] = self.rules.ui_level(state)
        reference = self.rules.chart_reference(metric)
        return {
            "station_id": station_id,
            "station_name": STATIONS[station_id]["name"],
            "component_key": component_key,
            "component_name": spec["name"],
            "component_en": spec["en"],
            "metric": metric,
            "unit": spec["unit"],
            "value_label": spec["value_label"],
            "anchor_time": anchor.isoformat(),
            "past_hours": 6,
            "future_hours": 2,
            "points": points,
            "threshold_reference": reference,
            "source": "UI_V6 formal DB time-series following 少榆0616_B版 UI output contract",
        }
