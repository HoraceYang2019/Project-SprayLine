"""Past / Current / Future integrated service for SprayLine.

此檔案的定位
-----------
這支 service 用來把 past / current 的 time-series 資料入口，
接到少榆端既有的 Future / Monitoring / Alert / DB 回寫流程。

重要原則
--------
1. past / current 資料來源仍走正式 Database/versionB sensor_1min / sensor_3min。
2. future prediction、alert_event、batch_station_status 的回寫仍走 Database/versionB。
3. 不改成 WebServices/time_series_service_B 的 runtime JSON persistence。
4. 不開 FastAPI / HTTP endpoint；本檔先提供 Python service function。
5. UI 需要的 time-series format 由 build_ui_time_series_response() 統一輸出。

時間軸概念
----------
slider_value < 0  -> past
slider_value == 0 -> current
slider_value > 0  -> future

past:
    以 now - abs(slider_value) 分鐘作為 anchor_time，
    回查 anchor_time 前 window_minutes 的資料。

current:
    以 now 作為 anchor_time，
    回查最近 window_minutes 的資料，並產生 current_snapshot。

future:
    以 current window 作為 model input，
    產生 prediction_time = now + slider_value 分鐘的 future payload。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from integration_adapter.database_versionb_adapter import (
    get_connection,
    query_sensor_1min,
    query_sensor_3min,
    get_latest_sensor_1min,
)
from future_service.future_service import (
    build_future_prediction_payload,
    save_future_prediction_result,
)
from monitoring_worker.monitoring_worker import run_monitoring_once


STATION_INFO = {
    "Station_1": {
        "line_id": "line_1",
        "station_name_zh": "底漆站",
        "station_name_en": "Primer Station",
        "ui_id": "M1",
    },
    "Station_2": {
        "line_id": "line_2",
        "station_name_zh": "面漆站",
        "station_name_en": "Topcoat Station",
        "ui_id": "M2",
    },
    "Station_3": {
        "line_id": "line_3",
        "station_name_zh": "金漆站",
        "station_name_en": "Gold Paint Station",
        "ui_id": "M3",
    },
}


DEFAULT_REQUESTED_METRICS = [
    "film_thickness_um",
    "paint_flow_ml_min",
    "air_pressure_bar",
    "spray_width_mm",
    "filter_diff_pressure_bar",
    "servo_torque_load_pct",
    "path_error_mm",
    "vibration_g",
    "temperature_c",
    "humidity_rh",
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return value


def _to_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(values: Iterable[Any]) -> Optional[float]:
    nums = [_to_float(v) for v in values]
    nums = [v for v in nums if v is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


@dataclass
class TimeWindow:
    time_type: str
    slider_value: float
    anchor_time: datetime
    window_start: datetime
    window_end: datetime
    future_time: Optional[datetime]
    sample_method: str


class IntegratedSprayLineService:
    """整合 past / current / future 的 service layer.

    這個 class 不取代 Database/versionB，也不取代 time_series_service_B。
    它把 UI 需要的 time-series output 與少榆端 DB 回寫流程接在一起。
    """

    def __init__(self, conn=None):
        self.conn = conn

    # ------------------------------------------------------------------
    # 1. Time slider / window
    # ------------------------------------------------------------------
    def determine_time_type(self, slider_value: float) -> str:
        if slider_value < 0:
            return "past"
        if slider_value == 0:
            return "current"
        return "future"

    def get_sample_method_name(self, time_type: str) -> str:
        if time_type == "past":
            return "mean"
        if time_type == "current":
            return "recent_average"
        if time_type == "future":
            return "latest_valid"
        raise ValueError(f"unsupported time_type: {time_type}")

    def build_time_window(
        self,
        slider_value: float,
        window_minutes: int = 30,
        now: Optional[datetime] = None,
    ) -> TimeWindow:
        now = now or _utc_now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        time_type = self.determine_time_type(slider_value)

        if time_type == "past":
            anchor = now - timedelta(minutes=abs(slider_value))
            start = anchor - timedelta(minutes=window_minutes)
            end = anchor
            future_time = None
        elif time_type == "current":
            anchor = now
            start = now - timedelta(minutes=window_minutes)
            end = now
            future_time = None
        else:
            anchor = now
            start = now - timedelta(minutes=window_minutes)
            end = now
            future_time = now + timedelta(minutes=slider_value)

        return TimeWindow(
            time_type=time_type,
            slider_value=slider_value,
            anchor_time=anchor,
            window_start=start,
            window_end=end,
            future_time=future_time,
            sample_method=self.get_sample_method_name(time_type),
        )

    def resolve_data_anchor_now(self, conn, station_ids: List[str]) -> datetime:
        """以資料庫中最新一筆 sensor_1min 的時間作為 anchor "now"。

        dataprocess 產生器跑在自己的虛擬時間軸上（會持續往未來推進，
        與真實時鐘脫鉤），若用 datetime.now() 當 anchor，past/current/future
        查詢永遠對不到任何資料。改用「資料庫目前最新時間」當作 anchor，
        Manager/Engineer UI 的 current 視圖才能反映 dataprocess 實際寫入的資料。
        """
        latest_ts: Optional[datetime] = None
        for station_id in station_ids:
            try:
                row = get_latest_sensor_1min(conn, station_id)
            except Exception:
                row = None
            ts = row.get("ts") if row else None
            if ts is not None and (latest_ts is None or ts > latest_ts):
                latest_ts = ts

        if latest_ts is None:
            return _utc_now()
        if latest_ts.tzinfo is None:
            latest_ts = latest_ts.replace(tzinfo=timezone.utc)
        return latest_ts

    def build_viewer_state(self, request: Dict[str, Any], window: TimeWindow) -> Dict[str, Any]:
        return {
            "mode": request.get("mode", "time"),
            "window_type": request.get("window_type", window.time_type),
            "slider_value": window.slider_value,
            "time_type": window.time_type,
            "display_label": (
                "current"
                if window.time_type == "current"
                else f"{window.time_type} {abs(window.slider_value)} min"
            ),
            "sample_method": window.sample_method,
            "is_history": window.time_type == "past",
            "is_current": window.time_type == "current",
            "is_future": window.time_type == "future",
            "anchor_time": _iso(window.anchor_time),
            "window_start": _iso(window.window_start),
            "window_end": _iso(window.window_end),
            "future_time": _iso(window.future_time),
        }

    # ------------------------------------------------------------------
    # 2. Past / current data retrieval from Database/versionB
    # ------------------------------------------------------------------
    def fetch_sensor_window(
        self,
        conn,
        station_id: str,
        window: TimeWindow,
        granularity: str = "1min",
    ) -> List[Dict[str, Any]]:
        if granularity == "1min":
            return query_sensor_1min(conn, station_id, window.window_start, window.window_end)
        if granularity == "3min":
            return query_sensor_3min(conn, station_id, window.window_start, window.window_end)
        raise ValueError("granularity must be '1min' or '3min'")

    def build_current_snapshot(
        self,
        rows_1min: List[Dict[str, Any]],
        rows_3min: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        latest_1min = rows_1min[-1] if rows_1min else {}
        latest_3min = rows_3min[-1] if rows_3min else {}

        snapshot = dict(latest_1min)
        # 3min 主要提供環境與減速機溫度，避免覆蓋 batch_id/station_id 等主欄位。
        for key in ("gearbox_temperature_c", "temperature_c", "humidity_rh"):
            if latest_3min.get(key) is not None:
                snapshot[key] = latest_3min.get(key)

        return self.normalize_row(snapshot)

    def normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {}
        for key, value in row.items():
            normalized[key] = _iso(value)
        return normalized

    def build_ui_series_points(
        self,
        rows: List[Dict[str, Any]],
        requested_metrics: List[str],
    ) -> List[Dict[str, Any]]:
        points = []
        for row in rows:
            point = {
                "timestamp": _iso(row.get("ts")),
                "batch_id": row.get("batch_id"),
                "station_id": row.get("station_id"),
                "data_quality_flag": row.get("data_quality_flag"),
            }
            for metric in requested_metrics:
                if metric in row:
                    point[metric] = row.get(metric)
            points.append(point)
        return points

    def build_window_summary(
        self,
        rows: List[Dict[str, Any]],
        requested_metrics: List[str],
    ) -> Dict[str, Any]:
        summary = {"point_count": len(rows)}
        for metric in requested_metrics:
            values = [row.get(metric) for row in rows]
            avg = _mean(values)
            if avg is not None:
                summary[f"avg_{metric}"] = round(avg, 4)
        return summary

    # ------------------------------------------------------------------
    # 3. Future prediction from current snapshot
    # ------------------------------------------------------------------
    def estimate_future_from_snapshot(
        self,
        snapshot: Dict[str, Any],
        station_id: str,
        prediction_time: str,
    ) -> Dict[str, Any]:
        """建立一個可測試用的 future payload。

        這裡是整合 service 的示範預測規則，用於串接 DB 回寫與 UI 顯示。
        正式模型可日後替換，但 payload 欄位已對齊 Database/versionB。
        """
        film = _to_float(snapshot.get("film_thickness_um"))
        width = _to_float(snapshot.get("spray_width_mm"))
        pressure = _to_float(snapshot.get("air_pressure_bar"))

        score = 100.0
        if film is not None:
            score -= min(35.0, abs(film - 15.0) * 2.0)
        if width is not None:
            score -= min(35.0, abs(width - 52.0) * 1.2)
        if pressure is not None:
            score -= min(25.0, abs(pressure - 2.5) * 12.0)

        quality_score = round(max(0.0, min(100.0, score)), 2)
        predicted_ok_rate = quality_score
        predicted_ng_count = int(round(max(0.0, 100.0 - quality_score) / 2.5))

        batch_id = snapshot.get("batch_id") or "BATCH_UNKNOWN"

        return build_future_prediction_payload(
            batch_id=batch_id,
            station_id=station_id,
            prediction_time=prediction_time,
            predicted_ok_rate=predicted_ok_rate,
            predicted_ng_count=predicted_ng_count,
            quality_score=quality_score,
            model_input_source="IntegratedSprayLineService:past_current_window",
        )

    # ------------------------------------------------------------------
    # 4. UI response format
    # ------------------------------------------------------------------
    def build_station_output(
        self,
        conn,
        station_id: str,
        window: TimeWindow,
        requested_metrics: List[str],
    ) -> Dict[str, Any]:
        rows_1min = self.fetch_sensor_window(conn, station_id, window, granularity="1min")
        rows_3min = self.fetch_sensor_window(conn, station_id, window, granularity="3min")
        snapshot = self.build_current_snapshot(rows_1min, rows_3min)

        station_info = STATION_INFO.get(station_id, {
            "line_id": station_id,
            "station_name_zh": station_id,
            "station_name_en": station_id,
            "ui_id": station_id,
        })

        output = {
            "station_id": station_id,
            **station_info,
            "time_series": {
                "granularity": "1min",
                "point_count": len(rows_1min),
                "points": self.build_ui_series_points(rows_1min, requested_metrics),
            },
            "past_window": {
                "window_start": _iso(window.window_start),
                "window_end": _iso(window.window_end),
                "summary": self.build_window_summary(rows_1min, requested_metrics),
            },
            "current_snapshot": snapshot,
            "environment_snapshot": self.normalize_row(rows_3min[-1]) if rows_3min else {},
        }

        if window.time_type == "future" and window.future_time is not None:
            output["future_prediction_payload"] = self.estimate_future_from_snapshot(
                snapshot=snapshot,
                station_id=station_id,
                prediction_time=_iso(window.future_time),
            )

        return output

    def build_ui_time_series_response(self, conn, request: Dict[str, Any]) -> Dict[str, Any]:
        slider_value = float(request.get("slider_value", 0))
        window_minutes = int(request.get("window_minutes", request.get("past_window_minutes", 30)))
        requested_metrics = request.get("requested_metrics") or DEFAULT_REQUESTED_METRICS
        station_scope = request.get("station_scope", request.get("stations", ["Station_1"]))

        if station_scope == "all":
            station_ids = list(STATION_INFO.keys())
        elif isinstance(station_scope, str):
            station_ids = [station_scope]
        else:
            station_ids = list(station_scope)

        anchor_now = self.resolve_data_anchor_now(conn, station_ids)
        window = self.build_time_window(slider_value=slider_value, window_minutes=window_minutes, now=anchor_now)

        stations = [
            self.build_station_output(conn, station_id, window, requested_metrics)
            for station_id in station_ids
        ]

        return {
            "schema_version": request.get("schema_version", "v1.0"),
            "service_name": "IntegratedSprayLineService",
            "output_type": "ui_time_series",
            "generated_at": _iso(_utc_now()),
            "request_id": request.get("request_id"),
            "viewer_state": self.build_viewer_state(request, window),
            "stations": stations,
            "source": {
                "past_current_data": "Database/versionB sensor_1min / sensor_3min",
                "future_prediction": "webservices.future_service + Database/versionB db_future",
                "alert_and_status": "webservices.monitoring_worker + Database/versionB db_alert/db_status",
                "http_endpoint_used": False,
                "runtime_json_used_as_persistence": False,
            },
        }

    # ------------------------------------------------------------------
    # 5. Optional DB write-back
    # ------------------------------------------------------------------
    def run_integrated_once(
        self,
        conn,
        request: Dict[str, Any],
        write_back: bool = False,
        commit: bool = True,
    ) -> Dict[str, Any]:
        response = self.build_ui_time_series_response(conn, request)

        if not write_back:
            response["write_back"] = {
                "enabled": False,
                "note": "UI time-series query only; no DB write-back executed.",
            }
            return response

        write_results = []

        # current/past：可選擇觸發 MonitoringWorker，產生 alert_event / batch_station_status。
        for station in response.get("stations", []):
            station_id = station.get("station_id")
            monitor_result = run_monitoring_once(
                station=station_id,
                lookback_minutes=int(request.get("window_minutes", 30)),
            )
            write_results.append({
                "type": "monitoring_alert_status",
                "station_id": station_id,
                "result": monitor_result,
            })

            # future：如果 response 中有 future_prediction_payload，就寫回 future_prediction_result。
            future_payload = station.get("future_prediction_payload")
            if future_payload:
                prediction_id = save_future_prediction_result(conn, future_payload, commit=False)
                write_results.append({
                    "type": "future_prediction_result",
                    "station_id": station_id,
                    "prediction_id": prediction_id,
                })

        if commit:
            conn.commit()

        response["write_back"] = {
            "enabled": True,
            "results": write_results,
        }
        return response


def build_demo_request(slider_value: float = 0) -> Dict[str, Any]:
    return {
        "schema_version": "v1.0",
        "service_name": "IntegratedSprayLineService",
        "request_id": "REQ_SHAOYU_PC_DEMO",
        "mode": "time",
        "window_type": "time_slider",
        "slider_value": slider_value,
        "window_minutes": 30,
        "station_scope": ["Station_1"],
        "requested_metrics": DEFAULT_REQUESTED_METRICS,
    }


def run_integrated_once(request: Optional[Dict[str, Any]] = None, write_back: bool = False) -> Dict[str, Any]:
    request = request or build_demo_request(slider_value=0)
    conn = get_connection()
    try:
        service = IntegratedSprayLineService(conn=conn)
        return service.run_integrated_once(conn, request, write_back=write_back)
    finally:
        conn.close()


if __name__ == "__main__":
    import json

    # 預設只做 UI time-series read，不寫 DB。
    demo_request = build_demo_request(slider_value=0)
    result = run_integrated_once(demo_request, write_back=False)
    print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
