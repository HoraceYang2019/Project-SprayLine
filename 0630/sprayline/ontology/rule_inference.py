from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ThresholdRule:
    metric: str
    component: str | None
    component_zh: str | None
    unit: str | None
    normal_min: float | None
    normal_max: float | None
    warning_low_min: float | None
    warning_low_max: float | None
    warning_high_min: float | None
    warning_high_max: float | None
    fault_low_max: float | None
    fault_high_min: float | None
    cause_id: str | None
    response_ids: list[str]
    description: str | None


def _unescape(value: str) -> str:
    return value.replace('\\"', '"').replace("\\\\", "\\")


def _get_string(block: str, pred: str) -> str | None:
    m = re.search(rf"{re.escape(pred)}\s+\"((?:\\.|[^\"\\])*)\"", block)
    return _unescape(m.group(1)) if m else None


def _get_float(block: str, pred: str) -> float | None:
    m = re.search(rf"{re.escape(pred)}\s+\"([-+]?\d+(?:\.\d+)?)\"\^\^xsd:decimal", block)
    return float(m.group(1)) if m else None


def load_rules(ttl_path: str | Path = "ontology/sprayline_threshold.ttl") -> dict[str, ThresholdRule]:
    text = Path(ttl_path).read_text(encoding="utf-8")
    raw_blocks = re.split(r"\n\s*\n", text)
    rules: dict[str, ThresholdRule] = {}

    for block in raw_blocks:
        if "a sl:SensorThreshold" not in block:
            continue
        metric = _get_string(block, "sl:metricName")
        if not metric:
            continue
        response_ids = _get_string(block, "sl:responseIds") or ""
        rules[metric] = ThresholdRule(
            metric=metric,
            component=_get_string(block, "sl:component"),
            component_zh=_get_string(block, "sl:componentZh"),
            unit=_get_string(block, "sl:unit"),
            normal_min=_get_float(block, "sl:normal_min"),
            normal_max=_get_float(block, "sl:normal_max"),
            warning_low_min=_get_float(block, "sl:warning_low_min"),
            warning_low_max=_get_float(block, "sl:warning_low_max"),
            warning_high_min=_get_float(block, "sl:warning_high_min"),
            warning_high_max=_get_float(block, "sl:warning_high_max"),
            fault_low_max=_get_float(block, "sl:fault_low_max"),
            fault_high_min=_get_float(block, "sl:fault_high_min"),
            cause_id=_get_string(block, "sl:causeId"),
            response_ids=[item for item in response_ids.split("|") if item],
            description=_get_string(block, "sl:description"),
        )
    return rules


def _between(value: float, low: float | None, high: float | None, *, low_inclusive: bool = True, high_inclusive: bool = True) -> bool:
    if low is None and high is None:
        return False
    if low is not None:
        if low_inclusive and value < low:
            return False
        if not low_inclusive and value <= low:
            return False
    if high is not None:
        if high_inclusive and value > high:
            return False
        if not high_inclusive and value >= high:
            return False
    return True


def infer_state(metric: str, value: float, ttl_path: str | Path = "ontology/sprayline_threshold.ttl") -> dict[str, Any]:
    rules = load_rules(ttl_path)
    if metric not in rules:
        return {
            "metric": metric,
            "value": value,
            "state": "unknown",
            "level": "unknown",
            "reason": "No ontology threshold rule found for this metric.",
            "source": str(ttl_path),
        }

    rule = rules[metric]
    if _between(value, rule.normal_min, rule.normal_max):
        state = "normal"
        level = "ok"
        issue = "目前狀態位於正常範圍。"
    elif (
        _between(value, rule.warning_low_min, rule.warning_low_max, high_inclusive=False)
        or _between(value, rule.warning_high_min, rule.warning_high_max, low_inclusive=False)
    ):
        state = "warning"
        level = "warning"
        issue = "目前狀態接近管制邊界，建議觀察趨勢。"
    else:
        state = "fault"
        level = "fault"
        issue = rule.description or "目前狀態超出管制範圍。"

    return {
        "metric": metric,
        "component": rule.component,
        "component_zh": rule.component_zh,
        "value": value,
        "unit": rule.unit,
        "state": state,
        "level": level,
        "issue": issue,
        "cause_id": rule.cause_id if state != "normal" else None,
        "response_ids": rule.response_ids if state != "normal" else [],
        "threshold": {
            "normal_min": rule.normal_min,
            "normal_max": rule.normal_max,
            "warning_low_min": rule.warning_low_min,
            "warning_low_max": rule.warning_low_max,
            "warning_high_min": rule.warning_high_min,
            "warning_high_max": rule.warning_high_max,
            "fault_low_max": rule.fault_low_max,
            "fault_high_min": rule.fault_high_min,
        },
        "source": str(ttl_path),
        "rule_engine": "ontology.rule_inference",
    }


def smoke_cases() -> list[tuple[str, float]]:
    return [
        ("air_pressure_bar", 3.2),
        ("air_pressure_bar", 4.1),
        ("spray_width_mm", 99.0),
        ("spray_width_mm", 145.0),
        ("filter_diff_pressure_bar", 0.48),
        ("filter_diff_pressure_bar", 0.72),
        ("film_thickness_um", 14.8),
        ("film_thickness_um", 17.8),
        ("paint_flow_ml_min", 107.0),
        ("servo_torque_load_pct", 58.9),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="SprayLine ontology TTL rule inference test.")
    parser.add_argument("--ttl", default="ontology/sprayline_threshold.ttl")
    parser.add_argument("--metric")
    parser.add_argument("--value", type=float)
    parser.add_argument("--run-smoke-test", action="store_true")
    args = parser.parse_args()

    if args.run_smoke_test:
        results = [infer_state(metric, value, args.ttl) for metric, value in smoke_cases()]
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return
    if not args.metric or args.value is None:
        parser.error("Use --metric and --value, or --run-smoke-test.")
    print(json.dumps(infer_state(args.metric, args.value, args.ttl), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
