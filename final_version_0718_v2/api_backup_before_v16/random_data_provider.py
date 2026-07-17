from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any, Dict, List


LINE_CONFIG = {
    "line_1": {
        "station_id": "Station_1",
        "station_name_zh": "底漆站",
        "station_name_en": "Primer Station",
        "recipe_name": "Primer_A",
        "film_thickness_target_um": 25.0,
        "film_thickness_range": (23.8, 26.2),
        "paint_flow_range": (112, 124),
        "nominal_flow_rate_ml_min": 120,
        "air_pressure_range": (2.42, 2.58),
        "filter_diff_pressure_range": (0.18, 0.48),
        "spray_width_target_mm": 115,
        "spray_width_range": (108, 122),
        "temperature_range": (24.0, 29.5),
        "humidity_range": (48.0, 62.0),
        "servo_torque_range": (42, 58),
        "path_error_range": (0.02, 0.09),
        "ok_rate_range": (0.92, 0.99),
    },
    "line_2": {
        "station_id": "Station_2",
        "station_name_zh": "面漆站",
        "station_name_en": "Topcoat Station",
        "recipe_name": "Topcoat_B",
        "film_thickness_target_um": 25.0,
        "film_thickness_range": (22.8, 27.0),
        "paint_flow_range": (101, 117),
        "nominal_flow_rate_ml_min": 120,
        "air_pressure_range": (2.34, 2.66),
        "filter_diff_pressure_range": (0.25, 0.62),
        "spray_width_target_mm": 115,
        "spray_width_range": (100, 120),
        "temperature_range": (25.0, 31.8),
        "humidity_range": (42.0, 68.0),
        "servo_torque_range": (48, 66),
        "path_error_range": (0.05, 0.13),
        "ok_rate_range": (0.86, 0.96),
    },
    "line_3": {
        "station_id": "Station_3",
        "station_name_zh": "金漆站",
        "station_name_en": "Gold Paint Station",
        "recipe_name": "Gold_C",
        "film_thickness_target_um": 25.0,
        "film_thickness_range": (21.5, 28.0),
        "paint_flow_range": (88, 112),
        "nominal_flow_rate_ml_min": 120,
        "air_pressure_range": (2.20, 2.74),
        "filter_diff_pressure_range": (0.32, 0.82),
        "spray_width_target_mm": 115,
        "spray_width_range": (90, 121),
        "temperature_range": (24.0, 34.0),
        "humidity_range": (34.0, 72.0),
        "servo_torque_range": (54, 78),
        "path_error_range": (0.07, 0.18),
        "ok_rate_range": (0.78, 0.93),
    },
}


def BuildRandomSeries(low: float, high: float, count: int, digits: int = 2) -> List[float]:
    return [round(random.uniform(low, high), digits) for _ in range(count)]


def BuildRandomBoolSeries(probability_true: float, count: int) -> List[bool]:
    return [random.random() < probability_true for _ in range(count)]


def BuildLineRawData(line_id: str, config: Dict[str, Any], sample_count: int) -> Dict[str, Any]:
    paint_flow_low, paint_flow_high = config["paint_flow_range"]
    air_pressure_low, air_pressure_high = config["air_pressure_range"]
    filter_diff_low, filter_diff_high = config["filter_diff_pressure_range"]
    width_low, width_high = config["spray_width_range"]
    temp_low, temp_high = config["temperature_range"]
    humidity_low, humidity_high = config["humidity_range"]
    torque_low, torque_high = config["servo_torque_range"]
    path_error_low, path_error_high = config["path_error_range"]
    thickness_low, thickness_high = config["film_thickness_range"]
    ok_rate_low, ok_rate_high = config["ok_rate_range"]

    nominal_flow = config["nominal_flow_rate_ml_min"]
    target_width = config["spray_width_target_mm"]
    target_thickness = config["film_thickness_target_um"]

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

    # Use formal Shaoyu contract names as the main payload.
    paint_flow_series = BuildRandomSeries(paint_flow_low, paint_flow_high, sample_count)
    air_pressure_series = BuildRandomSeries(air_pressure_low, air_pressure_high, sample_count)
    filter_diff_series = BuildRandomSeries(filter_diff_low, filter_diff_high, sample_count)
    filter_inflow_series = BuildRandomSeries(max(paint_flow_high, nominal_flow) * 0.98, max(paint_flow_high, nominal_flow) * 1.05, sample_count)
    # outflow is roughly inflow minus pressure/contamination related loss.
    filter_outflow_series = [
        round(max(0, inflow * random.uniform(0.88, 0.99) - diff * random.uniform(1.0, 3.0)), 2)
        for inflow, diff in zip(filter_inflow_series, filter_diff_series)
    ]

    raw_parameters = {
        "line_id": [line_id],
        "station_id": [config["station_id"]],
        "batch_id": [f"BATCH_{config['station_id']}_DEMO"],
        "timestamp": [datetime.now(timezone.utc).isoformat()],
        "data_quality_flag": ["normal"],

        # Quality module
        "film_thickness_um": BuildRandomSeries(thickness_low, thickness_high, sample_count),
        "target_film_thickness_um": [target_thickness],

        # Nozzle
        "paint_flow_ml_min": paint_flow_series,
        "flow_rate_ml_min": paint_flow_series,  # backward-compatible alias
        "nominal_flow_rate_ml_min": [nominal_flow],
        "nozzle_roll": BuildRandomSeries(-1.5, 1.5, sample_count),
        "nozzle_usage_time_hr": [nozzle_usage_time_hr],
        "nozzle_rul_hr": [nozzle_rul_hr],

        # Filter mesh
        "filter_diff_pressure_bar": filter_diff_series,
        "filter_inflow_ml_min": filter_inflow_series,
        "filter_outflow_ml_min": filter_outflow_series,
        "in_flow_ml_min": filter_inflow_series,  # backward-compatible alias
        "out_flow_ml_min": filter_outflow_series,  # backward-compatible alias
        "filter_usage_time_hr": [filter_usage_time_hr],
        "filter_rul_hr": [filter_rul_hr],

        # Pump / air / spray width
        "pump_current_a": BuildRandomSeries(1.45, 2.35, sample_count),
        "air_pressure_bar": air_pressure_series,
        "pressure_bar": air_pressure_series,  # backward-compatible alias
        "spray_width_mm": BuildRandomSeries(width_low, width_high, sample_count),
        "target_spray_width_mm": [target_width],
        "target_min_mm": [105],
        "target_max_mm": [125],

        # Robot arm
        "servo_torque_load_pct": BuildRandomSeries(torque_low, torque_high, sample_count),
        "path_error_mm": BuildRandomSeries(path_error_low, path_error_high, sample_count, digits=3),
        "vibration_g": BuildRandomSeries(0.01, 0.08, sample_count, digits=3),
        "tcp_x_mm": BuildRandomSeries(95, 105, sample_count),
        "tcp_y_mm": BuildRandomSeries(45, 55, sample_count),
        "tcp_z_mm": BuildRandomSeries(295, 305, sample_count),
        "speed_mm_s": BuildRandomSeries(220, 280, sample_count),
        "gearbox_temperature_c": BuildRandomSeries(34, 48, sample_count),

        # Environment
        "temperature_c": BuildRandomSeries(temp_low, temp_high, sample_count),
        "humidity_rh": BuildRandomSeries(humidity_low, humidity_high, sample_count),
        "recipe_name": [config["recipe_name"]],

        # Production metrics
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

    return {"raw_parameters": raw_parameters}


def BuildRandomRawDataset(
    time_type: str = "current",
    sample_count: int | None = None,
    seed: int | None = None,
) -> Dict[str, Any]:
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
        dataset[line_id] = BuildLineRawData(line_id=line_id, config=config, sample_count=sample_count)

    dataset["_metadata"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_type": "random_raw_data_shaoyu_aligned",
        "time_type": time_type,
        "sample_count": sample_count,
        "seed": seed,
        "field_contract": "Shaoyu 0614 station_sensor_mapping.csv",
        "rule_source": "config/rules/sensor_thresholds.json",
    }
    return dataset
