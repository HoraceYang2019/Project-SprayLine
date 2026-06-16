from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import json
import random

from random_data_provider import BuildRandomRawDataset
from event_rule_adapter import evaluate_station_rules
from d_integration_adapter import build_d_integration_payloads, flatten_d_payloads


class TimeSeriesService:
    """
    TimeSeriesService

    這份是隨機資料版本：
    - 不使用固定 raw_data_demo.json。
    - 不把假資料寫死在 service 裡。
    - raw data 由 random_data_provider.py 產生。
    - 正式整合時只要把 QueryRawDataFromDatabase() 改成真正 Database 查詢。
    """

    def __init__(self, processed_result_db_path: str | Path | None = None):
        self.lines = [
            {"line_id": "line_1", "station_name_zh": "底漆站", "station_name_en": "Primer Station"},
            {"line_id": "line_2", "station_name_zh": "面漆站", "station_name_en": "Topcoat Station"},
            {"line_id": "line_3", "station_name_zh": "金漆站", "station_name_en": "Gold Paint Station"},
        ]

        self.processed_result_db_path = Path(
            processed_result_db_path or "../data/runtime/processed_result_database_demo.json"
        )

        self.latest_output_json_path = self.processed_result_db_path.parent / "time_series_latest_output.json"

    def HandleTimeSeriesQuery(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        UI / Integration Service 呼叫的主 function。
        """

        self.ValidateRequest(request)

        time_type = self.DetermineTimeType(request)
        sample_method_name = self.GetSampleMethodName(time_type)
        sample_method = self.GetSampleMethod(time_type)

        raw_dataset = self.QueryRawDataFromDatabase(
            request=request,
            time_type=time_type
        )

        stations = []

        for line in self.ResolveLineScope(request):
            raw_line_data = raw_dataset.get(line["line_id"], {})

            sampled_data = self.ApplySampleMethods(
                raw_line_data=raw_line_data,
                sample_method=sample_method
            )

            calculated_data = self.CalculateLineMetrics(
                sampled_data=sampled_data,
                time_type=time_type,
                sample_method_name=sample_method_name
            )

            stations.append(
                self.BuildLineOutput(
                    line=line,
                    calculated_data=calculated_data
                )
            )

        output = self.BuildOutput(
            request=request,
            time_type=time_type,
            sample_method_name=sample_method_name,
            raw_dataset_metadata=raw_dataset.get("_metadata", {}),
            stations=stations
        )

        self.SaveProcessedResultToDatabase(output)
        self.SaveLatestOutputJson(output)
        self.SaveDIntegrationRuntimeOutputs(output)

        return output

    def ValidateRequest(self, request: Dict[str, Any]) -> None:
        required_fields = [
            "schema_version",
            "service_name",
            "mode",
            "window_type",
            "slider_value",
            "line_scope"
        ]

        missing_fields = [
            field for field in required_fields
            if field not in request
        ]

        if missing_fields:
            raise ValueError(f"request missing required fields: {missing_fields}")

        if request["service_name"] != "TimeSeriesService":
            raise ValueError("request['service_name'] must be 'TimeSeriesService'.")

        if not isinstance(request["slider_value"], (int, float)):
            raise ValueError("request['slider_value'] must be a number.")

    def DetermineTimeType(self, request: Dict[str, Any]) -> str:
        slider_value = request["slider_value"]

        if slider_value < 0:
            return "past"

        if slider_value == 0:
            return "current"

        return "future"

    def ResolveLineScope(self, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        line_scope = request["line_scope"]

        if line_scope == "all":
            return self.lines

        if isinstance(line_scope, str):
            selected_lines = [
                line for line in self.lines
                if line["line_id"] == line_scope
            ]

        elif isinstance(line_scope, list):
            selected_lines = [
                line for line in self.lines
                if line["line_id"] in line_scope
            ]

        else:
            raise ValueError("line_scope must be 'all', a line_id string, or a list of line_id.")

        if not selected_lines:
            raise ValueError(f"no matched line found for line_scope: {line_scope}")

        return selected_lines

    def QueryRawDataFromDatabase(self, request: Dict[str, Any], time_type: str) -> Dict[str, Any]:
        """
        Prototype 階段：
        使用 random_data_provider.py 隨機產生 raw data。

        正式整合時：
        這裡改成向真正 Database 查詢 raw data。
        """

        seed = request.get("random_seed")
        sample_count = request.get("sample_count")

        return BuildRandomRawDataset(
            time_type=time_type,
            sample_count=sample_count,
            seed=seed
        )

    def BuildViewerState(self, request: Dict[str, Any], time_type: str, sample_method_name: str | None = None) -> Dict[str, Any]:
        slider_value = request["slider_value"]

        if time_type == "past":
            display_label = f"past {abs(slider_value)}"
        elif time_type == "current":
            display_label = "current"
        else:
            display_label = f"future {slider_value}"

        return {
            "mode": request["mode"],
            "window_type": request["window_type"],
            "slider_value": slider_value,
            "display_label": display_label,
            "time_type": time_type,
            "sample_method": sample_method_name or self.GetSampleMethodName(time_type),
            "is_history": time_type == "past",
            "is_current": time_type == "current",
            "is_future": time_type == "future"
        }

    def GetSampleMethodName(self, time_type: str) -> str:
        if time_type == "past":
            return "mean"
        if time_type == "current":
            return "recent_average"
        if time_type == "future":
            return "latest_valid"
        raise ValueError(f"unsupported time_type: {time_type}")

    def GetSampleMethod(self, time_type: str) -> Dict[str, Any]:
        numeric_method = self.GetSampleMethodName(time_type)

        return {
            "raw_parameters": {
                "line_id": "latest_valid",
                "station_id": "latest_valid",
                "batch_id": "latest_valid",
                "timestamp": "latest_valid",
                "data_quality_flag": "latest_valid",

                # Quality module
                "film_thickness_um": numeric_method,
                "target_film_thickness_um": "latest_valid",

                # Nozzle
                "paint_flow_ml_min": numeric_method,
                "flow_rate_ml_min": numeric_method,
                "nominal_flow_rate_ml_min": "latest_valid",
                "nozzle_roll": numeric_method,
                "nozzle_usage_time_hr": "latest_valid",
                "nozzle_rul_hr": "latest_valid",

                # Filter mesh
                "filter_diff_pressure_bar": numeric_method,
                "filter_inflow_ml_min": numeric_method,
                "filter_outflow_ml_min": numeric_method,
                "in_flow_ml_min": numeric_method,
                "out_flow_ml_min": numeric_method,
                "filter_usage_time_hr": "latest_valid",
                "filter_rul_hr": "latest_valid",

                # Pump / air / spray width
                "pump_current_a": numeric_method,
                "air_pressure_bar": numeric_method,
                "pressure_bar": numeric_method,
                "spray_width_mm": numeric_method,
                "target_spray_width_mm": "latest_valid",
                "target_min_mm": "latest_valid",
                "target_max_mm": "latest_valid",

                # Robot arm
                "servo_torque_load_pct": numeric_method,
                "path_error_mm": numeric_method,
                "vibration_g": numeric_method,
                "tcp_x_mm": numeric_method,
                "tcp_y_mm": numeric_method,
                "tcp_z_mm": numeric_method,
                "speed_mm_s": numeric_method,
                "gearbox_temperature_c": numeric_method,

                # Environment / process
                "temperature_c": numeric_method,
                "humidity_rh": numeric_method,
                "recipe_name": "latest_valid",

                "running_time_sec": "latest_valid",
                "total_window_time_sec": "latest_valid",
                "available_time_sec": "latest_valid",
                "planned_time_sec": "latest_valid",

                "part_start_time": "latest_valid",
                "part_end_time": "latest_valid",

                "ok_count": "latest_valid",
                "total_count": "latest_valid",
                "defect": "count"
            }
        }

    def ApplySampleMethods(self, raw_line_data: Dict[str, Any], sample_method: Dict[str, Any]) -> Dict[str, Any]:
        raw_parameters = raw_line_data.get("raw_parameters", {})
        methods = sample_method.get("raw_parameters", {})

        sampled_parameters = {}

        for field_name, method in methods.items():
            sampled_parameters[field_name] = self.ApplySampleMethod(
                values=raw_parameters.get(field_name),
                method=method
            )

        return {"raw_parameters": sampled_parameters}

    def ApplySampleMethod(self, values: Any, method: str, recent_n: int = 5) -> Any:
        if values is None:
            return None

        if not isinstance(values, list):
            values = [values]

        valid_values = [value for value in values if value is not None]

        if not valid_values:
            return None

        if method == "mean":
            numeric_values = self.GetNumericValues(valid_values)
            return sum(numeric_values) / len(numeric_values) if numeric_values else None

        if method == "recent_average":
            numeric_values = self.GetNumericValues(valid_values)
            if not numeric_values:
                return None
            recent_values = numeric_values[-recent_n:]
            return sum(recent_values) / len(recent_values)

        if method == "latest_valid":
            return valid_values[-1]

        if method == "majority":
            return Counter(valid_values).most_common(1)[0][0]

        if method == "count":
            if all(isinstance(value, bool) for value in valid_values):
                return sum(1 for value in valid_values if value is True)
            return len(valid_values)

        if method == "max":
            numeric_values = self.GetNumericValues(valid_values)
            return max(numeric_values) if numeric_values else None

        if method == "min":
            numeric_values = self.GetNumericValues(valid_values)
            return min(numeric_values) if numeric_values else None

        raise ValueError(f"unsupported sample_method: {method}")

    def GetNumericValues(self, values: List[Any]) -> List[float]:
        return [
            value for value in values
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        ]

    def IsValidNumber(self, value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def CalculateQualityModuleMetrics(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        film_thickness = parameters.get("film_thickness_um")
        target_thickness = parameters.get("target_film_thickness_um")

        thickness_error_um = None
        thickness_error_pct = None
        if self.IsValidNumber(film_thickness) and self.IsValidNumber(target_thickness) and target_thickness != 0:
            thickness_error_um = film_thickness - target_thickness
            thickness_error_pct = abs(thickness_error_um) / target_thickness * 100

        return {
            "film_thickness_um": film_thickness,
            "target_film_thickness_um": target_thickness,
            "thickness_error_um": thickness_error_um,
            "thickness_error_pct": thickness_error_pct,
        }

    def CalculateNozzleMetrics(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        air_pressure_bar = parameters.get("air_pressure_bar", parameters.get("pressure_bar"))
        paint_flow = parameters.get("paint_flow_ml_min", parameters.get("flow_rate_ml_min"))
        nominal_flow = parameters.get("nominal_flow_rate_ml_min")
        nozzle_usage_time = parameters.get("nozzle_usage_time_hr")
        nozzle_rul = parameters.get("nozzle_rul_hr")

        return {
            "air_pressure_bar": air_pressure_bar,
            "pressure_bar": air_pressure_bar,
            "paint_flow_ml_min": paint_flow,
            "flow_rate_ml_min": paint_flow,
            "nominal_flow_rate_ml_min": nominal_flow,
            "nozzle_roll": parameters.get("nozzle_roll"),
            "nozzle_clog_rate_pct": self.CalculateClogRateFromNominalFlow(
                actual_flow_rate=paint_flow,
                nominal_flow_rate=nominal_flow
            ),
            "nozzle_maintainability_pct": self.CalculateMaintainabilityPct(
                rul_hr=nozzle_rul,
                usage_time_hr=nozzle_usage_time
            )
        }

    def CalculateFilterMetrics(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        in_flow = parameters.get("filter_inflow_ml_min", parameters.get("in_flow_ml_min"))
        out_flow = parameters.get("filter_outflow_ml_min", parameters.get("out_flow_ml_min"))
        filter_usage_time = parameters.get("filter_usage_time_hr")
        filter_rul = parameters.get("filter_rul_hr")

        flow_loss_pct = self.CalculateFlowLossPct(
            in_flow_ml_min=in_flow,
            out_flow_ml_min=out_flow
        )

        return {
            "filter_diff_pressure_bar": parameters.get("filter_diff_pressure_bar"),
            "filter_inflow_ml_min": in_flow,
            "filter_outflow_ml_min": out_flow,
            "flow_loss_pct": flow_loss_pct,
            "filter_clog_rate_pct": flow_loss_pct,
            "filter_maintainability_pct": self.CalculateMaintainabilityPct(
                rul_hr=filter_rul,
                usage_time_hr=filter_usage_time
            )
        }

    def CalculatePumpUnitMetrics(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "pump_current_a": parameters.get("pump_current_a")
        }

    def CalculateAirCompressorMetrics(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        air_pressure = parameters.get("air_pressure_bar", parameters.get("pressure_bar"))
        target_pressure = 2.5
        pressure_error_bar = None
        pressure_error_pct = None

        if self.IsValidNumber(air_pressure) and target_pressure != 0:
            pressure_error_bar = air_pressure - target_pressure
            pressure_error_pct = abs(pressure_error_bar) / target_pressure * 100

        return {
            "air_pressure_bar": air_pressure,
            "target_air_pressure_bar": target_pressure,
            "pressure_error_bar": pressure_error_bar,
            "pressure_error_pct": pressure_error_pct,
        }

    def CalculateSprayWidthMetrics(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        spray_width = parameters.get("spray_width_mm")
        target_width = parameters.get("target_spray_width_mm")
        target_min = parameters.get("target_min_mm")
        target_max = parameters.get("target_max_mm")

        width_error_mm = None
        width_error_pct = None
        coverage_score_pct = None

        if (
            self.IsValidNumber(spray_width)
            and self.IsValidNumber(target_width)
            and target_width != 0
        ):
            width_error_mm = spray_width - target_width
            width_error_pct = abs(spray_width - target_width) / target_width * 100
            coverage_score_pct = max(0, 100 - width_error_pct)

        return {
            "spray_width_mm": spray_width,
            "target_spray_width_mm": target_width,
            "width_error_mm": width_error_mm,
            "width_error_pct": width_error_pct,
            "coverage_score_pct": coverage_score_pct,
            "target_min_mm": target_min,
            "target_max_mm": target_max
        }

    def CalculateRobotArmMetrics(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "servo_torque_load_pct": parameters.get("servo_torque_load_pct"),
            "path_error_mm": parameters.get("path_error_mm"),
            "vibration_g": parameters.get("vibration_g"),
            "tcp_position_mm": {
                "x": parameters.get("tcp_x_mm"),
                "y": parameters.get("tcp_y_mm"),
                "z": parameters.get("tcp_z_mm"),
            },
            "speed_mm_s": parameters.get("speed_mm_s"),
            "gearbox_temperature_c": parameters.get("gearbox_temperature_c"),
        }

    def CalculateEnvironmentMetrics(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "temperature_c": parameters.get("temperature_c"),
            "humidity_rh": parameters.get("humidity_rh"),
        }

    def BuildSensorPayloadForRule(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        sensor_names = [
            "film_thickness_um",
            "paint_flow_ml_min",
            "nozzle_roll",
            "filter_diff_pressure_bar",
            "filter_inflow_ml_min",
            "filter_outflow_ml_min",
            "pump_current_a",
            "air_pressure_bar",
            "spray_width_mm",
            "servo_torque_load_pct",
            "path_error_mm",
            "vibration_g",
            "tcp_x_mm",
            "tcp_y_mm",
            "tcp_z_mm",
            "speed_mm_s",
            "gearbox_temperature_c",
            "temperature_c",
            "humidity_rh",
        ]

        return {
            sensor_name: parameters.get(sensor_name)
            for sensor_name in sensor_names
            if parameters.get(sensor_name) is not None
        }

    def CalculateLineMetrics(self, sampled_data: Dict[str, Any], time_type: str = "current", sample_method_name: str = "recent_average") -> Dict[str, Any]:
        parameters = sampled_data.get("raw_parameters", {})

        quality_module_metrics = self.CalculateQualityModuleMetrics(parameters)
        nozzle_metrics = self.CalculateNozzleMetrics(parameters)
        filter_metrics = self.CalculateFilterMetrics(parameters)
        pump_unit_metrics = self.CalculatePumpUnitMetrics(parameters)
        air_compressor_metrics = self.CalculateAirCompressorMetrics(parameters)
        spray_width_metrics = self.CalculateSprayWidthMetrics(parameters)
        robot_arm_metrics = self.CalculateRobotArmMetrics(parameters)
        environment_metrics = self.CalculateEnvironmentMetrics(parameters)

        clog_rate_pct = self.CalculateLineClogRate(
            nozzle_clog_rate_pct=nozzle_metrics.get("nozzle_clog_rate_pct"),
            filter_clog_rate_pct=filter_metrics.get("filter_clog_rate_pct")
        )

        maintainability_pct = self.CalculateLineMaintainability(
            nozzle_maintainability_pct=nozzle_metrics.get("nozzle_maintainability_pct"),
            filter_maintainability_pct=filter_metrics.get("filter_maintainability_pct")
        )

        quality_score_pct = self.CalculateQualityScorePct(
            coverage_score_pct=spray_width_metrics.get("coverage_score_pct"),
            ok_count=parameters.get("ok_count"),
            total_count=parameters.get("total_count"),
            defect_count=parameters.get("defect")
        )

        availability_pct = self.CalculateAvailabilityPct(
            available_time_sec=parameters.get("available_time_sec"),
            planned_time_sec=parameters.get("planned_time_sec")
        )

        utilization_pct = self.CalculateUtilizationPct(
            running_time_sec=parameters.get("running_time_sec"),
            total_window_time_sec=parameters.get("total_window_time_sec")
        )

        cycle_time_sec = self.CalculateCycleTimeSec(
            part_start_time=parameters.get("part_start_time"),
            part_end_time=parameters.get("part_end_time")
        )

        component_metrics = {
            "quality_module": quality_module_metrics,
            "nozzle": nozzle_metrics,
            "filter_mesh": filter_metrics,
            "pump_unit": pump_unit_metrics,
            "air_compressor": air_compressor_metrics,
            "spray_width": spray_width_metrics,
            "robot_arm": robot_arm_metrics,
            "environment": environment_metrics,
        }

        rule_evaluation = evaluate_station_rules(
            station_id=parameters.get("station_id"),
            line_id=parameters.get("line_id"),
            batch_id=parameters.get("batch_id"),
            timestamp=parameters.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            sensor_payload=self.BuildSensorPayloadForRule(parameters),
            data_quality_flag=parameters.get("data_quality_flag"),
        )

        return {
            "time_type": time_type,
            "sample_method": sample_method_name,
            "state": rule_evaluation.get("station_state"),
            "component_overview": rule_evaluation.get("component_overview", []),
            "fault_detail": rule_evaluation.get("fault_detail", []),
            "event_rule_evaluation": rule_evaluation,
            "component_metrics": component_metrics,
            "metrics": {
                "availability_pct": availability_pct,
                "clog_rate_pct": clog_rate_pct,
                "air_pressure_bar": air_compressor_metrics.get("air_pressure_bar"),
                "pressure_bar": air_compressor_metrics.get("air_pressure_bar"),
                "paint_flow_ml_min": nozzle_metrics.get("paint_flow_ml_min"),
                "flow_rate_ml_min": nozzle_metrics.get("paint_flow_ml_min"),
                "maintainability_pct": maintainability_pct,
                "quality_score_pct": quality_score_pct,
                "risk_text": rule_evaluation.get("risk_text"),
                "spray_width_mm": spray_width_metrics.get("spray_width_mm"),
                "film_thickness_um": quality_module_metrics.get("film_thickness_um"),
                "temperature_c": environment_metrics.get("temperature_c"),
                "humidity_rh": environment_metrics.get("humidity_rh"),
            },
            "process_parameters": {
                "recipe_name": parameters.get("recipe_name"),
                "temperature_c": parameters.get("temperature_c"),
                "humidity_rh": parameters.get("humidity_rh"),
                "utilization_pct": utilization_pct,
                "cycle_time_sec": cycle_time_sec,
                "station_id": parameters.get("station_id"),
                "batch_id": parameters.get("batch_id"),
                "timestamp": parameters.get("timestamp"),
                "data_quality_flag": parameters.get("data_quality_flag"),
            },
            "sensor_payload": self.BuildSensorPayloadForRule(parameters),
            "spray_width_image": {
                "spray_width_mm": spray_width_metrics.get("spray_width_mm"),
                "target_min_mm": spray_width_metrics.get("target_min_mm"),
                "target_max_mm": spray_width_metrics.get("target_max_mm"),
                "status": rule_evaluation.get("station_state"),
                "image_ref": None,
                "note": rule_evaluation.get("risk_text")
            }
        }

    def CalculateClogRateFromNominalFlow(self, actual_flow_rate: Any, nominal_flow_rate: Any) -> Any:
        if not self.IsValidNumber(actual_flow_rate):
            return None

        if not self.IsValidNumber(nominal_flow_rate) or nominal_flow_rate == 0:
            return None

        return max(
            0,
            (nominal_flow_rate - actual_flow_rate) / nominal_flow_rate * 100
        )

    def CalculateFlowLossPct(self, in_flow_ml_min: Any, out_flow_ml_min: Any) -> Any:
        if not self.IsValidNumber(in_flow_ml_min) or in_flow_ml_min == 0:
            return None

        if not self.IsValidNumber(out_flow_ml_min):
            return None

        return max(
            0,
            (in_flow_ml_min - out_flow_ml_min) / in_flow_ml_min * 100
        )

    def CalculateMaintainabilityPct(self, rul_hr: Any, usage_time_hr: Any) -> Any:
        if not self.IsValidNumber(rul_hr):
            return None

        if not self.IsValidNumber(usage_time_hr):
            return None

        total_time = rul_hr + usage_time_hr

        if total_time == 0:
            return None

        return rul_hr / total_time * 100

    def CalculateLineClogRate(self, nozzle_clog_rate_pct: Any, filter_clog_rate_pct: Any) -> Any:
        values = [
            value for value in [nozzle_clog_rate_pct, filter_clog_rate_pct]
            if self.IsValidNumber(value)
        ]

        return max(values) if values else None

    def CalculateLineMaintainability(
        self,
        nozzle_maintainability_pct: Any,
        filter_maintainability_pct: Any
    ) -> Any:
        values = [
            value for value in [nozzle_maintainability_pct, filter_maintainability_pct]
            if self.IsValidNumber(value)
        ]

        return min(values) if values else None

    def CalculateQualityScorePct(
        self,
        coverage_score_pct: Any,
        ok_count: Any,
        total_count: Any,
        defect_count: Any
    ) -> Any:
        if (
            self.IsValidNumber(ok_count)
            and self.IsValidNumber(total_count)
            and total_count != 0
        ):
            return ok_count / total_count * 100

        if self.IsValidNumber(coverage_score_pct):
            return coverage_score_pct

        if self.IsValidNumber(defect_count) and defect_count > 0:
            return 0

        return None

    def CalculateUtilizationPct(self, running_time_sec: Any, total_window_time_sec: Any) -> Any:
        if not self.IsValidNumber(running_time_sec):
            return None

        if not self.IsValidNumber(total_window_time_sec) or total_window_time_sec == 0:
            return None

        return running_time_sec / total_window_time_sec * 100

    def CalculateAvailabilityPct(self, available_time_sec: Any, planned_time_sec: Any) -> Any:
        if not self.IsValidNumber(available_time_sec):
            return None

        if not self.IsValidNumber(planned_time_sec) or planned_time_sec == 0:
            return None

        return available_time_sec / planned_time_sec * 100

    def CalculateCycleTimeSec(self, part_start_time: Any, part_end_time: Any) -> Any:
        if (
            self.IsValidNumber(part_start_time)
            and self.IsValidNumber(part_end_time)
        ):
            return part_end_time - part_start_time

        return None

    def BuildLineOutput(self, line: Dict[str, Any], calculated_data: Dict[str, Any]) -> Dict[str, Any]:
        state = calculated_data.get("state")
        metrics = calculated_data.get("metrics", {})

        station = {
            "line_id": line.get("line_id"),
            "station_id": calculated_data.get("process_parameters", {}).get("station_id"),
            "station_name_zh": line.get("station_name_zh"),
            "station_name_en": line.get("station_name_en"),

            "state": state,
            "component_overview": calculated_data.get("component_overview", []),

            "metrics": metrics,
            "process_parameters": calculated_data.get("process_parameters", {}),
            "component_metrics": calculated_data.get("component_metrics", {}),

            "fault_detail": calculated_data.get("fault_detail", []),
            "event_rule_evaluation": calculated_data.get("event_rule_evaluation", {}),
            "sensor_payload": calculated_data.get("sensor_payload", {}),
            "spray_width_image": calculated_data.get("spray_width_image", {})
        }

        station["d_payloads"] = build_d_integration_payloads(
            station=station,
            time_type=calculated_data.get("time_type", "current"),
            sample_method_name=calculated_data.get("sample_method", "recent_average"),
        )

        return station

    def BuildSummary(self, stations: List[Dict[str, Any]]) -> Dict[str, Any]:
        normal_count = sum(1 for station in stations if station.get("state") == "normal")
        warning_count = sum(1 for station in stations if station.get("state") == "warning")
        fault_count = sum(1 for station in stations if station.get("state") == "fault")

        d_payloads = flatten_d_payloads(stations)
        return {
            "total_station_count": len(stations),
            "normal_count": normal_count,
            "warning_count": warning_count,
            "fault_count": fault_count,
            "predict_risk_count": warning_count + fault_count,
            "monitoring_warning_count": sum(1 for item in d_payloads.get("monitoring_results", []) if item.get("status") != "normal"),
            "alert_event_count": len(d_payloads.get("alert_events", [])),
            "future_prediction_count": len(d_payloads.get("future_prediction_results", [])),
            "troubleshooting_count": len(d_payloads.get("troubleshooting_results", [])),
            "rule_integrated": True,
            "d_integration_enabled": True,
        }

    def BuildOutput(
        self,
        request: Dict[str, Any],
        time_type: str,
        sample_method_name: str,
        raw_dataset_metadata: Dict[str, Any],
        stations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        return {
            "schema_version": "v1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "service_name": "TimeSeriesService",
            "request_id": request.get("request_id"),
            "viewer_state": self.BuildViewerState(request, time_type, sample_method_name),
            "summary": self.BuildSummary(stations),
            "stations": stations,
            "d_integration": flatten_d_payloads(stations),
            "calculation_info": {
                "pipeline": [
                    "HandleTimeSeriesQuery",
                    "ValidateRequest",
                    "DetermineTimeType",
                    "QueryRawDataFromDatabase",
                    "ApplySampleMethods",
                    "CalculateLineMetrics",
                    "EvaluateEventRules",
                    "BuildDIntegrationPayloads",
                    "BuildMonitoringPayload",
                    "BuildAlertEventPayload",
                    "BuildFuturePredictionPayload",
                    "BuildTroubleshootingPayload",
                    "BuildOutput",
                    "SaveProcessedResultToDatabase"
                ],
                "raw_dataset_metadata": raw_dataset_metadata,
                "rule_stage": "integrated_D_monitoring_eventrule_future_troubleshooting_payload",
                "rule_source": "config/rules/sensor_thresholds.json",
                "knowledge_source": "config/knowledge/troubleshooting_matrix_reference.csv",
                "sample_method": sample_method_name,
                "note": "D-stage integration: TimeSeriesService calculates full component_metrics, evaluates EventRule thresholds, builds Monitoring payload, alert_event payload, batch_station_status payload, Future prediction payload, and Troubleshooting payload. Runtime files are demo JSON outputs; formal DB API can replace them later."
            },
            "database_info": {
                "save_processed_result": True,
                "save_target": str(self.processed_result_db_path),
                "saved_at": None,
                "data_type": "processed_result",
                "note": "Only processed/calculated data is saved. Raw data is generated randomly in prototype mode and not saved again by this service."
            }
        }

    def SaveDIntegrationRuntimeOutputs(self, output: Dict[str, Any]) -> Dict[str, str]:
        """Save D-stage payload groups as separate demo JSON files."""

        d_payloads = output.get("d_integration", {})
        runtime_dir = self.processed_result_db_path.parent
        runtime_dir.mkdir(parents=True, exist_ok=True)

        file_map = {
            "alert_events": runtime_dir / "alert_event_demo.json",
            "batch_station_status": runtime_dir / "batch_station_status_demo.json",
            "future_prediction_results": runtime_dir / "future_prediction_result_demo.json",
            "troubleshooting_results": runtime_dir / "troubleshooting_result_demo.json",
            "monitoring_results": runtime_dir / "monitoring_result_demo.json",
        }

        saved_paths = {}
        for key, path in file_map.items():
            path.write_text(
                json.dumps(d_payloads.get(key, []), ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            saved_paths[key] = str(path)

        output.setdefault("database_info", {})["d_runtime_output_paths"] = saved_paths
        return saved_paths

    def SaveLatestOutputJson(self, output: Dict[str, Any]) -> Path:
        """
        將最新一次完整 output 另存成 JSON 檔。

        這個檔案每次執行會覆蓋更新，方便直接打開查看最新結果。
        """

        output["database_info"]["latest_output_json_path"] = str(self.latest_output_json_path)

        self.latest_output_json_path.parent.mkdir(parents=True, exist_ok=True)

        self.latest_output_json_path.write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        return self.latest_output_json_path

    def SaveProcessedResultToDatabase(self, output: Dict[str, Any]) -> Dict[str, Any]:
        saved_at = datetime.now(timezone.utc).isoformat()

        output["database_info"]["saved_at"] = saved_at
        output["database_info"]["save_target"] = str(self.processed_result_db_path)

        db_record = {
            "schema_version": output.get("schema_version"),
            "saved_at": saved_at,
            "generated_at": output.get("generated_at"),
            "service_name": output.get("service_name"),
            "request_id": output.get("request_id"),
            "viewer_state": output.get("viewer_state"),
            "summary": output.get("summary"),
            "stations": output.get("stations"),
            "d_integration": output.get("d_integration"),
            "calculation_info": output.get("calculation_info"),
            "data_type": "processed_result"
        }

        self.processed_result_db_path.parent.mkdir(parents=True, exist_ok=True)

        if self.processed_result_db_path.exists():
            try:
                records = json.loads(
                    self.processed_result_db_path.read_text(encoding="utf-8")
                )
                if not isinstance(records, list):
                    records = []
            except json.JSONDecodeError:
                records = []
        else:
            records = []

        records.append(db_record)

        self.processed_result_db_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        return db_record


def BuildTimeSeriesRequestTemplate() -> Dict[str, Any]:
    return {
        "schema_version": "v1.0",
        "service_name": "TimeSeriesService",
        "request_id": None,
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
            "cycle_time_sec"
        ]
    }


def BuildRandomTimeSeriesRequest() -> Dict[str, Any]:
    """
    建立隨機時間狀態 request。

    目的：
    讓直接執行 time_series_service.py 時，
    不會每次都因為 slider_value = 0 而固定 current。
    """

    request = BuildTimeSeriesRequestTemplate()

    time_option = random.choice(["past", "current", "future"])

    if time_option == "past":
        request["request_id"] = "random_past_001"
        request["window_type"] = "2hour"
        request["slider_value"] = random.choice([-1, -2, -3, -4, -5])

    elif time_option == "current":
        request["request_id"] = "random_current_001"
        request["window_type"] = "current"
        request["slider_value"] = 0

    else:
        request["request_id"] = "random_future_001"
        request["window_type"] = "2hour"
        request["slider_value"] = random.choice([1, 2, 3, 4, 5])

    return request


if __name__ == "__main__":
    # Demo only.
    # 正式系統請透過 api_server.py 接收 UI / Integration Service 的 request。
    service = TimeSeriesService()
    request = BuildRandomTimeSeriesRequest()
    output = service.HandleTimeSeriesQuery(request)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(
        "\nRandom time_type = "
        f"{output['viewer_state']['time_type']}, "
        f"slider_value = {output['viewer_state']['slider_value']}"
    )
    print(f"Latest JSON output saved to: {service.latest_output_json_path}")
    print(f"Processed result database saved to: {service.processed_result_db_path}")
