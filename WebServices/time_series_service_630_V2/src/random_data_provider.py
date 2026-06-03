from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any, Dict, List


LINE_CONFIG = {
    "line_1": {
        "station_name_zh": "底漆站",
        "station_name_en": "Primer Station",
        "recipe_name": "Primer_A",
        "pressure_range": (2.2, 2.8),
        "flow_range": (112, 124),
        "nominal_flow_rate_ml_min": 120,
        "spray_width_target_mm": 52,
        "spray_width_range": (49, 55),
        "temperature_range": (26.5, 29.0),
        "ok_rate_range": (0.92, 0.99),
    },
    "line_2": {
        "station_name_zh": "面漆站",
        "station_name_en": "Topcoat Station",
        "recipe_name": "Topcoat_B",
        "pressure_range": (1.8, 2.4),
        "flow_range": (94, 112),
        "nominal_flow_rate_ml_min": 110,
        "spray_width_target_mm": 52,
        "spray_width_range": (47, 56),
        "temperature_range": (26.0, 28.5),
        "ok_rate_range": (0.86, 0.96),
    },
    "line_3": {
        "station_name_zh": "金漆站",
        "station_name_en": "Gold Paint Station",
        "recipe_name": "Gold_C",
        "pressure_range": (1.4, 2.1),
        "flow_range": (74, 105),
        "nominal_flow_rate_ml_min": 120,
        "spray_width_target_mm": 52,
        "spray_width_range": (40, 56),
        "temperature_range": (25.5, 28.0),
        "ok_rate_range": (0.78, 0.93),
    },
}


def BuildRandomSeries(low: float, high: float, count: int, digits: int = 2) -> List[float]:
    return [
        round(random.uniform(low, high), digits)
        for _ in range(count)
    ]


def BuildRandomBoolSeries(probability_true: float, count: int) -> List[bool]:
    return [
        random.random() < probability_true
        for _ in range(count)
    ]


def BuildLineRawData(config: Dict[str, Any], sample_count: int) -> Dict[str, Any]:
    pressure_low, pressure_high = config["pressure_range"]
    flow_low, flow_high = config["flow_range"]
    width_low, width_high = config["spray_width_range"]
    temp_low, temp_high = config["temperature_range"]
    ok_rate_low, ok_rate_high = config["ok_rate_range"]

    nominal_flow = config["nominal_flow_rate_ml_min"]
    target_width = config["spray_width_target_mm"]

    running_time_sec = random.randint(2000, 3400)
    total_window_time_sec = 3600

    available_time_sec = random.randint(2500, 3600)
    planned_time_sec = 3600

    part_start_time = random.randint(0, 20)
    part_end_time = part_start_time + random.randint(38, 70)

    total_count = random.randint(80, 130)
    ok_rate = random.uniform(ok_rate_low, ok_rate_high)
    ok_count = int(total_count * ok_rate)

    defect_probability = max(0.01, min(0.30, 1.0 - ok_rate))

    nozzle_usage_time_hr = random.randint(20, 420)
    nozzle_life_hr = random.randint(420, 700)
    nozzle_rul_hr = max(10, nozzle_life_hr - nozzle_usage_time_hr)

    filter_usage_time_hr = random.randint(20, 520)
    filter_life_hr = random.randint(480, 800)
    filter_rul_hr = max(10, filter_life_hr - filter_usage_time_hr)

    in_flow_base = max(flow_high + random.uniform(2, 12), nominal_flow * random.uniform(0.95, 1.10))
    out_flow_low = max(0, in_flow_base * random.uniform(0.60, 0.98))
    out_flow_high = min(in_flow_base, in_flow_base * random.uniform(0.82, 1.00))

    return {
        "raw_parameters": {
            "pressure_bar": BuildRandomSeries(pressure_low, pressure_high, sample_count),
            "flow_rate_ml_min": BuildRandomSeries(flow_low, flow_high, sample_count),
            "nominal_flow_rate_ml_min": [nominal_flow],

            "spray_width_mm": BuildRandomSeries(width_low, width_high, sample_count),
            "target_spray_width_mm": [target_width],
            "target_min_mm": [48],
            "target_max_mm": [56],

            "in_flow_ml_min": BuildRandomSeries(in_flow_base * 0.96, in_flow_base * 1.04, sample_count),
            "out_flow_ml_min": BuildRandomSeries(out_flow_low, out_flow_high, sample_count),

            "nozzle_usage_time_hr": [nozzle_usage_time_hr],
            "nozzle_rul_hr": [nozzle_rul_hr],
            "filter_usage_time_hr": [filter_usage_time_hr],
            "filter_rul_hr": [filter_rul_hr],

            "temperature_c": BuildRandomSeries(temp_low, temp_high, sample_count),
            "recipe_name": [config["recipe_name"]],

            "running_time_sec": [running_time_sec],
            "total_window_time_sec": [total_window_time_sec],
            "available_time_sec": [available_time_sec],
            "planned_time_sec": [planned_time_sec],

            "part_start_time": [part_start_time],
            "part_end_time": [part_end_time],

            "ok_count": [ok_count],
            "total_count": [total_count],
            "defect": BuildRandomBoolSeries(defect_probability, sample_count),
        }
    }


def BuildRandomRawDataset(
    time_type: str = "current",
    sample_count: int | None = None,
    seed: int | None = None,
) -> Dict[str, Any]:
    """
    建立隨機 raw dataset。

    Parameters
    ----------
    time_type:
        past / current / future。
        這裡會影響 sample_count 的預設值。
    sample_count:
        每個欄位要產生幾筆資料。
    seed:
        若需要重現同一份資料，可以指定 seed。
        若為 None，每次呼叫都會產生不同資料。
    """

    if seed is not None:
        random.seed(seed)

    if sample_count is None:
        if time_type == "past":
            sample_count = 20
        elif time_type == "future":
            sample_count = 5
        else:
            sample_count = 8

    dataset = {}

    for line_id, config in LINE_CONFIG.items():
        dataset[line_id] = BuildLineRawData(
            config=config,
            sample_count=sample_count
        )

    dataset["_metadata"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_type": "random_raw_data",
        "time_type": time_type,
        "sample_count": sample_count,
        "seed": seed,
    }

    return dataset
