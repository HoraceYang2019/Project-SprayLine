"""
current_service.py

Current Service Prototype v1.1

更新重點：
1. 欄位名稱沿用 v6。
2. sample_method 計算函式直接寫在 service 內。
3. Current state 使用 latest_valid 反映目前最新有效狀態。
4. alarm_count / defect_count 使用 count 保留目前視窗內的異常次數。
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


CURRENT_SAMPLE_METHOD = {
    # 狀態類：取最新有效狀態
    "state": "latest_valid",

    # metrics 類
    "metrics": {
        "pressure_bar": "recent_average",
        "flow_rate_ml_min": "recent_average",
        "quality_score_pct": "latest_valid",
        "availability_pct": "latest_valid",
        "clog_rate_pct": "latest_valid",
        "maintainability_pct": "latest_valid",

        # 新增：保留目前視窗內的異常次數
        "alarm_count": "count",
        "defect_count": "count",

        "risk_text": "latest_valid"
    },

    # process_parameters 類
    "process_parameters": {
        "temperature_c": "recent_average",
        "utilization_pct": "latest_valid",
        "cycle_time_sec": "latest_valid"
    }
}


def apply_sample_method(values, method, recent_n=5):
    """
    依照 sample_method 對資料進行計算。

    count 的設計：
    - 若 values 是布林值序列，count 會計算 True 的次數。
    - 若 values 是一般事件序列，count 會計算非 None 的筆數。
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
        if all(isinstance(v, bool) for v in valid_values):
            return sum(1 for v in valid_values if v is True)
        return len(valid_values)

    raise ValueError(f"Unsupported sample_method: {method}")


def build_current_service_input():
    """
    Current Service input 初版。
    window / sample_method / target / stations 使用 v6 格式。
    """

    return {
        "service_name": "current_service",
        "schema_version": "v6-compatible",

        "window": {
            "mode": "current",
            "window_type": "current_window",
            "window_size": None,
            "display_label": "current"
        },

        "sample_method": CURRENT_SAMPLE_METHOD,

        "target": [
            "state",
            "metrics",
            "process_parameters"
        ],

        "stations": STATIONS
    }


def build_empty_station_output(station):
    """
    建立單一站別的 Current Service output。
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


def calculate_station_output(station, raw_data, recent_n=5):
    """
    根據 raw_data 與 CURRENT_SAMPLE_METHOD 產生單一站別 output。

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
        CURRENT_SAMPLE_METHOD["state"],
        recent_n=recent_n
    )

    for field_name, method in CURRENT_SAMPLE_METHOD["metrics"].items():
        output["metrics"][field_name] = apply_sample_method(
            raw_data.get("metrics", {}).get(field_name),
            method,
            recent_n=recent_n
        )

    for field_name, method in CURRENT_SAMPLE_METHOD["process_parameters"].items():
        output["process_parameters"][field_name] = apply_sample_method(
            raw_data.get("process_parameters", {}).get(field_name),
            method,
            recent_n=recent_n
        )

    return output


def build_current_service_output(raw_dataset=None, recent_n=5):
    """
    Current Service output 初版。

    Parameters
    ----------
    raw_dataset : dict or None
        依 station_id 儲存的目前或近即時資料。
        若為 None，所有數值欄位維持 null。
    recent_n : int
        recent_average 使用的最近 N 筆資料數量。
    """

    if raw_dataset is None:
        raw_dataset = {}

    return {
        "service_name": "current_service",
        "schema_version": "v6-compatible",
        "generated_at": datetime.now(timezone.utc).isoformat(),

        "window": {
            "window_id": None,
            "mode": "current",
            "window_type": "current_window",
            "window_size": None,
            "display_label": "current"
        },

        "sample_method": CURRENT_SAMPLE_METHOD,

        "stations": [
            calculate_station_output(
                station,
                raw_dataset.get(station["station_id"]),
                recent_n=recent_n
            )
            for station in STATIONS
        ],

        "notes": [
            "Current Service 主要提供目前站別狀態、metrics 與 process_parameters。",
            "Current state 使用 latest_valid 反映目前最新有效狀態。",
            "alarm_count / defect_count 使用 count 保留目前視窗內的異常次數。",
            "pressure_bar、flow_rate_ml_min、temperature_c 建議用 recent_average，避免即時值跳動過大。",
            "目前若未傳入 raw_dataset，數值欄位會維持 null。"
        ]
    }


if __name__ == "__main__":
    print("=== Current Service Input ===")
    print(json.dumps(build_current_service_input(), ensure_ascii=False, indent=2))

    print("\n=== Current Service Output with null placeholders ===")
    print(json.dumps(build_current_service_output(), ensure_ascii=False, indent=2))

    print("\n=== Current Service Demo with alarm_count / defect_count ===")
    demo_raw_dataset = {
        "M1": {
            "state": ["Running", "Running", "Alarm"],
            "metrics": {
                "pressure_bar": [2.1, 2.2, 2.0],
                "flow_rate_ml_min": [15.0, 15.2, 14.9],
                "quality_score_pct": [97.0, 96.8, 95.5],
                "availability_pct": [90.0, 92.0, 91.0],
                "clog_rate_pct": [1.0, 1.2, 3.0],
                "maintainability_pct": [85.0, 85.5, 84.0],
                "alarm_count": [False, False, True],
                "defect_count": [False, True, False],
                "risk_text": ["Low", "Low", "Medium"]
            },
            "process_parameters": {
                "temperature_c": [26.1, 26.2, 26.5],
                "utilization_pct": [88.0, 88.5, 87.0],
                "cycle_time_sec": [48.0, 49.0, 50.0]
            }
        }
    }
    print(json.dumps(build_current_service_output(demo_raw_dataset), ensure_ascii=False, indent=2))
