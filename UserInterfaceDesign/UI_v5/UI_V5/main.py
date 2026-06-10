# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import sys
import math
import time
import json
import sqlite3
import copy
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

app = FastAPI(title="Spraying Line Monitoring System")

BASE_DIR = Path(__file__).resolve().parent
HTML_FILE = BASE_DIR / "spraying_dashboard_updated.html"
DIAGNOSIS_RULE_FILE = BASE_DIR / "diagnosis_rules.json"
DIAGNOSIS_DB_FILE = BASE_DIR / "diagnosis_rules.db"

NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def FindServiceRoot() -> Optional[Path]:
    candidates = [
        BASE_DIR / "time_series_service_v3",
        BASE_DIR.parent / "time_series_service_v3",
        Path.cwd() / "time_series_service_v3",
        Path.cwd().parent / "time_series_service_v3",
    ]
    for candidate in candidates:
        service_src = candidate / "src"
        if (service_src / "time_series_service.py").exists() and (service_src / "ui_adapter.py").exists():
            return candidate.resolve()
    return None


SERVICE_ROOT = FindServiceRoot()
SERVICE_SRC = SERVICE_ROOT / "src" if SERVICE_ROOT else None
SERVICE_EXAMPLES = SERVICE_ROOT / "examples" if SERVICE_ROOT else None
PROCESSED_DB = SERVICE_EXAMPLES / "processed_result_database_demo.json" if SERVICE_EXAMPLES else None

if SERVICE_SRC and SERVICE_SRC.exists():
    sys.path.insert(0, str(SERVICE_SRC))

try:
    if SERVICE_ROOT is None:
        raise FileNotFoundError("找不到 time_series_service_v3，將使用備援動態資料。")
    from time_series_service import TimeSeriesService
    from ui_adapter import BuildUiSummaryOutput, BuildUiStationDetailOutput, BuildUiComponentDetailOutput
    service = TimeSeriesService(processed_result_db_path=PROCESSED_DB)
    SERVICE_AVAILABLE = True
    SERVICE_ERROR = None
except Exception as exc:
    service = None
    BuildUiSummaryOutput = None
    SERVICE_AVAILABLE = False
    SERVICE_ERROR = repr(exc)


def IsNumber(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def RoundValue(value: Any, digits: int = 2) -> Any:
    if IsNumber(value):
        return round(value, digits)
    return value


def FormatValue(value: Any, digits: int = 1, unit: str = "") -> str:
    if not IsNumber(value):
        return f"--{unit}"
    rounded = round(value, digits)
    if float(rounded).is_integer():
        return f"{int(rounded)}{unit}"
    return f"{rounded:.{digits}f}{unit}"


def RemoveSpaces(value: Any) -> str:
    return str(value or "").replace(" ", "")


def LevelText(level: str) -> str:
    return {"ok": "正常", "warn": "注意", "bad": "異常"}.get(level, "監控")


def PercentLevel(value: Any, warn: float = 80, bad: float = 60) -> str:
    if not IsNumber(value):
        return "warn"
    if value < bad:
        return "bad"
    if value < warn:
        return "warn"
    return "ok"


def ClogLevel(value: Any) -> str:
    if not IsNumber(value):
        return "warn"
    if value >= 60:
        return "bad"
    if value >= 30:
        return "warn"
    return "ok"


def PressureLevel(value: Any) -> str:
    if not IsNumber(value):
        return "warn"
    if value < 1.5:
        return "bad"
    if value < 2.0:
        return "warn"
    return "ok"


def SprayWidthLevel(width: Any, target_min: Any, target_max: Any) -> str:
    if not IsNumber(width) or not IsNumber(target_min) or not IsNumber(target_max):
        return "warn"
    # 目標範圍外超過 2mm 視為異常；剛超出目標範圍視為注意。
    if width < target_min - 2 or width > target_max + 2:
        return "bad"
    if width < target_min or width > target_max:
        return "warn"
    return "ok"


def DirectionLowOk(value: Any, level: str) -> str:
    return "ok" if level == "ok" else "low"


def DirectionHighOk(value: Any, level: str) -> str:
    return "ok" if level == "ok" else "high"


def DirectionSprayWidth(width: Any, target_min: Any, target_max: Any, level: str) -> str:
    if level == "ok":
        return "ok"
    if IsNumber(width) and IsNumber(target_min) and width < target_min:
        return "low"
    if IsNumber(width) and IsNumber(target_max) and width > target_max:
        return "high"
    return "unknown"


def EnsureDiagnosisDatabase() -> None:
    """建立診斷規則資料庫。正式版可把這裡改成連 MySQL / MSSQL。"""
    if DIAGNOSIS_DB_FILE.exists():
        return

    rules = []
    if DIAGNOSIS_RULE_FILE.exists():
        try:
            data = json.loads(DIAGNOSIS_RULE_FILE.read_text(encoding="utf-8"))
            rules = data.get("rules", [])
        except Exception:
            rules = []

    conn = sqlite3.connect(DIAGNOSIS_DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS diagnosis_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                component TEXT NOT NULL,
                level TEXT NOT NULL,
                direction TEXT NOT NULL DEFAULT 'any',
                issue TEXT NOT NULL,
                reason TEXT NOT NULL,
                solution TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_diagnosis_lookup ON diagnosis_rules(component, level, direction, enabled)")
        if rules:
            cur.executemany(
                """
                INSERT INTO diagnosis_rules(component, level, direction, issue, reason, solution, enabled)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                [
                    (
                        rule.get("component", ""),
                        rule.get("level", ""),
                        rule.get("direction", "any") or "any",
                        rule.get("issue", ""),
                        rule.get("reason", ""),
                        rule.get("solution", ""),
                    )
                    for rule in rules
                ],
            )
        conn.commit()
    finally:
        conn.close()


def LoadDiagnosisRules() -> List[Dict[str, Any]]:
    """從 SQLite 資料庫讀取診斷規則，不再從前端或 JS 寫死。"""
    try:
        EnsureDiagnosisDatabase()
        conn = sqlite3.connect(DIAGNOSIS_DB_FILE)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT id, component, level, direction, issue, reason, solution
                FROM diagnosis_rules
                WHERE enabled = 1
                ORDER BY id
                """
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    except Exception:
        return []


def CountDiagnosisRules() -> int:
    try:
        EnsureDiagnosisDatabase()
        conn = sqlite3.connect(DIAGNOSIS_DB_FILE)
        try:
            row = conn.execute("SELECT COUNT(*) FROM diagnosis_rules WHERE enabled = 1").fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()
    except Exception:
        return 0


def SafeFormat(text: Any, context: Dict[str, Any]) -> str:
    try:
        return str(text).format(**context)
    except Exception:
        return str(text)


def LookupDiagnosis(component: str, level: str, direction: str, context: Dict[str, Any]) -> Dict[str, str]:
    rules = LoadDiagnosisRules()
    candidates = []
    for rule in rules:
        if rule.get("component") != component:
            continue
        if rule.get("level") != level:
            continue
        rule_direction = rule.get("direction")
        score = 0
        if rule_direction == direction:
            score = 3
        elif rule_direction in (None, "", "any"):
            score = 2
        elif direction == "unknown":
            score = 1
        if score:
            candidates.append((score, rule))
    if candidates:
        rule = sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]
        return {
            "issue": SafeFormat(rule.get("issue", "資料庫尚未設定問題說明。"), context),
            "reason": SafeFormat(rule.get("reason", "資料庫尚未設定可能原因。"), context),
            "solution": SafeFormat(rule.get("solution", "資料庫尚未設定處理建議。"), context),
            "diagnosis_source": "diagnosis_rules.db",
        }
    return {
        "issue": "診斷規則資料庫尚未設定此狀態的問題說明。",
        "reason": "請確認 diagnosis_rules.json 是否有對應的 component、level 與 direction。",
        "solution": "新增或修正 diagnosis_rules.json 後，前端下次 15 秒更新即會套用。",
        "diagnosis_source": "missing_rule",
    }


def Component(key: str, icon: str, name: str, en: str, level: str, value: str, diagnosis: Dict[str, str]) -> Dict[str, Any]:
    return {
        "key": key,
        "icon": icon,
        "name": name,
        "en": en,
        "level": level,
        "status_text": LevelText(level),
        "value": value,
        "issue": diagnosis["issue"],
        "reason": diagnosis["reason"],
        "solution": diagnosis["solution"],
        "diagnosis_source": diagnosis.get("diagnosis_source"),
    }


def BuildComponents(station: Dict[str, Any]) -> List[Dict[str, Any]]:
    availability = station.get("availability_pct")
    clog = station.get("clog_rate_pct")
    pressure = station.get("pressure_bar")
    width = station.get("spray_width_mm")
    target_min = station.get("target_min_mm")
    target_max = station.get("target_max_mm")
    maintainability = station.get("maintainability_pct")
    quality = station.get("quality_score_pct")

    common = {
        "stationName": station.get("name"),
        "targetMin": target_min if IsNumber(target_min) else 0,
        "targetMax": target_max if IsNumber(target_max) else 0,
        "sprayWidth": width if IsNumber(width) else 0,
        "pressure": pressure if IsNumber(pressure) else 0,
        "clog": clog if IsNumber(clog) else 0,
        "availability": availability if IsNumber(availability) else 0,
        "maintainability": maintainability if IsNumber(maintainability) else 0,
        "quality": quality if IsNumber(quality) else 0,
    }

    arm_level = PercentLevel(availability)
    nozzle_level = ClogLevel(clog)
    air_level = PressureLevel(pressure)
    width_level = SprayWidthLevel(width, target_min, target_max)
    filter_level = PercentLevel(maintainability, warn=50, bad=25)
    quality_level = PercentLevel(quality, warn=90, bad=80)

    return [
        Component("arm", "🦾", "機械手臂", "RobotArm", arm_level, f"可用度 {FormatValue(availability, 1, '%')}", LookupDiagnosis("arm", arm_level, DirectionLowOk(availability, arm_level), common)),
        Component("nozzle", "💧", "噴嘴", "Nozzle", nozzle_level, f"堵塞率 {FormatValue(clog, 1, '%')}", LookupDiagnosis("nozzle", nozzle_level, DirectionHighOk(clog, nozzle_level), common)),
        Component("air", "⚙️", "空壓機", "AirCompressor", air_level, f"壓力 {FormatValue(pressure, 1, ' bar')}", LookupDiagnosis("air", air_level, DirectionLowOk(pressure, air_level), common)),
        Component("width", "↔️", "噴幅", "SprayWidth", width_level, f"噴幅 {FormatValue(width, 1, ' mm')}", LookupDiagnosis("width", width_level, DirectionSprayWidth(width, target_min, target_max, width_level), common)),
        Component("filter", "🧽", "濾網", "FilterMesh", filter_level, f"維護性 {FormatValue(maintainability, 1, '%')}", LookupDiagnosis("filter", filter_level, DirectionLowOk(maintainability, filter_level), common)),
        Component("quality", "📏", "品質", "Quality", quality_level, f"膜厚穩定度 {FormatValue(quality, 1, '%')}", LookupDiagnosis("quality", quality_level, DirectionLowOk(quality, quality_level), common)),
    ]


def BuildStationOutput(station: Dict[str, Any]) -> Dict[str, Any]:
    components = BuildComponents(station)
    has_bad = any(component["level"] == "bad" for component in components)
    has_warn = any(component["level"] == "warn" for component in components)
    if has_bad:
        overall = "Alarm"
        risk_text = "高風險"
    elif has_warn:
        overall = "Maintenance"
        risk_text = "中風險"
    else:
        overall = "Running"
        risk_text = "低風險"
    return {
        "id": station.get("id"),
        "lineId": station.get("line_id"),
        "name": station.get("name"),
        "englishName": RemoveSpaces(station.get("english_name")),
        "overall": overall,
        "riskText": risk_text,
        "recipe": station.get("recipe"),
        "pressure": RoundValue(station.get("pressure_bar"), 1),
        "flowRate": RoundValue(station.get("flow_rate_ml_min"), 1),
        "sprayWidth": RoundValue(station.get("spray_width_mm"), 1),
        "targetMin": station.get("target_min_mm"),
        "targetMax": station.get("target_max_mm"),
        "temperature": RoundValue(station.get("temperature_c"), 1),
        "availability": RoundValue(station.get("availability_pct"), 1),
        "maintainability": RoundValue(station.get("maintainability_pct"), 1),
        "clog": RoundValue(station.get("clog_rate_pct"), 1),
        "quality": RoundValue(station.get("quality_score_pct"), 1),
        "utilization": RoundValue(station.get("utilization_pct"), 1),
        "cycle": RoundValue(station.get("cycle_time_sec"), 0),
        "components": components,
    }


def BuildDashboardPayloadFromStations(stations: List[Dict[str, Any]], viewer_state: Dict[str, Any], source_type: str, source_error: Any = None) -> Dict[str, Any]:
    normal_count = sum(1 for station in stations if station["overall"] in ["Running", "Standby"])
    warning_count = sum(1 for station in stations if station["overall"] in ["Maintenance", "Alarm"])
    risk_count = sum(1 for station in stations if station["riskText"] in ["中風險", "高風險"])
    return {
        "schema_version": "v1.1",
        "service_name": "SprayingDashboardIntegrated",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_type": source_type,
        "source_error": source_error,
        "service_root": str(SERVICE_ROOT) if SERVICE_ROOT else None,
        "diagnosis_database_file": str(DIAGNOSIS_DB_FILE),
        "diagnosis_rule_file": str(DIAGNOSIS_RULE_FILE),
        "update_interval_sec": 15,
        "viewer_state": viewer_state,
        "summary": {
            "total_station_count": len(stations),
            "normal_count": normal_count,
            "warning_count": warning_count,
            "predict_risk_count": risk_count,
        },
        "stations": stations,
    }


def BuildDashboardPayload(ui_output: Dict[str, Any]) -> Dict[str, Any]:
    stations = [BuildStationOutput(station) for station in ui_output.get("stations", [])]
    return BuildDashboardPayloadFromStations(stations=stations, viewer_state=ui_output.get("viewer_state", {}), source_type="TimeSeriesService")


def BuildServiceRequest(mode: str, slider_value: float, line_scope: str = "all") -> Dict[str, Any]:
    # 用 15 秒為一個資料 bucket，讓 summary 與 detail 在同一個更新週期內數值一致。
    # 同學的 random_data_provider 支援 random_seed，所以按鈕 detail 不會和畫面總覽差太多。
    data_bucket = int(time.time() / 15)
    return {
        "schema_version": "v1.0",
        "service_name": "TimeSeriesService",
        "request_id": f"dashboard_{mode}_{slider_value}_{line_scope}_{data_bucket}",
        "mode": mode,
        "window_type": "current" if slider_value == 0 else "2hour",
        "slider_value": slider_value,
        "line_scope": line_scope,
        "random_seed": data_bucket,
        "requested_metrics": [
            "availability_pct", "clog_rate_pct", "pressure_bar", "flow_rate_ml_min",
            "maintainability_pct", "quality_score_pct", "risk_text", "spray_width_mm",
            "recipe_name", "temperature_c", "utilization_pct", "cycle_time_sec",
        ],
    }


def BuildViewerState(mode: str, slider_value: float) -> Dict[str, Any]:
    if slider_value < 0:
        time_type = "past"
        display_label = f"past {abs(slider_value)}"
    elif slider_value > 0:
        time_type = "future"
        display_label = f"future {slider_value}"
    else:
        time_type = "current"
        display_label = "current"
    return {
        "mode": mode,
        "window_type": "current" if slider_value == 0 else "2hour",
        "slider_value": slider_value,
        "display_label": display_label,
        "time_type": time_type,
        "is_history": time_type == "past",
        "is_current": time_type == "current",
        "is_future": time_type == "future",
    }




STATION_ID_TO_LINE_ID = {
    "M1": "line_1",
    "M2": "line_2",
    "M3": "line_3",
    "line_1": "line_1",
    "line_2": "line_2",
    "line_3": "line_3",
}

SERVICE_COMPONENT_MAP = {
    "nozzle": "nozzle",
    "filter": "filter_mesh",
    "width": "spray_width",
    "filter_mesh": "filter_mesh",
    "spray_width": "spray_width",
}

COMPONENT_META = {
    "arm": {"icon": "🦾", "name": "機械手臂", "en": "RobotArm"},
    "nozzle": {"icon": "💧", "name": "噴嘴", "en": "Nozzle"},
    "air": {"icon": "⚙️", "name": "空壓機", "en": "AirCompressor"},
    "width": {"icon": "↔️", "name": "噴幅", "en": "SprayWidth"},
    "filter": {"icon": "🧽", "name": "濾網", "en": "FilterMesh"},
    "quality": {"icon": "📏", "name": "品質", "en": "Quality"},
}

# 儲存前端目前畫面用的最新資料快照。
# 用途：Dashboard 與 Detail 必須顯示同一批數值，避免 detail 重新呼叫 service 後數值跳掉。
LATEST_DASHBOARD_SNAPSHOTS: Dict[str, Dict[str, Any]] = {}


def NormalizeSliderValue(slider_value: float) -> float:
    try:
        return round(float(slider_value), 6)
    except Exception:
        return 0.0


def SnapshotKey(mode: str, slider_value: float) -> str:
    return f"{mode}|{NormalizeSliderValue(slider_value)}"


def SaveDashboardSnapshot(mode: str, slider_value: float, payload: Dict[str, Any]) -> None:
    # 深拷貝，避免後續 detail 補欄位時污染原始 dashboard 資料。
    LATEST_DASHBOARD_SNAPSHOTS[SnapshotKey(mode, slider_value)] = {
        "saved_at": time.time(),
        "payload": copy.deepcopy(payload),
    }

    # 避免快取無限制長大，只保留最近 20 筆不同時間軸狀態。
    if len(LATEST_DASHBOARD_SNAPSHOTS) > 20:
        oldest_key = sorted(
            LATEST_DASHBOARD_SNAPSHOTS.items(),
            key=lambda item: item[1].get("saved_at", 0),
        )[0][0]
        LATEST_DASHBOARD_SNAPSHOTS.pop(oldest_key, None)


def GetDashboardSnapshot(mode: str, slider_value: float) -> Optional[Dict[str, Any]]:
    record = LATEST_DASHBOARD_SNAPSHOTS.get(SnapshotKey(mode, slider_value))
    if not record:
        return None
    return copy.deepcopy(record.get("payload"))


def FindSnapshotStation(mode: str, slider_value: float, station_id: str) -> Optional[Dict[str, Any]]:
    payload = GetDashboardSnapshot(mode, slider_value)
    if not payload:
        return None
    line_id = STATION_ID_TO_LINE_ID.get(station_id, station_id)
    for station in payload.get("stations", []):
        if station.get("id") == station_id or station.get("lineId") == line_id:
            return station
    return None


def FindSnapshotComponent(mode: str, slider_value: float, station_id: str, component_key: str) -> Optional[Dict[str, Any]]:
    station = FindSnapshotStation(mode, slider_value, station_id)
    if not station:
        return None
    for component in station.get("components", []):
        if component.get("key") == component_key:
            return component
    return None


def ResolveLineId(station_id: str) -> str:
    line_id = STATION_ID_TO_LINE_ID.get(station_id)
    if not line_id:
        raise ValueError(f"unknown station_id or line_id: {station_id}")
    return line_id


def StationRawFromUiStationDetail(ui_detail: Dict[str, Any]) -> Dict[str, Any]:
    metrics = ui_detail.get("metrics", {})
    process = ui_detail.get("process_parameters", {})
    image = ui_detail.get("spray_width_image", {})
    return {
        "id": ui_detail.get("ui_id"),
        "line_id": ui_detail.get("line_id"),
        "name": ui_detail.get("name"),
        "english_name": ui_detail.get("english_name"),
        "recipe": process.get("recipe_name"),
        "pressure_bar": metrics.get("pressure_bar"),
        "flow_rate_ml_min": metrics.get("flow_rate_ml_min"),
        "spray_width_mm": metrics.get("spray_width_mm"),
        "target_min_mm": image.get("target_min_mm"),
        "target_max_mm": image.get("target_max_mm"),
        "temperature_c": process.get("temperature_c"),
        "availability_pct": metrics.get("availability_pct"),
        "maintainability_pct": metrics.get("maintainability_pct"),
        "clog_rate_pct": metrics.get("clog_rate_pct"),
        "quality_score_pct": metrics.get("quality_score_pct"),
        "utilization_pct": process.get("utilization_pct"),
        "cycle_time_sec": process.get("cycle_time_sec"),
    }


def BuildUiStationDetailByService(mode: str, slider_value: float, line_id: str) -> Dict[str, Any]:
    if not SERVICE_AVAILABLE or service is None:
        raise RuntimeError(f"TimeSeriesService unavailable: {SERVICE_ERROR}")
    core_request = BuildServiceRequest(mode=mode, slider_value=slider_value, line_scope=line_id)
    core_output = service.HandleTimeSeriesQuery(core_request)
    return BuildUiStationDetailOutput(core_output=core_output, line_id=line_id)


def BuildUiComponentDetailByService(mode: str, slider_value: float, line_id: str, component_name: str) -> Dict[str, Any]:
    if not SERVICE_AVAILABLE or service is None:
        raise RuntimeError(f"TimeSeriesService unavailable: {SERVICE_ERROR}")
    core_request = BuildServiceRequest(mode=mode, slider_value=slider_value, line_scope=line_id)
    core_output = service.HandleTimeSeriesQuery(core_request)
    return BuildUiComponentDetailOutput(core_output=core_output, line_id=line_id, component_name=component_name)


def AnnotateDetailComponent(component: Dict[str, Any], detail_source: str, detail_endpoint: str) -> Dict[str, Any]:
    result = copy.deepcopy(component)
    result["detail_source"] = detail_source
    result["detail_endpoint"] = detail_endpoint
    result["display_value_source"] = "latest_dashboard_snapshot"
    return result


def BuildDashboardStationDetailPayload(mode: str, slider_value: float, station_id: str) -> Dict[str, Any]:
    line_id = ResolveLineId(station_id)

    # 這裡仍然會呼叫同學的 station-detail function，作為真正 detail API 串接。
    # 但畫面顯示數值採用 latest dashboard snapshot，避免同學 random service 每 call 一次數值不同。
    ui_detail = BuildUiStationDetailByService(mode=mode, slider_value=slider_value, line_id=line_id)

    snapshot_station = FindSnapshotStation(mode, slider_value, station_id)
    if snapshot_station:
        station_output = copy.deepcopy(snapshot_station)
        station_output["detail_value_policy"] = "values_from_latest_dashboard_snapshot"
    else:
        station_raw = StationRawFromUiStationDetail(ui_detail)
        station_output = BuildStationOutput(station_raw)
        station_output["detail_value_policy"] = "values_from_station_detail_service_fallback"

    issues = [
        AnnotateDetailComponent(component, "BuildUiStationDetailOutput", "POST /api/time-series/ui/station-detail")
        for component in station_output.get("components", [])
        if component.get("level") != "ok"
    ]

    return {
        "schema_version": "v1.3",
        "output_type": "dashboard_station_detail",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "detail_function": "BuildUiStationDetailOutput",
        "detail_endpoint": "POST /api/time-series/ui/station-detail",
        "source": ui_detail.get("source"),
        "station": station_output,
        "issues": issues,
        "raw_detail": ui_detail,
        "value_consistency": "detail display values are read from latest dashboard snapshot when available",
        "diagnosis_database_file": str(DIAGNOSIS_DB_FILE),
    }


def BuildComponentFromServiceComponentDetail(ui_component_detail: Dict[str, Any]) -> Dict[str, Any]:
    service_component = ui_component_detail.get("component_name")
    data = ui_component_detail.get("data", {})

    if service_component == "nozzle":
        key = "nozzle"
        clog = data.get("nozzle_clog_rate_pct")
        level = ClogLevel(clog)
        value = f"堵塞率 {FormatValue(clog, 1, '%')}"
        context = {"clog": clog if IsNumber(clog) else 0, "pressure": data.get("pressure_bar") or 0}
        diagnosis = LookupDiagnosis("nozzle", level, DirectionHighOk(clog, level), context)

    elif service_component == "filter_mesh":
        key = "filter"
        maintainability = data.get("filter_maintainability_pct")
        level = PercentLevel(maintainability, warn=50, bad=25)
        value = f"維護性 {FormatValue(maintainability, 1, '%')}"
        context = {"maintainability": maintainability if IsNumber(maintainability) else 0, "clog": data.get("filter_clog_rate_pct") or 0}
        diagnosis = LookupDiagnosis("filter", level, DirectionLowOk(maintainability, level), context)

    elif service_component == "spray_width":
        key = "width"
        width = data.get("spray_width_mm")
        target_min = data.get("target_min_mm")
        target_max = data.get("target_max_mm")
        level = SprayWidthLevel(width, target_min, target_max)
        value = f"噴幅 {FormatValue(width, 1, ' mm')}"
        context = {"sprayWidth": width if IsNumber(width) else 0, "targetMin": target_min if IsNumber(target_min) else 0, "targetMax": target_max if IsNumber(target_max) else 0}
        diagnosis = LookupDiagnosis("width", level, DirectionSprayWidth(width, target_min, target_max, level), context)

    else:
        raise ValueError(f"unsupported service component: {service_component}")

    meta = COMPONENT_META[key]
    component = Component(key, meta["icon"], meta["name"], meta["en"], level, value, diagnosis)
    component["detail_source"] = "BuildUiComponentDetailOutput"
    component["detail_endpoint"] = "POST /api/time-series/ui/component-detail"
    component["raw_detail"] = ui_component_detail
    return component


def BuildDashboardComponentDetailPayload(mode: str, slider_value: float, station_id: str, component_key: str) -> Dict[str, Any]:
    line_id = ResolveLineId(station_id)
    service_component = SERVICE_COMPONENT_MAP.get(component_key)

    if service_component:
        # 這裡真的會呼叫同學的 component-detail function。
        ui_component_detail = BuildUiComponentDetailByService(
            mode=mode,
            slider_value=slider_value,
            line_id=line_id,
            component_name=service_component,
        )

        snapshot_component = FindSnapshotComponent(mode, slider_value, station_id, component_key)
        if snapshot_component:
            component = AnnotateDetailComponent(
                snapshot_component,
                "BuildUiComponentDetailOutput",
                "POST /api/time-series/ui/component-detail",
            )
        else:
            component = BuildComponentFromServiceComponentDetail(ui_component_detail)
            component["display_value_source"] = "component_detail_service_fallback"

        component["raw_detail"] = ui_component_detail
        return {
            "schema_version": "v1.3",
            "output_type": "dashboard_component_detail",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "detail_function": "BuildUiComponentDetailOutput",
            "detail_endpoint": "POST /api/time-series/ui/component-detail",
            "station_id": station_id,
            "line_id": line_id,
            "component": component,
            "raw_detail": ui_component_detail,
            "value_consistency": "detail display value comes from latest dashboard snapshot when available",
            "diagnosis_database_file": str(DIAGNOSIS_DB_FILE),
        }

    # TimeSeriesService 目前只有 nozzle / filter_mesh / spray_width 三個 component detail。
    # 其他零件仍會呼叫 station-detail function，但顯示值優先使用 dashboard snapshot。
    station_payload = BuildDashboardStationDetailPayload(mode=mode, slider_value=slider_value, station_id=station_id)
    snapshot_component = FindSnapshotComponent(mode, slider_value, station_id, component_key)
    if snapshot_component:
        component = AnnotateDetailComponent(
            snapshot_component,
            "BuildUiStationDetailOutput",
            "POST /api/time-series/ui/station-detail",
        )
    else:
        component = next((item for item in station_payload["station"].get("components", []) if item.get("key") == component_key), None)
        if component is None:
            raise ValueError(f"component_key not found: {component_key}")
        component = AnnotateDetailComponent(
            component,
            "BuildUiStationDetailOutput",
            "POST /api/time-series/ui/station-detail",
        )
        component["display_value_source"] = "station_detail_service_fallback"

    return {
        "schema_version": "v1.3",
        "output_type": "dashboard_component_detail",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "detail_function": "BuildUiStationDetailOutput",
        "detail_endpoint": "POST /api/time-series/ui/station-detail",
        "station_id": station_id,
        "line_id": line_id,
        "component": component,
        "raw_detail": station_payload.get("raw_detail"),
        "value_consistency": "detail display value comes from latest dashboard snapshot when available",
        "diagnosis_database_file": str(DIAGNOSIS_DB_FILE),
    }

def BuildFallbackPayload(mode: str, slider_value: float, source_error: Any = None) -> Dict[str, Any]:
    # 備援資料每 15 秒才改變一次，避免看起來像每秒亂跳。
    t = int(time.time() / 15)
    wave = math.sin(t)
    future_factor = max(0, slider_value) * 0.7
    past_factor = math.sin(slider_value) if slider_value < 0 else 0
    base_rows = [
        {"id":"M1","line_id":"line_1","name":"底漆站","english_name":"PrimerStation","recipe":"Primer_A","pressure":2.5,"width":120,"temp":28,"availability":95,"maintainability":92,"clog":12,"quality":96,"utilization":78,"cycle":42},
        {"id":"M2","line_id":"line_2","name":"面漆站","english_name":"TopcoatStation","recipe":"Topcoat_B","pressure":2.1,"width":100,"temp":27,"availability":88,"maintainability":86,"clog":25,"quality":91,"utilization":72,"cycle":46},
        {"id":"M3","line_id":"line_3","name":"金漆站","english_name":"GoldPaintStation","recipe":"Gold_C","pressure":1.7,"width":82,"temp":26,"availability":72,"maintainability":65,"clog":55,"quality":82,"utilization":60,"cycle":55},
    ]
    raw_stations = []
    for idx, row in enumerate(base_rows):
        drift = wave * (idx + 1) * 2 + future_factor * (idx + 1) * 4 + past_factor * 3
        clog = max(0, min(100, row["clog"] + drift))
        pressure = row["pressure"] - clog * 0.006
        spray_width = row["width"] - clog * 0.45
        availability = max(0, min(100, row["availability"] - max(0, future_factor) * (idx + 1) * 2 + wave))
        maintainability = max(0, min(100, row["maintainability"] - max(0, future_factor) * (idx + 1) * 2 + wave))
        quality = max(0, min(100, row["quality"] - max(0, future_factor) * (idx + 1) * 1.5 + wave))
        raw_stations.append({
            "id": row["id"], "line_id": row["line_id"], "name": row["name"], "english_name": row["english_name"], "recipe": row["recipe"],
            "pressure_bar": round(pressure, 1), "flow_rate_ml_min": round(max(0, 100 - clog), 1), "spray_width_mm": round(spray_width, 1),
            "target_min_mm": 110, "target_max_mm": 130, "temperature_c": round(row["temp"] + future_factor * 0.3, 1),
            "availability_pct": round(availability, 1), "maintainability_pct": round(maintainability, 1), "clog_rate_pct": round(clog, 1),
            "quality_score_pct": round(quality, 1), "utilization_pct": round(max(0, min(100, row["utilization"] - future_factor)), 1),
            "cycle_time_sec": round(row["cycle"] + max(0, future_factor) * (idx + 1), 0),
        })
    stations = [BuildStationOutput(station) for station in raw_stations]
    return BuildDashboardPayloadFromStations(stations, BuildViewerState(mode, slider_value), "FallbackDynamicData", source_error)


@app.get("/", response_class=HTMLResponse)
def Home():
    if not HTML_FILE.exists():
        return HTMLResponse("<h2>找不到 spraying_dashboard_updated.html</h2><p>請確認 main.py 和 HTML 放在同一個資料夾。</p>", status_code=404, headers=NO_CACHE_HEADERS)
    return FileResponse(HTML_FILE, media_type="text/html; charset=utf-8", headers=NO_CACHE_HEADERS)


@app.get("/spraying_dashboard_updated.html")
def DashboardHtml():
    return Home()


@app.get("/api/health")
def HealthCheck():
    return {
        "dashboard": "running",
        "base_dir": str(BASE_DIR),
        "service_root": str(SERVICE_ROOT) if SERVICE_ROOT else None,
        "service_available": SERVICE_AVAILABLE,
        "service_error": SERVICE_ERROR,
        "diagnosis_database_file": str(DIAGNOSIS_DB_FILE),
        "diagnosis_database_file": str(DIAGNOSIS_DB_FILE),
        "diagnosis_database_exists": DIAGNOSIS_DB_FILE.exists(),
        "diagnosis_rule_count": CountDiagnosisRules(),
        "diagnosis_rule_file": str(DIAGNOSIS_RULE_FILE),
        "diagnosis_rule_exists": DIAGNOSIS_RULE_FILE.exists(),
        "html_file": str(HTML_FILE),
        "api": "/api/dashboard-data",
        "diagnosis_api": "/api/diagnosis-rules",
        "station_detail_api": "/api/station-detail",
        "component_detail_api": "/api/component-detail",
        "ui_station_detail_proxy": "POST /api/time-series/ui/station-detail",
        "ui_component_detail_proxy": "POST /api/time-series/ui/component-detail",
        "detail_functions_available": SERVICE_AVAILABLE and BuildUiStationDetailOutput is not None and BuildUiComponentDetailOutput is not None,
        "update_interval_sec": 15,
        "snapshot_cache_count": len(LATEST_DASHBOARD_SNAPSHOTS),
        "value_consistency_policy": "dashboard-data 會先存 latest snapshot；station-detail/component-detail 仍會呼叫同學 detail function，但顯示值會優先使用同一份 snapshot，避免數值不一致。",
        "note": "前端每 15 秒呼叫 /api/dashboard-data；按下異常/零件按鈕時會再呼叫 station-detail 或 component-detail，並使用同學的 BuildUiStationDetailOutput / BuildUiComponentDetailOutput。",
    }


@app.get("/api/diagnosis-rules")
def DiagnosisRules():
    return JSONResponse(
        content={
            "source": "diagnosis_rules.db",
            "database_file": str(DIAGNOSIS_DB_FILE),
            "rule_count": CountDiagnosisRules(),
            "rules": LoadDiagnosisRules(),
        },
        headers=NO_CACHE_HEADERS,
    )


@app.get("/api/dashboard-data")
def DashboardData(mode: str = Query("time"), slider_value: float = Query(0)):
    if SERVICE_AVAILABLE and service is not None and BuildUiSummaryOutput is not None:
        try:
            core_request = BuildServiceRequest(mode=mode, slider_value=slider_value)
            core_output = service.HandleTimeSeriesQuery(core_request)
            ui_output = BuildUiSummaryOutput(core_output)
            payload = BuildDashboardPayload(ui_output)
            SaveDashboardSnapshot(mode, slider_value, payload)
            return JSONResponse(content=payload, headers=NO_CACHE_HEADERS)
        except Exception as exc:
            fallback_payload = BuildFallbackPayload(mode, slider_value, source_error=repr(exc))
            SaveDashboardSnapshot(mode, slider_value, fallback_payload)
            return JSONResponse(content=fallback_payload, headers=NO_CACHE_HEADERS)
    fallback_payload = BuildFallbackPayload(mode, slider_value, source_error=SERVICE_ERROR)
    SaveDashboardSnapshot(mode, slider_value, fallback_payload)
    return JSONResponse(content=fallback_payload, headers=NO_CACHE_HEADERS)


@app.post("/api/time-series/ui/summary")
def TimeSeriesUiSummaryProxy(request: Dict[str, Any]):
    slider_value = request.get("slider_value", 0)
    mode = request.get("mode", "time")
    if SERVICE_AVAILABLE and service is not None and BuildUiSummaryOutput is not None:
        try:
            core_request = BuildServiceRequest(mode=mode, slider_value=slider_value)
            core_output = service.HandleTimeSeriesQuery(core_request)
            return JSONResponse(content=BuildUiSummaryOutput(core_output), headers=NO_CACHE_HEADERS)
        except Exception as exc:
            return JSONResponse(content=BuildFallbackPayload(mode, slider_value, repr(exc)), headers=NO_CACHE_HEADERS)
    return JSONResponse(content=BuildFallbackPayload(mode, slider_value, SERVICE_ERROR), headers=NO_CACHE_HEADERS)


@app.get("/api/station-detail")
def DashboardStationDetail(station_id: str = Query(...), mode: str = Query("time"), slider_value: float = Query(0)):
    try:
        payload = BuildDashboardStationDetailPayload(mode=mode, slider_value=slider_value, station_id=station_id)
        return JSONResponse(content=payload, headers=NO_CACHE_HEADERS)
    except Exception as exc:
        return JSONResponse(content={"error": repr(exc), "station_id": station_id}, status_code=500, headers=NO_CACHE_HEADERS)


@app.get("/api/component-detail")
def DashboardComponentDetail(station_id: str = Query(...), component_key: str = Query(...), mode: str = Query("time"), slider_value: float = Query(0)):
    try:
        payload = BuildDashboardComponentDetailPayload(mode=mode, slider_value=slider_value, station_id=station_id, component_key=component_key)
        return JSONResponse(content=payload, headers=NO_CACHE_HEADERS)
    except Exception as exc:
        return JSONResponse(content={"error": repr(exc), "station_id": station_id, "component_key": component_key}, status_code=500, headers=NO_CACHE_HEADERS)


@app.post("/api/time-series/ui/station-detail")
def TimeSeriesUiStationDetailProxy(request: Dict[str, Any]):
    try:
        if "line_id" not in request:
            raise ValueError("request must include line_id")
        mode = request.get("mode", "time")
        slider_value = float(request.get("slider_value", 0))
        line_id = ResolveLineId(request["line_id"])
        ui_detail = BuildUiStationDetailByService(mode=mode, slider_value=slider_value, line_id=line_id)
        return JSONResponse(content=ui_detail, headers=NO_CACHE_HEADERS)
    except Exception as exc:
        return JSONResponse(content={"error": repr(exc), "request": request}, status_code=500, headers=NO_CACHE_HEADERS)


@app.post("/api/time-series/ui/component-detail")
def TimeSeriesUiComponentDetailProxy(request: Dict[str, Any]):
    try:
        if "line_id" not in request:
            raise ValueError("request must include line_id")
        if "component_name" not in request:
            raise ValueError("request must include component_name")
        mode = request.get("mode", "time")
        slider_value = float(request.get("slider_value", 0))
        line_id = ResolveLineId(request["line_id"])
        component_name = request["component_name"]
        ui_detail = BuildUiComponentDetailByService(mode=mode, slider_value=slider_value, line_id=line_id, component_name=component_name)
        return JSONResponse(content=ui_detail, headers=NO_CACHE_HEADERS)
    except Exception as exc:
        return JSONResponse(content={"error": repr(exc), "request": request}, status_code=500, headers=NO_CACHE_HEADERS)
