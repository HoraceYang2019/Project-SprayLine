"""
past_service.py

Past Service Prototype v1.1

更新重點：
1. 欄位名稱沿用 v6。
2. sample_method 計算函式直接寫在 service 內。
3. Past state 使用 majority 表示歷史區間的主要狀態。
4. alarm_count / defect_count 使用 count 保留歷史異常次數，避免短暫異常被 majority 蓋掉。
"""

from datetime import datetime, timezone
from collections import Counter
import json


STATIONS = [
    {
        "station_id": "M1",
        "station_name_zh": "底漆站",
        "station_name_en": "Primer Station"
    },
    {
        "station_id": "M2",
        "station_name_zh": "面漆站",
        "station_name_en": "Topcoat Station"
    },
    {
        "station_id": "M3",
        "station_name_zh": "金漆站",
        "station_name_en": "Gold Paint Station"
    }
]


PAST_SAMPLE_METHOD = {
    # 狀態類：歷史區間內取出現次數最多的狀態
    "state": "majority",

    # metrics 類
    "metrics": {
        "pressure_bar": "mean",
        "flow_rate_ml_min": "mean",
        "quality_score_pct": "mean",
        "availability_pct": "mean",
        "clog_rate_pct": "mean",
        "maintainability_pct": "mean",

        # 新增：保留異常次數，避免短暫異常被 past state 的 majority 蓋掉
        "alarm_count": "count",
        "defect_count": "count",

        "risk_text": "latest_valid"
    },

    # process_parameters 類
    "process_parameters": {
        "temperature_c": "mean",
        "utilization_pct": "mean",
        "cycle_time_sec": "mean"
    }
}


def apply_sample_method(values, method, recent_n=5):
    """
    依照 sample_method 對資料進行計算。

    支援：
    - mean
    - latest_valid
    - majority
    - recent_average
    - max
    - min
    - count

    count 的設計：
    - 若 values 是布林值序列，count 會計算 True 的次數。
      例如 [False, True, False, True] -> 2
    - 若 values 是一般事件序列，count 會計算非 None 的筆數。
      例如 ["Alarm", None, "Alarm"] -> 2
    """

    if values is None:
        return None

    valid_values = [v for v in values if v is not None]

    if not valid_values:
        return None

    if method == "mean":
        numeric_values = [v for v in valid_values if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if not numeric_values:
            return None
        return sum(numeric_values) / len(numeric_values)

    if method == "latest_valid":
        return valid_values[-1]

    if method == "majority":
        return Counter(valid_values).most_common(1)[0][0]

    if method == "recent_average":
        numeric_values = [v for v in valid_values if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if not numeric_values:
            return None
        recent_values = numeric_values[-recent_n:]
        return sum(recent_values) / len(recent_values)

    if method == "max":
        numeric_values = [v for v in valid_values if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if not numeric_values:
            return None
        return max(numeric_values)

    if method == "min":
        numeric_values = [v for v in valid_values if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if not numeric_values:
            return None
        return min(numeric_values)

    if method == "count":
        # 布林資料：計算 True 次數，適合 alarm / defect flags
        if all(isinstance(v, bool) for v in valid_values):
            return sum(1 for v in valid_values if v is True)

        # 一般事件資料：計算有效事件筆數
        return len(valid_values)

    raise ValueError(f"Unsupported sample_method: {method}")


def build_past_service_input():
    """
    Past Service input 初版。
    range_variable / window / sample_method / target / stations 使用 v6 格式。
    """

    return {
        "service_name": "past_service",
        "schema_version": "v6-compatible",

        "range_variable": {
            "type": "history_range",
            "description": "Past Service 查詢的歷史範圍",
            "start": None,
            "end": None
        },

        "window": {
            "mode": "time_or_batch",
            "window_type": "2hour_or_10batch",
            "window_size": None
        },

        "sample_method": PAST_SAMPLE_METHOD,

        "target": [
            "state",
            "metrics",
            "process_parameters"
        ],

        "stations": STATIONS
    }


def build_empty_station_output(station):
    """
    建立單一站別的 Past Service output。
    目前所有待填資料先用 None，轉成 JSON 後會顯示 null。
    """

    return {
        "station_id": station["station_id"],
        "station_name_zh": station["station_name_zh"],
        "station_name_en": station["station_name_en"],

        "state": None,

        "metrics": {
            "pressure_bar": None,
            "flow_rate_ml_min": None,
            "quality_score_pct": None,
            "availability_pct": None,
            "clog_rate_pct": None,
            "maintainability_pct": None,
            "alarm_count": None,
            "defect_count": None,
            "risk_text": None
        },

        "process_parameters": {
            "temperature_c": None,
            "utilization_pct": None,
            "cycle_time_sec": None
        }
    }


def calculate_station_output(station, raw_data):
    """
    根據 raw_data 與 PAST_SAMPLE_METHOD 產生單一站別 output。

    raw_data 格式範例：
    {
        "state": ["Running", "Running", "Alarm"],
        "metrics": {
            "pressure_bar": [2.1, 2.2, 2.0],
            "alarm_count": [False, False, True],
            "defect_count": [False, True, False]
        },
        "process_parameters": {
            "temperature_c": [26.1, 26.2],
            "cycle_time_sec": [48.0, 49.0]
        }
    }

    初版若 raw_data 為 None，會輸出 null 欄位。
    """

    output = build_empty_station_output(station)

    if raw_data is None:
        return output

    output["state"] = apply_sample_method(
        raw_data.get("state"),
        PAST_SAMPLE_METHOD["state"]
    )

    for field_name, method in PAST_SAMPLE_METHOD["metrics"].items():
        output["metrics"][field_name] = apply_sample_method(
            raw_data.get("metrics", {}).get(field_name),
            method
        )

    for field_name, method in PAST_SAMPLE_METHOD["process_parameters"].items():
        output["process_parameters"][field_name] = apply_sample_method(
            raw_data.get("process_parameters", {}).get(field_name),
            method
        )

    return output


def build_past_service_output(raw_dataset=None):
    """
    Past Service output 初版。

    Parameters
    ----------
    raw_dataset : dict or None
        依 station_id 儲存的原始歷史資料。
        若為 None，所有數值欄位維持 null。
    """

    if raw_dataset is None:
        raw_dataset = {}

    return {
        "service_name": "past_service",
        "schema_version": "v6-compatible",
        "generated_at": datetime.now(timezone.utc).isoformat(),

        "window": {
            "window_id": None,
            "mode": "time_or_batch",
            "window_type": "2hour_or_10batch",
            "window_start": None,
            "window_end": None,
            "display_label": "past window"
        },

        "sample_method": PAST_SAMPLE_METHOD,

        "stations": [
            calculate_station_output(
                station,
                raw_dataset.get(station["station_id"])
            )
            for station in STATIONS
        ],

        "notes": [
            "Past Service 主要提供歷史視窗內的站別狀態、metrics 與 process_parameters。",
            "Past state 使用 majority 表示該歷史區間的主要狀態。",
            "alarm_count / defect_count 使用 count 保留異常次數，避免短暫異常被 majority 蓋掉。",
            "目前若未傳入 raw_dataset，數值欄位會維持 null。",
            "sample_method 計算函式目前直接寫在 past_service.py 中。"
        ]
    }


if __name__ == "__main__":
    print("=== Past Service Input ===")
    print(json.dumps(build_past_service_input(), ensure_ascii=False, indent=2))

    print("\n=== Past Service Output with null placeholders ===")
    print(json.dumps(build_past_service_output(), ensure_ascii=False, indent=2))

    print("\n=== Past Service Demo with alarm_count / defect_count ===")
    demo_raw_dataset = {
        "M1": {
            "state": ["Running", "Running", "Alarm", "Running"],
            "metrics": {
                "pressure_bar": [2.1, 2.2, 2.0, 2.1],
                "flow_rate_ml_min": [15.0, 15.2, 14.9, 15.1],
                "quality_score_pct": [97.0, 96.8, 95.5, 96.9],
                "availability_pct": [90.0, 92.0, 91.0, 93.0],
                "clog_rate_pct": [1.0, 1.2, 3.0, 1.1],
                "maintainability_pct": [85.0, 85.5, 84.0, 85.2],
                "alarm_count": [False, False, True, False],
                "defect_count": [False, True, False, False],
                "risk_text": ["Low", "Low", "Medium", "Low"]
            },
            "process_parameters": {
                "temperature_c": [26.1, 26.2, 26.5, 26.3],
                "utilization_pct": [88.0, 88.5, 87.0, 88.2],
                "cycle_time_sec": [48.0, 49.0, 50.0, 48.5]
            }
        }
    }
    print(json.dumps(build_past_service_output(demo_raw_dataset), ensure_ascii=False, indent=2))
