
from collections import Counter
from datetime import datetime, timezone
import json


class TimeSeriesService:
    """TimeSeriesService：只負責計算數值，不負責 Rule 判斷。"""

    def __init__(self):
        self.lines = [
            {"line_id": "M1", "station_name_zh": "底漆站", "station_name_en": "Primer Station"},
            {"line_id": "M2", "station_name_zh": "面漆站", "station_name_en": "Topcoat Station"},
            {"line_id": "M3", "station_name_zh": "金漆站", "station_name_en": "Gold Paint Station"},
        ]

    def HandleTimeSeriesQuery(self, request):
        """UI / Integration Service 呼叫的主 function。"""
        time_type = self.DetermineTimeType(request)
        sample_method = self.GetSampleMethod(time_type)
        raw_dataset = self.QueryData(request, time_type)
        stations = []
        for line in self.ResolveLineScope(request):
            raw_line_data = raw_dataset.get(line["line_id"], {})
            sampled_data = self.ApplySampleMethods(raw_line_data, sample_method)
            calculated_data = self.CalculateLineMetrics(sampled_data)
            stations.append(self.BuildLineOutput(line, calculated_data))
        return self.BuildOutput(request, time_type, stations)

    def DetermineTimeType(self, request):
        """slider_value < 0: past；=0: current；>0: future。"""
        slider_value = request.get("slider_value", 0)
        if slider_value < 0:
            return "past"
        if slider_value == 0:
            return "current"
        return "future"

    def ResolveLineScope(self, request):
        line_scope = request.get("line_scope", "all")
        if line_scope == "all":
            return self.lines
        if isinstance(line_scope, str):
            return [line for line in self.lines if line["line_id"] == line_scope]
        if isinstance(line_scope, list):
            return [line for line in self.lines if line["line_id"] in line_scope]
        return self.lines

    def BuildViewerState(self, request, time_type):
        slider_value = request.get("slider_value", 0)
        if time_type == "past":
            display_label = f"past {abs(slider_value)}"
        elif time_type == "current":
            display_label = "current"
        else:
            display_label = f"future {slider_value}"
        return {
            "mode": request.get("mode", "time"),
            "window_type": request.get("window_type", "current"),
            "slider_value": slider_value,
            "display_label": display_label,
            "time_type": time_type,
            "is_history": time_type == "past",
            "is_current": time_type == "current",
            "is_future": time_type == "future",
        }

    def QueryData(self, request, time_type):
        """正式版請在這裡接 DB / API / MQTT / OPC UA / Prediction Service。"""
        return {}

    def GetSampleMethod(self, time_type):
        if time_type == "past":
            numeric_method = "mean"
        elif time_type == "current":
            numeric_method = "recent_average"
        else:
            numeric_method = "latest_valid"
        return {
            "raw_parameters": {
                "spray_pressure_bar": numeric_method,
                "spray_flow_rate_ml_min": numeric_method,
                "nominal_flow_rate_ml_min": "latest_valid",
                "spray_width_mm": numeric_method,
                "target_spray_width_mm": "latest_valid",
                "target_min_mm": "latest_valid",
                "target_max_mm": "latest_valid",
                "in_flow_ml_min": numeric_method,
                "out_flow_ml_min": numeric_method,
                "nozzle_usage_time_hr": "latest_valid",
                "nozzle_rul_hr": "latest_valid",
                "filter_usage_time_hr": "latest_valid",
                "filter_rul_hr": "latest_valid",
                "temperature_c": numeric_method,
                "recipe_name": "latest_valid",
                "running_time_sec": "latest_valid",
                "total_window_time_sec": "latest_valid",
                "available_time_sec": "latest_valid",
                "planned_time_sec": "latest_valid",
                "part_start_time": "latest_valid",
                "part_end_time": "latest_valid",
                "ok_count": "latest_valid",
                "total_count": "latest_valid",
                "defect": "count",
            }
        }

    def ApplySampleMethods(self, raw_line_data, sample_method):
        raw_parameters = raw_line_data.get("raw_parameters", {})
        methods = sample_method.get("raw_parameters", {})
        return {"raw_parameters": {k: self.ApplySampleMethod(raw_parameters.get(k), m) for k, m in methods.items()}}

    def ApplySampleMethod(self, values, method, recent_n=5):
        if values is None:
            return None
        if not isinstance(values, list):
            values = [values]
        valid = [v for v in values if v is not None]
        if not valid:
            return None
        if method == "mean":
            nums = self.GetNumericValues(valid)
            return sum(nums) / len(nums) if nums else None
        if method == "recent_average":
            nums = self.GetNumericValues(valid)
            nums = nums[-recent_n:]
            return sum(nums) / len(nums) if nums else None
        if method == "latest_valid":
            return valid[-1]
        if method == "majority":
            return Counter(valid).most_common(1)[0][0]
        if method == "count":
            if all(isinstance(v, bool) for v in valid):
                return sum(1 for v in valid if v is True)
            return len(valid)
        if method == "max":
            nums = self.GetNumericValues(valid)
            return max(nums) if nums else None
        if method == "min":
            nums = self.GetNumericValues(valid)
            return min(nums) if nums else None
        raise ValueError(f"Unsupported sample_method: {method}")

    def GetNumericValues(self, values):
        return [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]

    def IsValidNumber(self, value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def CalculateNozzleMetrics(self, p):
        return {
            "pressure_bar": p.get("spray_pressure_bar"),
            "flow_rate_ml_min": p.get("spray_flow_rate_ml_min"),
            "nozzle_clog_rate_pct": self.CalculateClogRateFromNominalFlow(p.get("spray_flow_rate_ml_min"), p.get("nominal_flow_rate_ml_min")),
            "nozzle_maintainability_pct": self.CalculateMaintainabilityPct(p.get("nozzle_rul_hr"), p.get("nozzle_usage_time_hr")),
        }

    def CalculateFilterMetrics(self, p):
        flow_loss_pct = self.CalculateFlowLossPct(p.get("in_flow_ml_min"), p.get("out_flow_ml_min"))
        return {
            "flow_loss_pct": flow_loss_pct,
            "filter_clog_rate_pct": flow_loss_pct,
            "filter_maintainability_pct": self.CalculateMaintainabilityPct(p.get("filter_rul_hr"), p.get("filter_usage_time_hr")),
        }

    def CalculateSprayWidthMetrics(self, p):
        spray_width = p.get("spray_width_mm")
        target_width = p.get("target_spray_width_mm")
        width_error_mm = None
        width_error_pct = None
        coverage_score_pct = None
        if self.IsValidNumber(spray_width) and self.IsValidNumber(target_width) and target_width != 0:
            width_error_mm = spray_width - target_width
            width_error_pct = abs(spray_width - target_width) / target_width * 100
            coverage_score_pct = max(0, 100 - width_error_pct)
        return {
            "spray_width_mm": spray_width,
            "width_error_mm": width_error_mm,
            "width_error_pct": width_error_pct,
            "coverage_score_pct": coverage_score_pct,
            "target_min_mm": p.get("target_min_mm"),
            "target_max_mm": p.get("target_max_mm"),
        }

    def CalculateLineMetrics(self, sampled_data):
        p = sampled_data.get("raw_parameters", {})
        nozzle = self.CalculateNozzleMetrics(p)
        filter_mesh = self.CalculateFilterMetrics(p)
        spray_width = self.CalculateSprayWidthMetrics(p)
        return {
            "component_metrics": {
                "nozzle": nozzle,
                "filter_mesh": filter_mesh,
                "spray_width": spray_width,
            },
            "metrics": {
                "availability_pct": self.CalculateAvailabilityPct(p.get("available_time_sec"), p.get("planned_time_sec")),
                "clog_rate_pct": self.CalculateLineClogRate(nozzle.get("nozzle_clog_rate_pct"), filter_mesh.get("filter_clog_rate_pct")),
                "pressure_bar": nozzle.get("pressure_bar"),
                "flow_rate_ml_min": nozzle.get("flow_rate_ml_min"),
                "maintainability_pct": self.CalculateLineMaintainability(nozzle.get("nozzle_maintainability_pct"), filter_mesh.get("filter_maintainability_pct")),
                "quality_score_pct": self.CalculateQualityScorePct(spray_width.get("coverage_score_pct"), p.get("ok_count"), p.get("total_count"), p.get("defect")),
                "risk_text": None,
                "spray_width_mm": spray_width.get("spray_width_mm"),
            },
            "process_parameters": {
                "recipe_name": p.get("recipe_name"),
                "temperature_c": p.get("temperature_c"),
                "utilization_pct": self.CalculateUtilizationPct(p.get("running_time_sec"), p.get("total_window_time_sec")),
                "cycle_time_sec": self.CalculateCycleTimeSec(p.get("part_start_time"), p.get("part_end_time")),
            },
            "spray_width_image": {
                "spray_width_mm": spray_width.get("spray_width_mm"),
                "target_min_mm": spray_width.get("target_min_mm"),
                "target_max_mm": spray_width.get("target_max_mm"),
                "status": None,
                "image_ref": None,
                "note": None,
            },
        }

    def CalculateClogRateFromNominalFlow(self, actual_flow_rate, nominal_flow_rate):
        if not self.IsValidNumber(actual_flow_rate):
            return None
        if not self.IsValidNumber(nominal_flow_rate) or nominal_flow_rate == 0:
            return None
        return max(0, (nominal_flow_rate - actual_flow_rate) / nominal_flow_rate * 100)

    def CalculateFlowLossPct(self, in_flow_ml_min, out_flow_ml_min):
        if not self.IsValidNumber(in_flow_ml_min) or in_flow_ml_min == 0:
            return None
        if not self.IsValidNumber(out_flow_ml_min):
            return None
        return max(0, (in_flow_ml_min - out_flow_ml_min) / in_flow_ml_min * 100)

    def CalculateMaintainabilityPct(self, rul_hr, usage_time_hr):
        if not self.IsValidNumber(rul_hr) or not self.IsValidNumber(usage_time_hr):
            return None
        total = rul_hr + usage_time_hr
        if total == 0:
            return None
        return rul_hr / total * 100

    def CalculateLineClogRate(self, nozzle_clog_rate_pct, filter_clog_rate_pct):
        values = [v for v in [nozzle_clog_rate_pct, filter_clog_rate_pct] if self.IsValidNumber(v)]
        return max(values) if values else None

    def CalculateLineMaintainability(self, nozzle_maintainability_pct, filter_maintainability_pct):
        values = [v for v in [nozzle_maintainability_pct, filter_maintainability_pct] if self.IsValidNumber(v)]
        return min(values) if values else None

    def CalculateQualityScorePct(self, coverage_score_pct, ok_count, total_count, defect_count):
        if self.IsValidNumber(ok_count) and self.IsValidNumber(total_count) and total_count != 0:
            return ok_count / total_count * 100
        if self.IsValidNumber(coverage_score_pct):
            return coverage_score_pct
        if self.IsValidNumber(defect_count) and defect_count > 0:
            return 0
        return None

    def CalculateUtilizationPct(self, running_time_sec, total_window_time_sec):
        if not self.IsValidNumber(running_time_sec):
            return None
        if not self.IsValidNumber(total_window_time_sec) or total_window_time_sec == 0:
            return None
        return running_time_sec / total_window_time_sec * 100

    def CalculateAvailabilityPct(self, available_time_sec, planned_time_sec):
        if not self.IsValidNumber(available_time_sec):
            return None
        if not self.IsValidNumber(planned_time_sec) or planned_time_sec == 0:
            return None
        return available_time_sec / planned_time_sec * 100

    def CalculateCycleTimeSec(self, part_start_time, part_end_time):
        if self.IsValidNumber(part_start_time) and self.IsValidNumber(part_end_time):
            return part_end_time - part_start_time
        return None

    def BuildLineOutput(self, line, calculated_data):
        return {
            "line_id": line.get("line_id"),
            "station_name_zh": line.get("station_name_zh"),
            "station_name_en": line.get("station_name_en"),
            "state": None,
            "component_overview": [],
            "metrics": calculated_data.get("metrics", {}),
            "process_parameters": calculated_data.get("process_parameters", {}),
            "component_metrics": calculated_data.get("component_metrics", {}),
            "fault_detail": [],
            "spray_width_image": calculated_data.get("spray_width_image", {}),
        }

    def BuildOutput(self, request, time_type, stations):
        return {
            "schema_version": "v1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "serviceName": "TimeSeriesService",
            "requestId": request.get("requestId"),
            "viewer_state": self.BuildViewerState(request, time_type),
            "summary": {
                "total_station_count": len(stations),
                "normal_count": None,
                "warning_count": None,
                "predict_risk_count": None,
            },
            "stations": stations,
            "calculation_info": {
                "pipeline": [
                    "HandleTimeSeriesQuery",
                    "DetermineTimeType",
                    "QueryData",
                    "ApplySampleMethods",
                    "CalculateLineMetrics",
                    "BuildOutput",
                ],
                "rule_stage": "external",
                "note": "This service calculates metric values only. Rule Service should decide state, risk_text, fault_detail, and component_overview.",
            },
        }


def BuildTimeSeriesRequestTemplate():
    return {
        "serviceName": "TimeSeriesService",
        "requestId": None,
        "mode": "time",
        "window_type": "current",
        "slider_value": 0,
        "line_scope": "all",
        "requested_metrics": [
            "availability_pct",
            "clog_rate_pct",
            "pressure_bar",
            "flow_rate_ml_min",
            "maintainability_pct",
            "quality_score_pct",
            "risk_text",
            "spray_width_mm",
            "recipe_name",
            "temperature_c",
            "utilization_pct",
            "cycle_time_sec",
        ],
    }


def BuildDemoRawDataset():
    return {
        "M1": {"raw_parameters": {"spray_pressure_bar": [2.4, 2.5, 2.6], "spray_flow_rate_ml_min": [118, 120, 119], "nominal_flow_rate_ml_min": [120], "spray_width_mm": [52, 53, 52], "target_spray_width_mm": [52], "target_min_mm": [48], "target_max_mm": [56], "in_flow_ml_min": [122, 121, 120], "out_flow_ml_min": [118, 119, 118], "nozzle_usage_time_hr": [80], "nozzle_rul_hr": [320], "filter_usage_time_hr": [100], "filter_rul_hr": [400], "temperature_c": [27.8, 28.0, 28.1], "recipe_name": ["Primer_A"], "running_time_sec": [2800], "total_window_time_sec": [3600], "available_time_sec": [3420], "planned_time_sec": [3600], "part_start_time": [10], "part_end_time": [52], "ok_count": [96], "total_count": [100], "defect": [False, False, False]}},
        "M2": {"raw_parameters": {"spray_pressure_bar": [2.0, 2.1, 2.0], "spray_flow_rate_ml_min": [98, 100, 99], "nominal_flow_rate_ml_min": [110], "spray_width_mm": [50, 49, 50], "target_spray_width_mm": [52], "target_min_mm": [48], "target_max_mm": [56], "in_flow_ml_min": [110, 108, 109], "out_flow_ml_min": [95, 96, 95], "nozzle_usage_time_hr": [180], "nozzle_rul_hr": [220], "filter_usage_time_hr": [250], "filter_rul_hr": [180], "temperature_c": [27.0, 27.1, 27.2], "recipe_name": ["Topcoat_B"], "running_time_sec": [2600], "total_window_time_sec": [3600], "available_time_sec": [3200], "planned_time_sec": [3600], "part_start_time": [5], "part_end_time": [51], "ok_count": [91], "total_count": [100], "defect": [False, True, False]}},
        "M3": {"raw_parameters": {"spray_pressure_bar": [1.6, 1.7, 1.6], "spray_flow_rate_ml_min": [80, 82, 81], "nominal_flow_rate_ml_min": [120], "spray_width_mm": [43, 42, 43], "target_spray_width_mm": [52], "target_min_mm": [48], "target_max_mm": [56], "in_flow_ml_min": [120, 120, 119], "out_flow_ml_min": [70, 68, 69], "nozzle_usage_time_hr": [300], "nozzle_rul_hr": [100], "filter_usage_time_hr": [400], "filter_rul_hr": [80], "temperature_c": [26.0, 26.1, 26.2], "recipe_name": ["Gold_C"], "running_time_sec": [2100], "total_window_time_sec": [3600], "available_time_sec": [2600], "planned_time_sec": [3600], "part_start_time": [8], "part_end_time": [63], "ok_count": [82], "total_count": [100], "defect": [True, False, True]}},
    }


class DemoTimeSeriesService(TimeSeriesService):
    def QueryData(self, request, time_type):
        return BuildDemoRawDataset()


if __name__ == "__main__":
    service = DemoTimeSeriesService()
    request = BuildTimeSeriesRequestTemplate()
    output = service.HandleTimeSeriesQuery(request)
    print(json.dumps(output, ensure_ascii=False, indent=2))
