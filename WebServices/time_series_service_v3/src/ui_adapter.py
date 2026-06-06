from __future__ import annotations

from typing import Any, Dict, List


LINE_ID_TO_UI_ID = {
    "line_1": "M1",
    "line_2": "M2",
    "line_3": "M3",
}


COMPONENT_NAME_ZH = {
    "nozzle": "噴嘴",
    "filter_mesh": "濾網",
    "spray_width": "噴幅",
}


def RoundValue(value: Any, digits: int = 2) -> Any:
    """
    將數值四捨五入，非數值或 None 則原樣回傳。
    """

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(value, digits)

    return value


def BuildBaseRequestFromUiRequest(ui_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    將 UI adapter request 轉成 TimeSeriesService 核心 request。

    UI adapter request 可以比較簡化，但最後仍會轉成核心 service 需要的欄位。
    """

    return {
        "schema_version": ui_request.get("schema_version", "v1.0"),
        "service_name": "TimeSeriesService",
        "request_id": ui_request.get("request_id"),
        "mode": ui_request.get("mode", "time"),
        "window_type": ui_request.get("window_type", "current"),
        "slider_value": ui_request["slider_value"],
        "line_scope": ui_request.get("line_scope", "all"),
        "requested_metrics": ui_request.get(
            "requested_metrics",
            [
                "availability_pct",
                "clog_rate_pct",
                "pressure_bar",
                "flow_rate_ml_min",
                "maintainability_pct",
                "quality_score_pct",
                "risk_text",
                "spray_width_mm",
                "recipe_name",
                "temperature_c",
                "utilization_pct",
                "cycle_time_sec",
            ],
        ),
        "random_seed": ui_request.get("random_seed"),
        "sample_count": ui_request.get("sample_count"),
    }


def RemoveNoneOptionalFields(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    移除值為 None 的 optional 欄位，避免影響 service。
    """

    return {
        key: value
        for key, value in request.items()
        if value is not None
    }


def BuildUiStationCard(station: Dict[str, Any]) -> Dict[str, Any]:
    """
    將核心 station output 轉成 UI 初始化畫面需要的卡片格式。
    """

    metrics = station.get("metrics", {})
    process = station.get("process_parameters", {})
    spray_width_image = station.get("spray_width_image", {})

    line_id = station.get("line_id")

    return {
        "id": LINE_ID_TO_UI_ID.get(line_id, line_id),
        "line_id": line_id,
        "name": station.get("station_name_zh"),
        "english_name": station.get("station_name_en"),

        "recipe": process.get("recipe_name"),
        "pressure_bar": RoundValue(metrics.get("pressure_bar")),
        "flow_rate_ml_min": RoundValue(metrics.get("flow_rate_ml_min")),
        "spray_width_mm": RoundValue(metrics.get("spray_width_mm")),
        "target_min_mm": spray_width_image.get("target_min_mm"),
        "target_max_mm": spray_width_image.get("target_max_mm"),
        "temperature_c": RoundValue(process.get("temperature_c")),

        "availability_pct": RoundValue(metrics.get("availability_pct")),
        "maintainability_pct": RoundValue(metrics.get("maintainability_pct")),
        "clog_rate_pct": RoundValue(metrics.get("clog_rate_pct")),
        "quality_score_pct": RoundValue(metrics.get("quality_score_pct")),
        "utilization_pct": RoundValue(process.get("utilization_pct")),
        "cycle_time_sec": RoundValue(process.get("cycle_time_sec")),

        # Rule Service 之後補
        "state": station.get("state"),
        "risk_text": metrics.get("risk_text"),
    }


def BuildUiSummaryOutput(core_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    建立 UI 初始化畫面 output。

    用途：
    - 首頁 dashboard
    - station cards
    - summary numbers
    """

    return {
        "schema_version": core_output.get("schema_version"),
        "service_name": "TimeSeriesService",
        "output_type": "ui_summary",
        "generated_at": core_output.get("generated_at"),
        "request_id": core_output.get("request_id"),
        "viewer_state": core_output.get("viewer_state", {}),
        "summary": core_output.get("summary", {}),
        "stations": [
            BuildUiStationCard(station)
            for station in core_output.get("stations", [])
        ],
        "source": {
            "core_endpoint": "POST /api/time-series",
            "adapter_endpoint": "POST /api/time-series/ui/summary",
        },
    }


def FindStation(core_output: Dict[str, Any], line_id: str) -> Dict[str, Any] | None:
    """
    從 core output 找指定 line_id 的 station。
    """

    for station in core_output.get("stations", []):
        if station.get("line_id") == line_id:
            return station

    return None


def BuildUiStationDetailOutput(core_output: Dict[str, Any], line_id: str) -> Dict[str, Any]:
    """
    建立 UI station detail output。
    """

    station = FindStation(core_output, line_id)

    if station is None:
        raise ValueError(f"line_id not found: {line_id}")

    return {
        "schema_version": core_output.get("schema_version"),
        "service_name": "TimeSeriesService",
        "output_type": "ui_station_detail",
        "generated_at": core_output.get("generated_at"),
        "request_id": core_output.get("request_id"),
        "viewer_state": core_output.get("viewer_state", {}),
        "line_id": station.get("line_id"),
        "ui_id": LINE_ID_TO_UI_ID.get(station.get("line_id"), station.get("line_id")),
        "name": station.get("station_name_zh"),
        "english_name": station.get("station_name_en"),
        "state": station.get("state"),
        "risk_text": station.get("metrics", {}).get("risk_text"),
        "metrics": station.get("metrics", {}),
        "process_parameters": station.get("process_parameters", {}),
        "component_metrics": station.get("component_metrics", {}),
        "spray_width_image": station.get("spray_width_image", {}),
        "fault_detail": station.get("fault_detail", []),
        "component_overview": station.get("component_overview", []),
        "source": {
            "core_endpoint": "POST /api/time-series",
            "adapter_endpoint": "POST /api/time-series/ui/station-detail",
        },
    }


def BuildUiComponentDetailOutput(
    core_output: Dict[str, Any],
    line_id: str,
    component_name: str
) -> Dict[str, Any]:
    """
    建立 UI component detail output。
    """

    station = FindStation(core_output, line_id)

    if station is None:
        raise ValueError(f"line_id not found: {line_id}")

    component_metrics = station.get("component_metrics", {})

    if component_name not in component_metrics:
        raise ValueError(f"component_name not found: {component_name}")

    return {
        "schema_version": core_output.get("schema_version"),
        "service_name": "TimeSeriesService",
        "output_type": "ui_component_detail",
        "generated_at": core_output.get("generated_at"),
        "request_id": core_output.get("request_id"),
        "viewer_state": core_output.get("viewer_state", {}),
        "line_id": station.get("line_id"),
        "ui_id": LINE_ID_TO_UI_ID.get(station.get("line_id"), station.get("line_id")),
        "station_name": station.get("station_name_zh"),
        "component_name": component_name,
        "component_name_zh": COMPONENT_NAME_ZH.get(component_name, component_name),
        "data": component_metrics.get(component_name, {}),
        "source": {
            "core_endpoint": "POST /api/time-series",
            "adapter_endpoint": "POST /api/time-series/ui/component-detail",
        },
    }
