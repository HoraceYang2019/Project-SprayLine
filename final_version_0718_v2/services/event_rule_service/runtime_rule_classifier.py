from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_TTL_PATH = PROJECT_ROOT / "ontology" / "sprayline_threshold.ttl"
JSON_RULE_FILE = PROJECT_ROOT / "rules" / "sensor_thresholds.json"
EVENT_MAPPING_FILE = PROJECT_ROOT / "rules" / "sensor_event_mapping.json"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ontology.rule_inference import infer_state  # noqa: E402


VALID_STATES = {"normal", "warning", "fault"}


@lru_cache(maxsize=8)
def _load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _in_band(value: float, band: dict[str, Any]) -> bool:
    if "min" in band and value < float(band["min"]):
        return False
    if "min_exclusive" in band and value <= float(band["min_exclusive"]):
        return False
    if "max" in band and value > float(band["max"]):
        return False
    if "max_exclusive" in band and value >= float(band["max_exclusive"]):
        return False
    return True


def _json_fallback(
    metric: str,
    value: float,
    json_rule_file: Path,
    fallback_reason: str,
) -> dict[str, Any]:
    rules = _load_json(str(json_rule_file)).get("rules", {})
    rule = rules.get(metric)
    if not rule:
        return {
            "metric": metric,
            "value": value,
            "state": "unknown",
            "level": "unknown",
            "cause_id": None,
            "response_ids": [],
            "rule_engine": "none",
            "rule_source": None,
            "fallback_reason": fallback_reason,
        }

    if any(_in_band(value, band) for band in rule.get("fault", [])):
        state = "fault"
    elif any(_in_band(value, band) for band in rule.get("warning", [])):
        state = "warning"
    elif _in_band(value, rule.get("normal", {})):
        state = "normal"
    else:
        state = "warning"

    mapping = _load_json(str(EVENT_MAPPING_FILE)).get("sensor_mapping", {}).get(metric, {})
    abnormal = state != "normal"
    return {
        "metric": metric,
        "value": value,
        "unit": rule.get("unit"),
        "state": state,
        "level": "ok" if state == "normal" else state,
        "cause_id": mapping.get("cause_id") if abnormal else None,
        "response_ids": list(mapping.get("response_ids") or []) if abnormal else [],
        "component_id": mapping.get("component_id"),
        "rule_engine": "json_threshold_fallback",
        "rule_source": "rules/sensor_thresholds.json",
        "fallback_reason": fallback_reason,
    }


def classify_sensor_value(
    metric: str,
    value: Any,
    *,
    ttl_path: str | Path = ONTOLOGY_TTL_PATH,
    json_rule_file: str | Path = JSON_RULE_FILE,
) -> dict[str, Any]:
    """Classify one metric with Ontology TTL as the formal runtime source."""
    if value is None or isinstance(value, bool):
        return {
            "metric": metric,
            "value": value,
            "state": "unknown",
            "level": "unknown",
            "cause_id": None,
            "response_ids": [],
            "rule_engine": "none",
            "rule_source": None,
            "fallback_reason": "non_numeric_value",
        }

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return {
            "metric": metric,
            "value": value,
            "state": "unknown",
            "level": "unknown",
            "cause_id": None,
            "response_ids": [],
            "rule_engine": "none",
            "rule_source": None,
            "fallback_reason": "non_numeric_value",
        }

    ttl_path = Path(ttl_path)
    json_rule_file = Path(json_rule_file)
    try:
        result = infer_state(metric, numeric_value, ttl_path)
        state = result.get("state")

        # 正常、警告、故障直接採用 Ontology 結果。
        # 若 Ontology 有此感測器規則，但數值落在未定義區間，
        # 也保留 unknown，不再轉交 JSON fallback 誤判。
        if state in VALID_STATES or (
            state == "unknown"
            and "threshold" in result
        ):
            result["source"] = "ontology/sprayline_threshold.ttl"
            result["rule_source"] = "ontology/sprayline_threshold.ttl"
            result["rule_engine"] = "ontology.rule_inference"
            result["fallback_reason"] = None
            return result

        # 只有 Ontology 完全沒有該 metric 規則時，才使用 JSON fallback。
        fallback_reason = "ontology_rule_missing"

    except Exception as exc:
        fallback_reason = (
            f"ontology_error:{exc.__class__.__name__}"
        )

    return _json_fallback(metric, numeric_value, json_rule_file, fallback_reason)


def classify_value(metric: str, value: Any) -> str | None:
    result = classify_sensor_value(metric, value)
    state = result.get("state")
    return str(state) if state in VALID_STATES else None
