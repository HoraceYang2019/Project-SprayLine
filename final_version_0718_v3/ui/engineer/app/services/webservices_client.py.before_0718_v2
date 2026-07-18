from __future__ import annotations

import json
import os
from datetime import datetime
from time import monotonic
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class WebservicesRequestError(RuntimeError):
    """Raised when the Shaoyu0617 Webservices request cannot be completed."""


class WebservicesClient:
    """HTTP client for Summary, Station, Component and database-status APIs."""

    def __init__(self) -> None:
        self.base_url = os.getenv("WEBSERVICES_URL", "http://127.0.0.1:8001").rstrip("/")
        self.timeout = float(os.getenv("WEBSERVICES_TIMEOUT_SEC", "20"))
        self.source_mode = os.getenv("WEBSERVICES_SOURCE_MODE", "integrated").strip().lower() or "integrated"
        if self.source_mode not in {"demo", "auto", "integrated"}:
            self.source_mode = "integrated"
        self._db_cache: tuple[float, dict[str, Any]] | None = None

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        request = Request(f"{self.base_url}{path}", data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                if not isinstance(result, dict):
                    raise WebservicesRequestError(f"{path} did not return a JSON object")
                return result
        except HTTPError as exc:
            try:
                response_text = exc.read().decode("utf-8", errors="replace")
            except Exception:
                response_text = ""
            raise WebservicesRequestError(
                f"{method} {path} failed: HTTP {exc.code}; {response_text[:800]}"
            ) from exc
        except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            raise WebservicesRequestError(f"{method} {path} failed: {exc}") from exc

    @staticmethod
    def _window_type(mode: str, slider_value: float) -> str:
        if mode == "batch":
            return "batch_slider"
        return "current" if float(slider_value) == 0 else "time_slider"

    @staticmethod
    def _service_slider_value(mode: str, slider_value: float) -> float:
        """Keep the engineer UI slider value unchanged for Shaoyu API.

        V19 converted hours into minutes, but the 0620 Shaoyu API hotfix already
        interprets slider_value as its own time/batch index. Sending -180 for
        「過去3小時」 made the API jump outside the intended window, so station
        cards had no data and stayed green. V20 keeps the UI value as-is:
        - -3 means the UI-selected past third point
        -  0 means current
        - +4 means the UI-selected future fourth point
        """
        return float(slider_value)

    def _common_payload(self, *, mode: str, slider_value: float, random_seed: int, request_id: str) -> dict[str, Any]:
        ui_slider_value = float(slider_value)
        service_slider_value = self._service_slider_value(mode, ui_slider_value)
        return {
            "schema_version": "v1.0",
            "request_id": request_id,
            "mode": mode,
            "window_type": self._window_type(mode, ui_slider_value),
            "slider_value": service_slider_value,
            "ui_slider_value": ui_slider_value,
            "ui_slider_unit": "raw_ui_time_index" if mode != "batch" else "batch_index",
            "source_mode": self.source_mode,
            "random_seed": int(random_seed),
        }

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/api/health")

    def database_status(self, *, force: bool = False) -> dict[str, Any]:
        now = monotonic()
        if not force and self._db_cache and now - self._db_cache[0] < 5:
            return self._db_cache[1]
        result = self._request("GET", "/api/database/status")
        self._db_cache = (now, result)
        return result

    def fetch_summary(self, *, mode: str, slider_value: float, random_seed: int) -> dict[str, Any]:
        payload = self._common_payload(mode=mode, slider_value=slider_value, random_seed=random_seed,
                                       request_id=f"ui_v16_summary_{random_seed}")
        payload["line_scope"] = "all"
        return self._request("POST", "/api/time-series/ui/summary", payload)

    def fetch_station_detail(self, *, line_id: str, mode: str, slider_value: float, random_seed: int) -> dict[str, Any]:
        payload = self._common_payload(mode=mode, slider_value=slider_value, random_seed=random_seed,
                                       request_id=f"ui_v16_station_{line_id}_{random_seed}")
        payload["line_id"] = line_id
        return self._request("POST", "/api/time-series/ui/station-detail", payload)

    def fetch_component_detail(self, *, line_id: str, component_name: str, mode: str,
                               slider_value: float, random_seed: int) -> dict[str, Any]:
        payload = self._common_payload(mode=mode, slider_value=slider_value, random_seed=random_seed,
                                       request_id=f"ui_v16_component_{line_id}_{component_name}_{random_seed}")
        payload.update({"line_id": line_id, "component_name": component_name})
        return self._request("POST", "/api/time-series/ui/component-detail", payload)

    def status(self) -> dict[str, Any]:
        checked_at = datetime.now().astimezone().isoformat()
        route_status: dict[str, dict[str, Any]] = {}
        try:
            health = self.health()
        except WebservicesRequestError as exc:
            return {
                "webservices_connected": False, "database_connected": False, "data_received": False,
                "mode": "offline", "label": "Webservices 未連線",
                "detail": "UI 無法連到 Service API。", "error": str(exc),
                "base_url": self.base_url, "checked_at": checked_at, "route_status": route_status,
            }

        try:
            db_status = self.database_status(force=True)
        except WebservicesRequestError as exc:
            db_status = {"connected": False, "error_message": str(exc)}

        if not db_status.get("connected"):
            return {
                "webservices_connected": True, "database_connected": False, "data_received": False,
                "mode": self.source_mode, "label": "Webservices 已連線，但資料庫未連線",
                "detail": db_status.get("error_message") or "PostgreSQL 連線檢查失敗。",
                "base_url": self.base_url, "checked_at": checked_at, "health": health,
                "database_status": db_status, "route_status": route_status,
            }

        seed = 91234
        try:
            summary = self.fetch_summary(mode="time", slider_value=0, random_seed=seed)
            count = len(summary.get("stations", []) or [])
            route_status["summary"] = {"ok": summary.get("output_type") == "ui_summary" and count == 3,
                                       "route": "POST /api/time-series/ui/summary", "station_count": count}
        except WebservicesRequestError as exc:
            route_status["summary"] = {"ok": False, "route": "POST /api/time-series/ui/summary", "error": str(exc)}
        try:
            station = self.fetch_station_detail(line_id="line_1", mode="time", slider_value=0, random_seed=seed)
            route_status["station_detail"] = {"ok": station.get("output_type") == "ui_station_detail",
                                              "route": "POST /api/time-series/ui/station-detail"}
        except WebservicesRequestError as exc:
            route_status["station_detail"] = {"ok": False, "route": "POST /api/time-series/ui/station-detail", "error": str(exc)}
        try:
            component = self.fetch_component_detail(line_id="line_1", component_name="nozzle",
                                                      mode="time", slider_value=0, random_seed=seed)
            route_status["component_detail"] = {"ok": component.get("output_type") == "ui_component_detail",
                                                "route": "POST /api/time-series/ui/component-detail"}
        except WebservicesRequestError as exc:
            route_status["component_detail"] = {"ok": False, "route": "POST /api/time-series/ui/component-detail", "error": str(exc)}

        all_ok = len(route_status) == 3 and all(item.get("ok") for item in route_status.values())
        ok_count = sum(1 for item in route_status.values() if item.get("ok"))
        db_name = (db_status.get("database") or {}).get("name", "-")
        return {
            "webservices_connected": True, "database_connected": True, "data_received": all_ok,
            "mode": self.source_mode,
            "label": "Webservices 與資料庫皆已連線" if all_ok else "資料庫已連線，但部分 Service API 異常",
            "detail": f"PostgreSQL：{db_name}；已通過 {ok_count}/3 個 UI Service API。",
            "base_url": self.base_url, "checked_at": checked_at, "health": health,
            "database_status": db_status, "route_status": route_status,
        }
