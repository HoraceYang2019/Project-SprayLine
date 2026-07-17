from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import RLock
from time import time
from typing import Any

from app.services.diagnosis_service import DiagnosisService
from app.services.rules_service import LEVEL_RANK, RulesService
from app.services.webservices_client import WebservicesClient, WebservicesRequestError


STATIONS: dict[str, dict[str, str]] = {
    "M1": {"line_id": "line_1", "station_id": "Station_1", "name": "底漆站", "english_name": "Primer Station"},
    "M2": {"line_id": "line_2", "station_id": "Station_2", "name": "面漆站", "english_name": "Topcoat Station"},
    "M3": {"line_id": "line_3", "station_id": "Station_3", "name": "金漆站", "english_name": "Gold Paint Station"},
}
LINE_TO_UI = {value["line_id"]: key for key, value in STATIONS.items()}
STATION_TO_UI = {value["station_id"]: key for key, value in STATIONS.items()}

COMPONENTS: list[dict[str, Any]] = [
    {
        "key": "arm",
        "service_name": "robot_arm",
        "component_id": "ROBOT_ARM",
        "icon": "🦾",
        "name": "機械手臂",
        "en": "RobotArm",
        "primary_metric": "servo_torque_load_pct",
        "status_metrics": ["servo_torque_load_pct"],
        "value_label": "伺服負載",
        "unit": "%",
    },
    {
        "key": "nozzle",
        "service_name": "nozzle",
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
        "service_name": "air_compressor",
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
        "service_name": "spray_width",
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
        "service_name": "filter_mesh",
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
        "service_name": "quality_module",
        "component_id": "QUALITY",
        "icon": "📏",
        "name": "品質",
        "en": "Quality",
        "primary_metric": "film_thickness_um",
        "status_metrics": ["film_thickness_um"],
        "value_label": "膜厚",
        "unit": "µm",
    },
]
COMPONENT_BY_KEY = {item["key"]: item for item in COMPONENTS}
COMPONENT_BY_SERVICE_NAME = {item["service_name"]: item for item in COMPONENTS}


class DashboardService:
    """Translate 少榆0617ver_1 Service API responses into the dashboard format.

    This class intentionally does not generate station cards from local demo data.
    Summary, station cards, station details and component details all come from
    the three dedicated Webservices UI endpoints.
    """

    def __init__(
        self,
        rules_service: RulesService,
        diagnosis_service: DiagnosisService,
        webservices_client: WebservicesClient,
    ) -> None:
        self.rules = rules_service
        self.diagnosis = diagnosis_service
        self.webservices = webservices_client
        self.refresh_seconds = 15
        self._lock = RLock()
        self._station_cache: dict[tuple[int, str, float, str], dict[str, Any]] = {}
        self._component_cache: dict[tuple[int, str, float, str, str], dict[str, Any]] = {}
        self._trend_cache: dict[tuple[int, str, float, str, str], dict[str, Any]] = {}

    @staticmethod
    def _format_number(value: Any, metric: str) -> str:
        if value is None:
            return "--"
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        if metric in {"filter_diff_pressure_bar", "path_error_mm", "vibration_g"}:
            return f"{number:.3f}".rstrip("0").rstrip(".")
        if metric in {"air_pressure_bar", "pressure_bar"}:
            return f"{number:.2f}".rstrip("0").rstrip(".")
        return f"{number:.1f}".rstrip("0").rstrip(".")

    @staticmethod
    def _ui_station_id(value: Any) -> str | None:
        if value in STATIONS:
            return str(value)
        return LINE_TO_UI.get(str(value)) or STATION_TO_UI.get(str(value))

    @staticmethod
    def _time_type(slider_value: float) -> str:
        if float(slider_value) < 0:
            return "past"
        if float(slider_value) > 0:
            return "future"
        return "current"

    @staticmethod
    def _display_label(mode: str, slider_value: float) -> str:
        if mode == "batch":
            if slider_value == 0:
                return "目前批次"
            return f"過去第{abs(int(slider_value))}批" if slider_value < 0 else f"未來第{int(slider_value)}批"
        if slider_value == 0:
            return "現在"
        return f"過去{abs(slider_value):g}小時" if slider_value < 0 else f"未來{slider_value * 0.5:g}小時"

    @staticmethod
    def _selected_time(mode: str, slider_value: float) -> datetime:
        """Fallback display time used only when the Service API is unavailable.

        Successful responses use viewer_state.anchor_time/future_time from the
        database-backed Service API. BatchMode must not invent an 18-minute
        interval on the UI side.
        """
        now = datetime.now(timezone.utc)
        if mode == "batch":
            return now
        hours = float(slider_value) if slider_value < 0 else float(slider_value) * 0.5
        return now + timedelta(hours=hours)

    def new_snapshot_seed(self, mode: str, slider_value: float) -> int:
        """One deterministic 32-bit seed per 15-second UI snapshot.

        Keeping the seed below 2^31 avoids platform-specific random-seed limits
        while still reusing exactly the same snapshot across summary, station,
        component and trend requests.
        """
        bucket = int(time() // self.refresh_seconds) % 10_000_000
        mode_offset = 700_000_000 if mode == "batch" else 0
        slider_offset = int(round((float(slider_value) + 50) * 10))
        return int((91_000 + mode_offset + bucket * 100 + slider_offset) % 2_147_483_647)

    @staticmethod
    def _state_to_level(state: Any) -> str:
        normalized = str(state or "normal").lower()
        if normalized in {"fault", "alarm", "error", "high"}:
            return "bad"
        if normalized in {"warning", "warn", "maintenance", "medium"}:
            return "warn"
        return "ok"

    @staticmethod
    def _level_to_overall(level: str) -> str:
        return {"bad": "Alarm", "warn": "Maintenance", "ok": "Running"}.get(level, "Maintenance")

    @staticmethod
    def _overall_to_risk_text(overall: str) -> str:
        return {"Alarm": "高風險", "Maintenance": "中風險", "Running": "低風險"}.get(overall, "待確認")

    @staticmethod
    def _worst_level_from_components(components: list[dict[str, Any]]) -> str:
        # Use component states as the source of truth for station aggregation.
        # If a station has any red component, the whole station must not remain green.
        rank = {"ok": 1, "warn": 2, "bad": 3}
        levels = [str(item.get("level") or "ok") for item in components]
        if not levels:
            return "ok"
        return max(levels, key=lambda level: rank.get(level, 0))

    @staticmethod
    def _parse_service_time(value: Any) -> datetime | None:
        if value is None:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    def _component_state_from_data(self, data: dict[str, Any], spec: dict[str, Any]) -> tuple[str, str | None]:
        classified: list[tuple[str, str]] = []
        for sensor in spec["status_metrics"]:
            if data.get(sensor) is None:
                continue
            classified.append((sensor, self.rules.classify(sensor, data.get(sensor))))
        if not classified:
            return "normal", None
        source_sensor, state = max(classified, key=lambda item: LEVEL_RANK.get(item[1], 0))
        return state, source_sensor

    @staticmethod
    def _overview_map(station_detail: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {
            str(item.get("component_name")): item
            for item in (station_detail.get("component_overview") or [])
            if isinstance(item, dict) and item.get("component_name")
        }

    @staticmethod
    def _merge_metric_dict(target: dict[str, Any], source: Any) -> None:
        """Merge only flat scalar metric-like values from a Service API object.

        少榆 API in integrated mode may put sensor values in different layers:
        - root.metrics
        - root.current_snapshot
        - data.metrics
        - data.current_snapshot
        Older UI_V16 only returned root.data directly. When data contained
        current_snapshot/time_series instead of flat metric keys, component cards
        could only show 「API 無資料」 even though the API response already had values.
        """
        if not isinstance(source, dict):
            return
        for key, value in source.items():
            if isinstance(value, (dict, list, tuple)):
                continue
            if value is not None:
                target[str(key)] = value

    @classmethod
    def _component_data_from_response(cls, response: dict[str, Any]) -> dict[str, Any]:
        """Return a flat metric map from station-detail/component-detail response.

        Supported response shapes include:
        1. {"metrics": {"servo_torque_load_pct": 59.46}}
        2. {"current_snapshot": {"servo_torque_load_pct": 59.46, ...}}
        3. {"data": {"current_snapshot": {...}, "time_series": {...}}}
        4. {"data": {"metrics": {...}}}
        5. {"data": {"servo_torque_load_pct": 59.46}}
        """
        output: dict[str, Any] = {}

        # Merge the current snapshot first, then the endpoint's visible metrics.
        # In Future mode, metrics already contain canonical predicted values and
        # must not be overwritten by the anchor snapshot.
        cls._merge_metric_dict(output, response.get("current_snapshot"))
        cls._merge_metric_dict(output, response.get("metrics"))

        future = response.get("future_prediction")
        if isinstance(future, dict):
            cls._merge_metric_dict(output, future.get("predicted_metrics"))

        data = response.get("data")
        if isinstance(data, dict):
            # Some endpoints put the values directly under data; others nest them.
            cls._merge_metric_dict(output, data.get("current_snapshot"))
            cls._merge_metric_dict(output, data)
            cls._merge_metric_dict(output, data.get("metrics"))
            nested_future = data.get("future_prediction")
            if isinstance(nested_future, dict):
                cls._merge_metric_dict(output, nested_future.get("predicted_metrics"))

        return output

    @staticmethod
    def _service_detail_from_troubleshooting(items: list[dict[str, Any]]) -> dict[str, Any] | None:
        valid = [item for item in items if isinstance(item, dict)]
        if not valid:
            return None
        first = valid[0]
        issue = first.get("state_name") or first.get("state_description") or "Service API 偵測到需要注意的狀態。"
        reason = first.get("state_description") or first.get("cause") or first.get("message") or "請依感測器狀態進一步確認。"
        countermeasures: list[str] = []
        response_ids: list[str] = []
        for item in valid:
            text = item.get("countermeasure")
            if text and text not in countermeasures:
                countermeasures.append(str(text))
            response_id = item.get("countermeasure_id")
            if response_id and response_id not in response_ids:
                response_ids.append(str(response_id))
        return {
            "issue": str(issue),
            "reason": str(reason),
            "solution": "；".join(countermeasures) if countermeasures else "依 Service API 診斷結果安排檢查。",
            "issue_state": first.get("troubleshooting_state"),
            "cause_id": first.get("cause_id"),
            "response_ids": response_ids,
            "diagnosis_source": "Webservices troubleshooting",
        }

    def _build_component(
        self,
        station_detail: dict[str, Any],
        spec: dict[str, Any],
        *,
        component_response: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        service_name = spec["service_name"]
        if component_response is not None:
            data = self._component_data_from_response(component_response)
            state_item = component_response.get("component_state") or {}
            troubleshooting = component_response.get("troubleshooting") or []
        else:
            component_metrics = station_detail.get("component_metrics") or {}
            nested_component_data = component_metrics.get(service_name) or {}
            data = self._component_data_from_response(station_detail)
            if isinstance(nested_component_data, dict):
                # Keep component-specific values if present, while still allowing
                # station-detail root metrics/current_snapshot to fill missing keys.
                data.update({k: v for k, v in nested_component_data.items() if v is not None})
            state_item = self._overview_map(station_detail).get(service_name) or {}
            troubleshooting = [
                item
                for item in (station_detail.get("troubleshooting") or [])
                if isinstance(item, dict) and item.get("component_name") == service_name
            ]

        primary_metric = spec["primary_metric"]
        primary_value = data.get(primary_metric)
        available = primary_value is not None

        # V20: use the sensor values + Shaoyu 0620 thresholds as the judgement
        # source of truth. Some integrated component-detail responses still report
        # component_state=normal even when the numeric metric has crossed the
        # threshold. If we trust that field first, past/current/future all stay
        # green. We therefore classify the actual returned metrics first and use
        # component_state only as a fallback when no metric exists.
        state, source_sensor = self._component_state_from_data(data, spec)
        if not available and source_sensor is None:
            fallback_state = str(state_item.get("state") or "normal").lower()
            state = fallback_state if fallback_state in {"normal", "warning", "fault"} else "warning"
            triggered = state_item.get("triggered_sensors") or []
            if triggered and isinstance(triggered[0], dict):
                source_sensor = triggered[0].get("sensor_name")
            elif triggered and isinstance(triggered[0], str):
                source_sensor = triggered[0]

        level = self._state_to_level(state)
        if not available:
            level = "warn"
            state = "warning"
        value_text = (
            f"{spec['value_label']} {self._format_number(primary_value, primary_metric)} {spec['unit']}"
            if available
            else f"{spec['value_label']} API 無資料"
        )

        mapping = self.rules.sensor_mapping(source_sensor or primary_metric)
        component = {
            "key": spec["key"],
            "service_component_name": service_name,
            "component_id": spec["component_id"],
            "icon": spec["icon"],
            "name": spec["name"],
            "en": spec["en"],
            "level": level,
            "state": state or "normal",
            "status_text": {"ok": "正常", "warn": "注意", "bad": "異常"}.get(level, "監控"),
            "value": value_text,
            "raw_value": primary_value,
            "unit": spec["unit"],
            "primary_metric": primary_metric,
            "trend_metric": primary_metric,
            "status_source_sensor": source_sensor,
            "status_source_value": data.get(source_sensor) if source_sensor else primary_value,
            "available": available,
            "service_data": data,
            "mapping": {
                "issue_state": mapping.get("issue_state"),
                "cause_id": mapping.get("cause_id"),
                "response_ids": mapping.get("response_ids", []),
            },
        }

        service_detail = self._service_detail_from_troubleshooting(troubleshooting)
        if service_detail:
            component.update(service_detail)
        else:
            component.update(self.diagnosis.build_detail(component, source_sensor, mapping))
            component["diagnosis_source"] = "UI rule fallback (Service API did not return troubleshooting)"
        return component

    def _build_station(
        self,
        summary_station: dict[str, Any],
        station_detail: dict[str, Any],
        *,
        component_responses: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        ui_id = (
            self._ui_station_id(station_detail.get("ui_id"))
            or self._ui_station_id(station_detail.get("line_id"))
            or self._ui_station_id(summary_station.get("id"))
        )
        if ui_id not in STATIONS:
            raise ValueError(f"Unknown station returned by Webservices: {ui_id}")

        ref = STATIONS[ui_id]
        metrics = station_detail.get("metrics") or {}
        process = station_detail.get("process_parameters") or {}
        spray = station_detail.get("spray_width_image") or {}

        # V20: station cards must use the same component-detail function that
        # clicking a component uses. station-detail gives the station shell, while
        # component-detail gives the real component metrics and judgement basis.
        responses = component_responses or {}
        components = [
            self._build_component(
                station_detail,
                spec,
                component_response=responses.get(spec["key"]),
            )
            for spec in COMPONENTS
        ]

        # V18/V20: station status is aggregated from the six component cards.
        # The old station-detail/summary response could still say Running,
        # while component-detail already reported warning/fault values. That made
        # the station header and top summary stay green.
        worst_level = self._worst_level_from_components(components)
        overall = self._level_to_overall(worst_level)
        risk_text = self._overall_to_risk_text(overall)

        viewer_state = station_detail.get("viewer_state") or {}
        snapshot_timestamp = (station_detail.get("current_snapshot") or {}).get("ts")
        if viewer_state.get("time_type") == "future":
            station_timestamp = (
                viewer_state.get("future_time")
                or process.get("timestamp")
                or snapshot_timestamp
                or viewer_state.get("anchor_time")
                or station_detail.get("generated_at")
            )
        else:
            station_timestamp = (
                process.get("timestamp")
                or snapshot_timestamp
                or viewer_state.get("anchor_time")
                or station_detail.get("anchor_time")
                or station_detail.get("data_anchor_time")
                or station_detail.get("generated_at")
            )

        target_min = spray.get("target_min_mm")
        target_max = spray.get("target_max_mm")
        if target_min is None or target_max is None:
            width_data = (station_detail.get("component_metrics") or {}).get("spray_width") or {}
            target_min = width_data.get("target_min_mm", 105)
            target_max = width_data.get("target_max_mm", 125)

        return {
            "id": ui_id,
            "line_id": station_detail.get("line_id") or ref["line_id"],
            "station_id": process.get("station_id") or ref["station_id"],
            "name": station_detail.get("name") or summary_station.get("name") or ref["name"],
            "englishName": station_detail.get("english_name") or summary_station.get("english_name") or ref["english_name"],
            "overall": overall,
            "riskText": risk_text,
            "recipe": process.get("recipe_name") or summary_station.get("recipe") or "--",
            "temperature": process.get("temperature_c", metrics.get("temperature_c")),
            "humidity": process.get("humidity_rh", metrics.get("humidity_rh")),
            "utilization": process.get("utilization_pct", summary_station.get("utilization_pct")),
            "cycle": process.get("cycle_time_sec", summary_station.get("cycle_time_sec")),
            "sprayWidth": metrics.get("spray_width_mm", summary_station.get("spray_width_mm")),
            "targetMin": target_min,
            "targetMax": target_max,
            "timestamp": station_timestamp,
            "aggregation_source": "component_status_v18",
            "components": components,
            "metrics": metrics,
            "process_parameters": process,
            "service_api": {
                "route": "POST /api/time-series/ui/station-detail",
                "output_type": station_detail.get("output_type"),
                "request_id": station_detail.get("request_id"),
                "source": station_detail.get("source"),
            },
        }

    def _build_summary_fallback_station(self, ui_id: str, summary_station: dict[str, Any], error: str) -> dict[str, Any]:
        """Render a visible station card when station-detail fails.

        The station-detail function is still called first. This fallback only
        prevents the whole dashboard from becoming blank and clearly marks that
        detailed component values were not received.
        """
        ref = STATIONS[ui_id]
        overview = self._overview_map({"component_overview": summary_station.get("component_overview") or []})
        components: list[dict[str, Any]] = []
        summary_metric_map = {
            "nozzle": ("paint_flow_ml_min", "塗料流量", "ml/min"),
            "air_compressor": ("air_pressure_bar", "壓力", "bar"),
            "spray_width": ("spray_width_mm", "噴幅", "mm"),
        }
        for spec in COMPONENTS:
            state_item = overview.get(spec["service_name"]) or {}
            state = str(state_item.get("state") or "normal").lower()
            level = self._state_to_level(state)
            metric_info = summary_metric_map.get(spec["service_name"])
            raw_value = None
            value_text = f"{spec['value_label']} Station API 無資料"
            if metric_info:
                metric, label, unit = metric_info
                raw_value = summary_station.get(metric)
                if raw_value is not None:
                    value_text = f"{label} {self._format_number(raw_value, metric)} {unit}"
            components.append({
                "key": spec["key"],
                "service_component_name": spec["service_name"],
                "component_id": spec["component_id"],
                "icon": spec["icon"],
                "name": spec["name"],
                "en": spec["en"],
                "level": level,
                "state": state,
                "status_text": "資料待確認",
                "value": value_text,
                "raw_value": raw_value,
                "unit": spec["unit"],
                "primary_metric": spec["primary_metric"],
                "trend_metric": spec["primary_metric"],
                "available": raw_value is not None,
                "issue": "Station Detail Service API 讀取失敗",
                "reason": error,
                "solution": "確認 ServiceAPI 8001 是否為本包版本後，按重新檢查。",
                "diagnosis_source": "summary fallback after station-detail error",
            })
        overall = self._level_to_overall(self._state_to_level(summary_station.get("state")))
        return {
            "id": ui_id,
            "line_id": summary_station.get("line_id") or ref["line_id"],
            "station_id": ref["station_id"],
            "name": summary_station.get("name") or ref["name"],
            "englishName": summary_station.get("english_name") or ref["english_name"],
            "overall": overall,
            "riskText": summary_station.get("risk_text") or "Station API 資料異常",
            "recipe": summary_station.get("recipe") or "--",
            "temperature": summary_station.get("temperature_c"),
            "humidity": summary_station.get("humidity_rh"),
            "utilization": summary_station.get("utilization_pct"),
            "cycle": summary_station.get("cycle_time_sec"),
            "sprayWidth": summary_station.get("spray_width_mm"),
            "targetMin": summary_station.get("target_min_mm", 105),
            "targetMax": summary_station.get("target_max_mm", 125),
            "timestamp": summary_station.get("generated_at"),
            "components": components,
            "metrics": {},
            "process_parameters": {},
            "service_api": {
                "route": "POST /api/time-series/ui/station-detail",
                "output_type": "station_detail_failed_summary_fallback",
                "error": error,
            },
        }

    def _cache_station(self, seed: int, mode: str, slider_value: float, station_id: str, response: dict[str, Any]) -> None:
        with self._lock:
            self._station_cache[(seed, mode, float(slider_value), station_id)] = response
            if len(self._station_cache) > 200:
                for key in list(self._station_cache)[:80]:
                    self._station_cache.pop(key, None)

    def _fetch_station_response(self, station_id: str, mode: str, slider_value: float, seed: int, *, use_cache: bool = True) -> dict[str, Any]:
        key = (seed, mode, float(slider_value), station_id)
        with self._lock:
            cached = self._station_cache.get(key)
        if use_cache and cached is not None:
            return cached
        line_id = STATIONS[station_id]["line_id"]
        response = self.webservices.fetch_station_detail(
            line_id=line_id,
            mode=mode,
            slider_value=slider_value,
            random_seed=seed,
        )
        self._cache_station(seed, mode, slider_value, station_id, response)
        return response

    def _fetch_component_response(
        self,
        station_id: str,
        component_key: str,
        mode: str,
        slider_value: float,
        seed: int,
        *,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        key = (seed, mode, float(slider_value), station_id, component_key)
        with self._lock:
            cached = self._component_cache.get(key)
        if use_cache and cached is not None:
            return cached
        spec = COMPONENT_BY_KEY[component_key]
        response = self.webservices.fetch_component_detail(
            line_id=STATIONS[station_id]["line_id"],
            component_name=spec["service_name"],
            mode=mode,
            slider_value=slider_value,
            random_seed=seed,
        )
        with self._lock:
            self._component_cache[key] = response
            if len(self._component_cache) > 500:
                for old_key in list(self._component_cache)[:180]:
                    self._component_cache.pop(old_key, None)
        return response

    def dashboard_payload(self, slider_value: float = 0, mode: str = "time") -> dict[str, Any]:
        seed = self.new_snapshot_seed(mode, slider_value)
        selected_time = self._selected_time(mode, slider_value)

        try:
            database_status = self.webservices.database_status()
        except WebservicesRequestError as exc:
            database_status = {"connected": False, "error_message": str(exc)}

        if not database_status.get("connected"):
            return {
                "schema_version": "ui_v16_database_integrated_v1",
                "service_name": "UI_V16_DatabaseIntegrated",
                "generated_at": datetime.now().astimezone().isoformat(),
                "snapshot_seed": seed,
                "viewer_state": {
                    "mode": mode,
                    "slider_value": slider_value,
                    "time_type": self._time_type(slider_value),
                    "display_label": self._display_label(mode, slider_value),
                    "selected_time": selected_time.isoformat(),
                },
                "summary": {"total_station_count": 0, "normal_count": 0, "warning_count": 0, "predict_risk_count": 0},
                "stations": [],
                "integration": {
                    "webservices_connected": True,
                    "database_connected": False,
                    "data_received": False,
                    "api_mode": self.webservices.source_mode,
                    "webservices_url": self.webservices.base_url,
                    "database_required": True,
                    "database_status": database_status,
                    "error": database_status.get("error_message") or "PostgreSQL 未連線",
                    "route_status": {"summary": False, "station_detail": False, "component_detail": None},
                },
            }

        try:
            summary_response = self.webservices.fetch_summary(
                mode=mode,
                slider_value=slider_value,
                random_seed=seed,
            )
        except WebservicesRequestError as exc:
            return {
                "schema_version": "ui_v16_database_integrated_v1",
                "service_name": "UI_V16_DatabaseIntegrated",
                "generated_at": datetime.now().astimezone().isoformat(),
                "snapshot_seed": seed,
                "viewer_state": {
                    "mode": mode,
                    "slider_value": slider_value,
                    "time_type": self._time_type(slider_value),
                    "display_label": self._display_label(mode, slider_value),
                    "selected_time": selected_time.isoformat(),
                },
                "summary": {"total_station_count": 0, "normal_count": 0, "warning_count": 0, "predict_risk_count": 0},
                "stations": [],
                "integration": {
                    "webservices_connected": True,
                    "data_received": False,
                    "api_mode": self.webservices.source_mode,
                    "webservices_url": self.webservices.base_url,
                    "database_required": True,
                    "database_connected": True,
                    "database_status": database_status,
                    "error": str(exc),
                    "route_status": {"summary": False, "station_detail": False, "component_detail": None},
                },
            }

        summary_stations = summary_response.get("stations") or []
        station_cards: list[dict[str, Any]] = []
        station_errors: dict[str, str] = {}
        component_errors: dict[str, dict[str, str]] = {}
        station_route_ok = 0
        component_route_ok = 0
        component_route_expected = 0  # component-detail is lazy in 0718_v2

        summary_by_id: dict[str, dict[str, Any]] = {}
        for item in summary_stations:
            if not isinstance(item, dict):
                continue
            ui_id = self._ui_station_id(item.get("id")) or self._ui_station_id(item.get("line_id"))
            if ui_id in STATIONS:
                summary_by_id[ui_id] = item

        # Always call the dedicated station-detail function once for each of M1/M2/M3.
        # Fixed ordering also makes cross-computer tests easier to compare.
        for ui_id in STATIONS:
            summary_station = summary_by_id.get(ui_id, {
                "id": ui_id,
                "line_id": STATIONS[ui_id]["line_id"],
                "name": STATIONS[ui_id]["name"],
                "english_name": STATIONS[ui_id]["english_name"],
            })
            try:
                detail_response = self._fetch_station_response(
                    ui_id, mode, slider_value, seed, use_cache=False
                )
                # 0718_v2 performance fix: station-detail already contains the six
                # component metrics/current_snapshot. Do not issue another 18
                # component-detail requests on every slider movement. The dedicated
                # component endpoint is still called when the user clicks a card or
                # opens a trend.
                station_card = self._build_station(
                    summary_station,
                    detail_response,
                    component_responses=None,
                )
                station_cards.append(station_card)
                station_route_ok += 1
            except Exception as exc:
                error_text = str(exc)
                station_errors[ui_id] = error_text
                station_cards.append(self._build_summary_fallback_station(ui_id, summary_station, error_text))

        remote_summary = summary_response.get("summary") or {}

        # V18: do not trust remote summary counts after component metrics are read.
        # Recalculate the top cards from the station cards that were just built.
        # Running = all components OK; Maintenance = worst component warning;
        # Alarm = at least one bad component, counted as PredictRisk.
        normal_count = sum(1 for item in station_cards if item["overall"] == "Running")
        warning_count = sum(1 for item in station_cards if item["overall"] == "Maintenance")
        risk_count = sum(1 for item in station_cards if item["overall"] == "Alarm")
        total_count = len(station_cards)

        viewer = summary_response.get("viewer_state") or {}

        # 0718_v2: the database clock is the only data-time source.  The previous
        # V29 code replaced PostgreSQL timestamps with datetime.now(), so the
        # TimePointViewer, station cards and charts referred to different years.
        service_time_raw = (
            viewer.get("future_time")
            if (viewer.get("time_type") or self._time_type(slider_value)) == "future"
            else viewer.get("anchor_time")
        )
        service_selected_time = self._parse_service_time(service_time_raw)
        if service_selected_time is None:
            for station in station_cards:
                service_selected_time = self._parse_service_time(station.get("timestamp"))
                if service_selected_time is not None:
                    break
        if service_selected_time is None:
            service_selected_time = selected_time

        anchor_time = self._parse_service_time(viewer.get("anchor_time")) or service_selected_time
        for station in station_cards:
            station["data_timestamp"] = station.get("timestamp")

        return {
            "schema_version": "ui_v16_database_integrated_v1",
            "service_name": "UI_V16_DatabaseIntegrated",
            "generated_at": summary_response.get("generated_at") or datetime.now().astimezone().isoformat(),
            "snapshot_seed": seed,
            "source_type": "少榆0617ver_1 dedicated UI Service APIs",
            "update_interval_sec": self.refresh_seconds,
            "viewer_state": {
                "mode": mode,
                "slider_value": slider_value,
                "time_type": viewer.get("time_type") or self._time_type(slider_value),
                "display_label": self._display_label(mode, slider_value),
                "selected_time": service_selected_time.isoformat(),
                "service_display_label": viewer.get("display_label"),
                "data_anchor_time": anchor_time.isoformat(),
            },
            "summary": {
                "total_station_count": total_count,
                "normal_count": normal_count,
                "warning_count": warning_count,
                "predict_risk_count": risk_count,
            },
            "stations": station_cards,
            "integration": {
                "webservices_connected": True,
                "data_received": station_route_ok == len(STATIONS),
                "summary_received": bool(summary_stations),
                "api_mode": self.webservices.source_mode,
                "webservices_url": self.webservices.base_url,
                "database_required": True,
                "database_status": database_status,
                "database_connected": bool(database_status.get("connected")),
                "snapshot_seed": seed,
                "route_status": {
                    "summary": True,
                    "station_detail": station_route_ok == len(STATIONS),
                    "station_detail_ok_count": station_route_ok,
                    "station_detail_expected_count": len(STATIONS),
                    "component_detail": component_route_ok == component_route_expected,
                    "component_detail_ok_count": component_route_ok,
                    "component_detail_expected_count": component_route_expected,
                },
                "station_errors": station_errors,
                "component_errors": component_errors,
                "summary_source": summary_response.get("source"),
                "summary_aggregation": "component_detail_metrics_v20",
            },
        }

    def component_detail(
        self,
        station_id: str,
        component_key: str,
        slider_value: float = 0,
        mode: str = "time",
        snapshot_seed: int | None = None,
    ) -> dict[str, Any]:
        seed = int(snapshot_seed or self.new_snapshot_seed(mode, slider_value))
        response = self._fetch_component_response(
            station_id, component_key, mode, slider_value, seed, use_cache=False
        )
        spec = COMPONENT_BY_KEY[component_key]
        component = self._build_component({}, spec, component_response=response)
        return {
            "station": {
                "id": station_id,
                "name": response.get("station_name") or STATIONS[station_id]["name"],
                "englishName": STATIONS[station_id]["english_name"],
            },
            "component": component,
            "snapshot_seed": seed,
            "detail_function": "POST /api/time-series/ui/component-detail",
            "detail_source": "少榆0617ver_1 Webservices component-detail function",
            "service_api": {
                "called": True,
                "route": "POST /api/time-series/ui/component-detail",
                "output_type": response.get("output_type"),
                "request_id": response.get("request_id"),
                "component_name": response.get("component_name") or spec["service_name"],
                "source": response.get("source"),
            },
        }

    def station_detail(
        self,
        station_id: str,
        slider_value: float = 0,
        mode: str = "time",
        snapshot_seed: int | None = None,
    ) -> dict[str, Any]:
        seed = int(snapshot_seed or self.new_snapshot_seed(mode, slider_value))
        response = self._fetch_station_response(
            station_id, mode, slider_value, seed, use_cache=False
        )
        summary_stub = {"id": station_id, "name": STATIONS[station_id]["name"], "english_name": STATIONS[station_id]["english_name"]}
        component_responses: dict[str, dict[str, Any]] = {}
        for spec in COMPONENTS:
            try:
                component_responses[spec["key"]] = self._fetch_component_response(
                    station_id, spec["key"], mode, slider_value, seed, use_cache=False
                )
            except Exception:
                pass
        station = self._build_station(summary_stub, response, component_responses=component_responses)
        issues = [item for item in station["components"] if item["level"] != "ok"]
        return {
            "station": {
                "id": station["id"],
                "name": station["name"],
                "englishName": station["englishName"],
                "overall": station["overall"],
            },
            "issues": issues,
            "snapshot_seed": seed,
            "detail_function": "POST /api/time-series/ui/station-detail",
            "detail_source": "少榆0617ver_1 Webservices station-detail function",
            "service_api": {
                "called": True,
                "route": "POST /api/time-series/ui/station-detail",
                "output_type": response.get("output_type"),
                "request_id": response.get("request_id"),
                "source": response.get("source"),
            },
        }

    @staticmethod
    def _extract_series_points(response: dict[str, Any], metric: str) -> list[dict[str, Any]]:
        series = response.get("time_series")
        if not isinstance(series, dict):
            data = response.get("data") or {}
            series = data.get("time_series") if isinstance(data, dict) else {}
        if not isinstance(series, dict):
            series = {}
        output: list[dict[str, Any]] = []
        for point in series.get("points") or []:
            if not isinstance(point, dict):
                continue
            value = point.get(metric)
            if value is None and point.get("value") is not None:
                value = point.get("value")
            if value is None:
                continue
            timestamp = point.get("timestamp")
            if not timestamp:
                continue
            output.append({"timestamp": timestamp, "value": value})
        return output

    @staticmethod
    def _moving_average(values: list[float]) -> list[float]:
        if len(values) < 3:
            return values[:]
        result: list[float] = []
        for index in range(len(values)):
            start = max(0, index - 1)
            end = min(len(values), index + 2)
            window = values[start:end]
            result.append(sum(window) / len(window))
        return result

    def _sampled_service_trend(
        self,
        station_id: str,
        component_key: str,
        mode: str,
        selected_slider: float,
        snapshot_seed: int,
        selected_value: float | None,
    ) -> list[dict[str, Any]]:
        """Sample the teammate Service API without inventing or smoothing values.

        0718_v2 changes:
        - BatchMode uses fewer checkpoints to reduce database/API load.
        - Timestamps come from Service API viewer_state, not datetime.now().
        - Missing fields are omitted instead of being replaced with the selected
          card value.
        - No moving-average, vertical shift or neighbour clamping is applied.
        """
        if mode == "batch":
            offsets: list[float] = [-10, -5, 0, 5, 10]
        else:
            offsets = [float(value) for value in range(-6, 5)]
        if float(selected_slider) not in offsets:
            offsets.append(float(selected_slider))
        offsets = sorted(set(offsets))

        points: list[dict[str, Any]] = []
        spec = COMPONENT_BY_KEY[component_key]
        metric = spec["primary_metric"]

        for index, offset in enumerate(offsets):
            point_seed = snapshot_seed if offset == float(selected_slider) else snapshot_seed + 10_000 + index * 137
            try:
                response = self._fetch_component_response(
                    station_id,
                    component_key,
                    mode,
                    offset,
                    point_seed,
                    use_cache=True,
                )
                data = self._component_data_from_response(response)
                raw_value = data.get(metric)
                if raw_value is None:
                    continue
                value = float(raw_value)

                viewer = response.get("viewer_state") or {}
                point_type = viewer.get("time_type") or self._time_type(offset)
                timestamp_raw = viewer.get("future_time") if point_type == "future" else viewer.get("anchor_time")
                timestamp = self._parse_service_time(timestamp_raw)
                if timestamp is None:
                    current_snapshot = response.get("current_snapshot") or {}
                    timestamp = self._parse_service_time(current_snapshot.get("ts"))
                if timestamp is None:
                    continue
            except Exception:
                continue

            digits = 3 if metric in {"filter_diff_pressure_bar", "path_error_mm", "vibration_g"} else 2
            points.append({
                "timestamp": timestamp.isoformat(),
                "value": round(value, digits),
                "raw_service_value": round(value, digits),
                "slider_value": offset,
                "time_type": point_type,
                "selected_snapshot": offset == float(selected_slider),
            })

        return points

    def _threshold_reference(self, metric: str) -> dict[str, Any] | None:
        # Only publish the official threshold file copied from 少榆0617ver_1.
        rule = self.rules.rule(metric)
        if not rule:
            return {
                "source": f"少榆0617ver_1 未提供 {metric} 的正式門檻；圖表只顯示 Service API 數值",
                "normal": None,
                "warning": [],
                "fault": [],
            }
        return {
            "unit": rule.get("unit", ""),
            "normal": rule.get("normal"),
            "warning": rule.get("warning", []),
            "fault": rule.get("fault", []),
            "source": "少榆0617ver_1 webservices/time_series_api/config/rules/sensor_thresholds.json",
        }

    def trend_payload(
        self,
        station_id: str,
        component_key: str,
        slider_value: float = 0,
        mode: str = "time",
        snapshot_seed: int | None = None,
    ) -> dict[str, Any]:
        seed = int(snapshot_seed or self.new_snapshot_seed(mode, slider_value))
        cache_key = (seed, mode, float(slider_value), station_id, component_key)
        with self._lock:
            cached = self._trend_cache.get(cache_key)
        if cached is not None:
            return cached

        spec = COMPONENT_BY_KEY[component_key]
        metric = spec["primary_metric"]
        selected_response = self._fetch_component_response(
            station_id, component_key, mode, slider_value, seed, use_cache=True
        )
        selected_data = self._component_data_from_response(selected_response)
        selected_raw = selected_data.get(metric)
        selected_value = float(selected_raw) if selected_raw is not None else None

        # V24:
        # component-detail 回傳的 time_series 是「該時間點附近的資料視窗」，
        # 不是 Engineer UI 需要的固定軸線「過去 6 小時 → 現在 → 未來 2 小時」。
        # 如果直接使用該 time_series，滑桿選過去或未來時，藍色圈選點會被固定在
        # 視窗內的最新點附近，看起來沒有跟著 slider_value 移動。
        #
        # 這裡改成對少榆的 component-detail function 做多時間點取樣：
        # time mode:  -6, -5, ..., 0, ..., +4
        # batch mode: -10, -8, ..., 0, ..., +10
        # 每一點都仍然呼叫少榆 Service API，不使用前端本機假資料。
        # 如此趨勢圖固定顯示完整時間軸，selected_snapshot 會跟 slider_value 對應。
        selected_viewer = selected_response.get("viewer_state") or {}
        response_time_raw = (
            selected_viewer.get("future_time")
            if (selected_viewer.get("time_type") or self._time_type(slider_value)) == "future"
            else selected_viewer.get("anchor_time")
        )
        selected_time = (
            self._parse_service_time(response_time_raw)
            or self._parse_service_time((selected_response.get("current_snapshot") or {}).get("ts"))
            or self._selected_time(mode, slider_value)
        )
        source_method = "component-detail multi-time sampling"
        points = self._sampled_service_trend(
            station_id,
            component_key,
            mode,
            float(slider_value),
            seed,
            selected_value,
        )
        source_note = (
            "趨勢圖只顯示少榆 component-detail Service API 實際回傳值；"
            "缺少的批次/時間點不補值、不平滑。"
        )

        for point in points:
            state = self.rules.classify(metric, point.get("value")) if self.rules.rule(metric) else "normal"
            point["state"] = state
            point["level"] = self.rules.ui_level(state)

        selected_component = self._build_component({}, spec, component_response=selected_response)
        ui_display_time = selected_time

        result = {
            "station_id": station_id,
            "station_name": selected_response.get("station_name") or STATIONS[station_id]["name"],
            "component_key": component_key,
            "component_name": spec["name"],
            "component_en": spec["en"],
            "service_component_name": spec["service_name"],
            "metric": metric,
            "unit": spec["unit"],
            "value_label": spec["value_label"],
            "anchor_time": selected_time.isoformat(),
            "ui_selected_time": ui_display_time.isoformat(),
            "data_anchor_time": selected_time.isoformat(),
            "past_hours": 6,
            "future_hours": 2,
            "points": points,
            "available": selected_value is not None,
            "message": None if selected_value is not None else f"此時間點／批次尚無 {metric} 資料",
            "threshold_reference": self._threshold_reference(metric),
            "selected_snapshot": {
                "mode": mode,
                "slider_value": slider_value,
                "display_label": self._display_label(mode, slider_value),
                "timestamp": ui_display_time.isoformat(),
                "data_timestamp": selected_time.isoformat(),
                "value": selected_value,
                "available": selected_value is not None,
                "formatted_value": selected_component.get("value") if selected_value is not None else "--",
                "source": "POST /api/time-series/ui/component-detail",
            },
            "source": source_note,
            "service_api": {
                "called": True,
                "route": "POST /api/time-series/ui/component-detail",
                "method": source_method,
                "snapshot_seed": seed,
                "source": selected_response.get("source"),
            },
            "axis_caption": "過去 6 小時　→　現在　→　未來 2 小時" if mode == "time" else "過去批次　→　目前批次　→　未來批次",
        }
        with self._lock:
            self._trend_cache[cache_key] = result
            if len(self._trend_cache) > 200:
                for old_key in list(self._trend_cache)[:80]:
                    self._trend_cache.pop(old_key, None)
        return result
