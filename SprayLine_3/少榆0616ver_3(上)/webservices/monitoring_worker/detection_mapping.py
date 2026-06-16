"""Mapping helpers for MonitoringWorker detection results.

0616ver_3 原則：
- threshold 數值判斷仍由 rules/sensor_thresholds.json 負責。
- 本檔只負責 sensor_name -> issue_state / cause_id / response_id / batch_station_status 欄位。
- cause_id / response_id 先依 Database/versionB 目前 catalog 命名對齊，最終仍待余宇承確認。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MAPPING_FILE = Path(__file__).resolve().parents[2] / "rules" / "sensor_event_mapping.json"

STATE_FIELDS = [
    "robot_arm_state",
    "nozzle_state",
    "filter_state",
    "compressor_state",
    "spray_width_state",
    "quality_state",
]

RESPONSE_FIELDS = [
    "robot_arm_response_id",
    "nozzle_response_id",
    "filter_response_id",
    "compressor_response_id",
    "spray_width_response_id",
    "quality_response_id",
]

_STATE_RANK = {None: 0, "ok": 1, "normal": 1, "warning": 2, "fault": 3}


def load_sensor_event_mapping() -> dict[str, Any]:
    return json.loads(MAPPING_FILE.read_text(encoding="utf-8"))


def get_sensor_mapping(sensor_name: str) -> dict[str, Any]:
    data = load_sensor_event_mapping()
    return data.get("sensor_mapping", {}).get(sensor_name, {})


def choose_more_severe(current_state: str | None, new_state: str | None) -> str | None:
    current_rank = _STATE_RANK.get(current_state, 0)
    new_rank = _STATE_RANK.get(new_state, 0)
    return new_state if new_rank >= current_rank else current_state


def build_detection_result(sensor_name: str, measured_value: float, state: str) -> dict[str, Any]:
    """Return a detection object enriched with DB catalog/status mapping.

    `state` is the DB alert severity value: warning / fault.
    `issue_state` is the concrete issue ID used by troubleshooting knowledge.
    `cause_id` currently mirrors Database/versionB cause_catalog IDs where available.
    """
    mapping = get_sensor_mapping(sensor_name)
    response_ids = list(mapping.get("response_ids") or [])
    primary_response_id = response_ids[0] if response_ids else None
    issue_state = mapping.get("issue_state")
    cause_id = mapping.get("cause_id")

    return {
        "sensor_name": sensor_name,
        "measured_value": float(measured_value),
        "state": state,
        "severity_state": state,
        "issue_state": issue_state,
        "fault_state": issue_state,
        "cause_id": cause_id,
        "cause": cause_id,
        "response_ids": response_ids,
        "primary_response_id": primary_response_id,
        "state_field": mapping.get("state_field"),
        "response_field": mapping.get("response_field"),
        "component_id": mapping.get("component_id"),
        "mapping_status": load_sensor_event_mapping().get("mapping_status"),
        "message": (
            f"{sensor_name} classified as {state}"
            + (f"; issue_state={issue_state}" if issue_state else "")
            + (f"; cause_id={cause_id}" if cause_id else "")
        ),
    }


def empty_status_record(batch_id: str, station_id: str) -> dict[str, Any]:
    data = load_sensor_event_mapping()
    defaults = data.get("defaults", {})
    record: dict[str, Any] = {"batch_id": batch_id, "station_id": station_id}
    for field in STATE_FIELDS:
        record[field] = defaults.get(field, "ok")
    for field in RESPONSE_FIELDS:
        record[field] = None
    return record


def normalize_existing_status(batch_id: str, station_id: str, current: dict[str, Any] | None) -> dict[str, Any]:
    record = empty_status_record(batch_id, station_id)
    if not current:
        return record
    for field in STATE_FIELDS + RESPONSE_FIELDS:
        if field in current and current[field] is not None:
            record[field] = current[field]
    return record


def build_batch_station_status_record(
    batch_id: str,
    station_id: str,
    detected: dict[str, Any],
    current: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a full 6-state + 6-response snapshot for db_status.upsert.

    db_status.upsert_batch_station_status() overwrites all 12 status/response columns.
    Therefore 少榆端 must submit a complete snapshot rather than a single changed field.
    """
    record = normalize_existing_status(batch_id, station_id, current)
    state_field = detected.get("state_field")
    response_field = detected.get("response_field")

    if state_field:
        record[state_field] = choose_more_severe(record.get(state_field), detected.get("state"))
    if response_field and detected.get("primary_response_id"):
        record[response_field] = detected["primary_response_id"]
    return record
