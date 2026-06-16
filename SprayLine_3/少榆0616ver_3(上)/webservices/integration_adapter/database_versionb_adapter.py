"""Integration adapter for Yu-Cheng Database/versionB functions.

少榆端不負責正式 API Server，也不維護 DB SQL。
本 adapter 只做一件事：集中處理 Database/versionB 的 import path，
讓 FutureService / MonitoringWorker 可以直接 import 余宇承提供的 Python DB functions。

尋找 Database/versionB 的優先順序：
1. 環境變數 SPRAYLINE_DB_FUNCTION_PATH 指向的資料夾
2. 環境變數 SPRAYLINE_PROJECT_ROOT/Database/versionB
3. 本包內附的 external/Database/versionB reference copy
4. 從目前檔案往上尋找 Database/versionB
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any


def locate_database_versionb_path() -> Path:
    candidates: list[Path] = []

    explicit = os.getenv("SPRAYLINE_DB_FUNCTION_PATH")
    if explicit:
        candidates.append(Path(explicit))

    project_root = os.getenv("SPRAYLINE_PROJECT_ROOT")
    if project_root:
        candidates.append(Path(project_root) / "Database" / "versionB")

    here = Path(__file__).resolve()
    package_root = here.parents[2]
    candidates.append(package_root / "external" / "Database" / "versionB")

    for parent in here.parents:
        candidates.append(parent / "Database" / "versionB")

    for candidate in candidates:
        if (candidate / "db_sensor.py").exists() and (candidate / "db_future.py").exists():
            return candidate.resolve()

    tried = "\n".join(str(c) for c in candidates)
    raise FileNotFoundError(
        "找不到 Database/versionB。請設定 SPRAYLINE_PROJECT_ROOT 或 "
        "SPRAYLINE_DB_FUNCTION_PATH。已嘗試：\n" + tried
    )


def ensure_database_versionb_on_path() -> Path:
    db_path = locate_database_versionb_path()
    path_str = str(db_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
    return db_path


def import_database_module(module_name: str):
    ensure_database_versionb_on_path()
    return importlib.import_module(module_name)


def get_connection(**overrides):
    module = import_database_module("db_connection")
    return module.get_connection(**overrides)


def query_sensor_1min(conn, station_id: str, start_time, end_time):
    module = import_database_module("db_sensor")
    return module.query_sensor_1min(conn, station_id, start_time, end_time)


def query_sensor_3min(conn, station_id: str, start_time, end_time):
    module = import_database_module("db_sensor")
    return module.query_sensor_3min(conn, station_id, start_time, end_time)


def insert_alert_event(conn, *, batch_id: str, station_id: str, sensor_name: str,
                       measured_value: float, state: str, cause: str | None = None,
                       message: str | None = None, ts=None) -> str:
    module = import_database_module("db_alert")
    return module.insert_alert_event(
        conn,
        batch_id=batch_id,
        station_id=station_id,
        sensor_name=sensor_name,
        measured_value=measured_value,
        state=state,
        cause=cause,
        message=message,
        ts=ts,
    )


def link_alert_cause(conn, event_id: str, cause_id: str, is_primary: bool = False) -> None:
    module = import_database_module("db_alert")
    return module.link_alert_cause(conn, event_id, cause_id, is_primary=is_primary)


def link_alert_response(conn, event_id: str, response_id: str, executed_at=None, operator_id: str | None = None) -> None:
    module = import_database_module("db_alert")
    return module.link_alert_response(
        conn,
        event_id,
        response_id,
        executed_at=executed_at,
        operator_id=operator_id,
    )


def get_batch_station_status(conn, batch_id: str, station_id: str) -> dict | None:
    module = import_database_module("db_status")
    return module.get_batch_station_status(conn, batch_id, station_id)


def upsert_batch_station_status(conn, record: dict[str, Any]) -> None:
    module = import_database_module("db_status")
    return module.upsert_batch_station_status(conn, record)


def insert_future_prediction_result(conn, payload: dict[str, Any]) -> str:
    module = import_database_module("db_future")
    return module.insert_future_prediction_result(conn, payload)


def get_future_prediction_summary(conn, station_id: str | None = None) -> dict:
    module = import_database_module("db_future")
    return module.get_future_prediction_summary(conn, station_id=station_id)


def import_sprayline_db_queries():
    """Optional aggregate DB query module.

    目前少榆端主流程仍分別 import db_sensor/db_alert/db_status/db_future。
    若余宇承確認 sprayline_db_queries.py 可作為統一入口，可由這裡集中切換。
    """
    return import_database_module("sprayline_db_queries")


def get_adapter_status() -> dict[str, str]:
    path = ensure_database_versionb_on_path()
    return {
        "database_versionB_path": str(path),
        "integration_mode": "direct_python_import",
        "http_endpoint_used": "false",
        "aggregate_entry_available": str((path / "sprayline_db_queries.py").exists()).lower(),
        "aggregate_entry_used_by_default": "false",
    }


if __name__ == "__main__":
    print(get_adapter_status())
