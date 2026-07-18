from __future__ import annotations

import json
from pathlib import Path
from typing import Any


LEVEL_RANK = {"normal": 1, "warning": 2, "fault": 3}
UI_LEVEL = {"normal": "ok", "warning": "warn", "fault": "bad"}


class RulesService:
    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir
        self.threshold_path = config_dir / "sensor_thresholds.json"
        self.mapping_path = config_dir / "sensor_event_mapping.json"
        self.reference_path = config_dir / "local_ui_reference.json"
        self.thresholds = json.loads(self.threshold_path.read_text(encoding="utf-8"))
        self.mapping = json.loads(self.mapping_path.read_text(encoding="utf-8"))
        self.references = json.loads(self.reference_path.read_text(encoding="utf-8"))

    @staticmethod
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

    def classify(self, sensor_name: str, value: Any) -> str:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "warning"

        rule = self.thresholds.get("rules", {}).get(sensor_name)
        if not rule:
            rule = self.references.get(sensor_name)
        if not rule:
            # B版尚未提供門檻的欄位，不用它單獨拉高元件嚴重度。
            return "normal"
        if any(self._in_band(number, band) for band in rule.get("fault", [])):
            return "fault"
        if any(self._in_band(number, band) for band in rule.get("warning", [])):
            return "warning"
        if self._in_band(number, rule.get("normal", {})):
            return "normal"
        return "warning"

    def ui_level(self, state: str) -> str:
        return UI_LEVEL.get(state, "warn")

    def more_severe(self, states: list[str]) -> str:
        if not states:
            return "normal"
        return max(states, key=lambda item: LEVEL_RANK.get(item, 0))

    def sensor_mapping(self, sensor_name: str) -> dict[str, Any]:
        return self.mapping.get("sensor_mapping", {}).get(sensor_name, {})

    def rule(self, sensor_name: str) -> dict[str, Any] | None:
        return self.thresholds.get("rules", {}).get(sensor_name)

    def chart_reference(self, sensor_name: str) -> dict[str, Any] | None:
        rule = self.rule(sensor_name)
        if rule:
            return {
                "unit": rule.get("unit", ""),
                "normal": rule.get("normal"),
                "warning": rule.get("warning", []),
                "fault": rule.get("fault", []),
                "source": "少榆0616_B版 sensor_thresholds.json",
            }
        reference = self.references.get(sensor_name)
        if reference:
            return reference
        return None
