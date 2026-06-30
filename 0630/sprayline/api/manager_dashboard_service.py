from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


STATION_META: dict[str, dict[str, str]] = {
    "line_1": {
        "stationId": "Station_1",
        "stationName": "Station 1",
        "layerName": "Primer",
        "machineName": "Primer Spray Robot",
        "engineerRole": "Primer Process Engineer",
        "engineerEmail": "primer.engineer@example.com",
        "recipeId": "BASE-WHITE-01",
    },
    "line_2": {
        "stationId": "Station_2",
        "stationName": "Station 2",
        "layerName": "Topcoat",
        "machineName": "Topcoat Spray Robot",
        "engineerRole": "Topcoat Process Engineer",
        "engineerEmail": "topcoat.engineer@example.com",
        "recipeId": "COLOR-WHITE-01",
    },
    "line_3": {
        "stationId": "Station_3",
        "stationName": "Station 3",
        "layerName": "Clearcoat",
        "machineName": "Clearcoat Spray Robot",
        "engineerRole": "Clearcoat Process Engineer",
        "engineerEmail": "clearcoat.engineer@example.com",
        "recipeId": "CLEAR-COAT-01",
    },
}

STATION_META_BY_STATION_ID: dict[str, dict[str, str]] = {
    meta["stationId"]: {
        **meta,
        "lineId": line_id,
    }
    for line_id, meta in STATION_META.items()
}

MANAGER_BATCH_SIZE_PCS = 264
MANAGER_DAILY_TARGET_PCS = 200000
MANAGER_BATCH_MODE_LABEL = "全部批號 / 該小時累計"


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _average(values: list[float]) -> float:
    cleaned = [float(value) for value in values if value is not None]
    if not cleaned:
        return 0.0
    return sum(cleaned) / len(cleaned)


def _parse_generated_at(api_bundle: dict[str, Any]) -> datetime:
    raw = str(api_bundle.get("generated_at") or "")
    if raw:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now().astimezone()


def _normalize_state(state: Any) -> str:
    value = str(state or "").lower()
    if value in {"warning", "alarm", "fault", "down"}:
        return "warning"
    return "running"


def _normalize_severity(value: Any) -> str:
    text = str(value or "").lower()
    if text in {"alarm", "critical", "danger", "fault"}:
        return "alarm"
    if text in {"warning", "warn"}:
        return "warning"
    if text in {"monitor", "observe"}:
        return "monitor"
    return "normal"


def _get_trend_row_hour(row: dict[str, Any], fallback_index: int) -> int:
    raw = row.get("hour", row.get("index", row.get("t", row.get("label", row.get("timestamp", fallback_index)))))
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    hour = int(digits[:2]) if digits else fallback_index
    return max(0, min(23, hour))


def _get_trend_row_value(row: dict[str, Any]) -> float | None:
    for key in (
        "value",
        "quality_score_pct",
        "predicted_ok_rate",
        "ok_rate",
        "utilization_pct",
        "cycle_time_sec",
        "cycle_time_s",
        "y",
    ):
        value = row.get(key)
        if value not in (None, ""):
            return _number(value)
    return None


def _normalize_quality_trend(trend: dict[str, Any] | None) -> list[float | None]:
    values: list[float | None] = [None] * 24
    if trend:
        for key in ("actual_series", "predicted_series", "forecast_series"):
            for index, row in enumerate(trend.get(key, []) or []):
                hour = _get_trend_row_hour(row, index)
                value = _get_trend_row_value(row)
                if value is not None:
                    values[hour] = value
    return [float(value) if value is not None else None for value in values]


def _normalize_single_series_trend(trend: dict[str, Any] | None) -> list[float | None]:
    values: list[float | None] = [None] * 24
    if trend:
        for index, row in enumerate(trend.get("series", []) or []):
            hour = _get_trend_row_hour(row, index)
            value = _get_trend_row_value(row)
            if value is not None:
                values[hour] = value
    return [float(value) if value is not None else None for value in values]


def _parse_selection_datetime(raw: Any, fallback: datetime) -> datetime:
    if raw:
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            pass
    return fallback


def _estimate_station_output(cycle_time_sec: float, utilization_pct: float, hours: float) -> int:
    cycle = max(cycle_time_sec, 1.0)
    utilization = max(0.0, utilization_pct) / 100.0
    return max(0, round(hours * 3600.0 / cycle * utilization))


def _get_spray_width_status(station: dict[str, Any]) -> str:
    metrics = station.get("metrics", {})
    width = _number(metrics.get("spray_width_mm"))
    target_min = _number(metrics.get("target_min_mm"))
    target_max = _number(metrics.get("target_max_mm"))

    if width < target_min or width > target_max:
        return "out"

    margin = min(abs(width - target_min), abs(target_max - width))
    return "near" if margin <= 2 else "normal"


def _get_risk_level_from_score(score: float) -> str:
    if score >= 70:
        return "alarm"
    if score >= 35:
        return "warning"
    return "normal"


def _build_station_risk_reasons(station: dict[str, Any]) -> list[str]:
    metrics = station.get("metrics", {})
    baseline = station.get("baseline", {})
    reasons: list[str] = []

    quality_score = _number(metrics.get("quality_score_pct"))
    clog_rate = _number(metrics.get("clog_rate_pct"))
    utilization = _number(metrics.get("utilization_pct"))
    cycle_time = _number(metrics.get("cycle_time_sec"))
    spray_width = _number(metrics.get("spray_width_mm"))
    target_min = _number(metrics.get("target_min_mm"))
    target_max = _number(metrics.get("target_max_mm"))
    flow_rate = _number(metrics.get("flow_rate_ml_min"))
    pressure = _number(metrics.get("pressure_bar"))

    baseline_utilization = _number(baseline.get("utilization_pct"))
    baseline_cycle = max(_number(baseline.get("cycle_time_sec")), 1.0)
    baseline_flow = max(_number(baseline.get("flow_rate_ml_min")), 1.0)
    baseline_pressure = max(_number(baseline.get("pressure_bar")), 1.0)

    if quality_score < 92:
        reasons.append(f"Quality score {quality_score:.1f}% is below the 92% management target.")
    if clog_rate >= 10:
        reasons.append(f"Clog rate {clog_rate:.1f}% indicates abnormal filter loading.")
    if utilization < baseline_utilization - 5:
        reasons.append(
            f"Utilization {utilization:.1f}% is {baseline_utilization - utilization:.1f} points below baseline."
        )
    if cycle_time > baseline_cycle * 1.08:
        reasons.append(f"Cycle time {cycle_time:.1f}s is slower than the {baseline_cycle:.1f}s baseline.")
    if spray_width < target_min or spray_width > target_max:
        reasons.append(f"Spray width {spray_width:.0f}mm is outside the {target_min:.0f}-{target_max:.0f}mm target.")
    if flow_rate < baseline_flow * 0.92:
        reasons.append(f"Flow rate {flow_rate:.0f} ml/min is below the {baseline_flow:.0f} ml/min baseline.")
    if abs(pressure - baseline_pressure) / baseline_pressure > 0.08:
        reasons.append(f"Pressure {pressure:.2f} bar deviates materially from the {baseline_pressure:.2f} bar baseline.")

    if not reasons:
        reasons.append("No abnormal delta was detected; keep monitoring this station.")

    return reasons


def _estimate_performance_pct(station: dict[str, Any]) -> float:
    baseline_cycle = max(_number(station.get("baseline", {}).get("cycle_time_sec")), 1.0)
    current_cycle = max(_number(station.get("metrics", {}).get("cycle_time_sec")), 1.0)
    value = baseline_cycle / current_cycle * 100.0
    return max(0.0, min(100.0, round(value, 1)))


def _evaluate_station_risk(db: dict[str, Any], station: dict[str, Any]) -> dict[str, Any]:
    responsibility = (db.get("stationResponsibility") or {}).get(station.get("lineId"), {})
    metrics = station.get("metrics", {})
    baseline = station.get("baseline", {})

    quality_risk = max(0.0, (94.0 - _number(metrics.get("quality_score_pct"))) * 4.2)
    clog_risk = max(0.0, (_number(metrics.get("clog_rate_pct")) - 5.0) * 3.2)
    utilization_risk = max(0.0, (_number(baseline.get("utilization_pct")) - _number(metrics.get("utilization_pct"))) * 2.0)

    baseline_cycle = max(_number(baseline.get("cycle_time_sec")), 1.0)
    cycle_risk = max(
        0.0,
        ((_number(metrics.get("cycle_time_sec")) - baseline_cycle) / baseline_cycle) * 100.0 * 1.8,
    )

    spray_status = _get_spray_width_status(station)
    spray_risk = 16.0 if spray_status == "out" else 6.0 if spray_status == "near" else 0.0

    baseline_flow = max(_number(baseline.get("flow_rate_ml_min")), 1.0)
    flow_risk = max(
        0.0,
        ((baseline_flow - _number(metrics.get("flow_rate_ml_min"))) / baseline_flow) * 100.0 * 1.4,
    )

    baseline_pressure = max(_number(baseline.get("pressure_bar")), 1.0)
    pressure_risk = max(
        0.0,
        ((abs(_number(metrics.get("pressure_bar")) - baseline_pressure) / baseline_pressure) * 100.0 - 5.0) * 1.1,
    )

    risk_score = round(quality_risk + clog_risk + utilization_risk + cycle_risk + spray_risk + flow_risk + pressure_risk)

    return {
        "station": station,
        "responsibility": responsibility,
        "riskScore": risk_score,
        "riskLevel": _get_risk_level_from_score(risk_score),
        "reasons": _build_station_risk_reasons(station),
    }


def _build_assignments_from_stations(
    station_evaluations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    assignments: list[dict[str, Any]] = []

    for index, evaluation in enumerate(station_evaluations):
        responsibility = evaluation.get("responsibility", {})
        station = evaluation.get("station", {})
        metrics = station.get("metrics", {})
        baseline = station.get("baseline", {})
        is_main_issue = index == 0

        task_parts = []
        if _number(metrics.get("clog_rate_pct")) >= 10 or station.get("componentHealth", {}).get("nozzle") != "normal":
            task_parts.append("inspect nozzle condition")
        if station.get("componentHealth", {}).get("filter_mesh") != "normal":
            task_parts.append("clean or replace the filter mesh")
        if _get_spray_width_status(station) != "normal":
            task_parts.append("re-center spray width")
        task_parts.extend(
            [
                "reconfirm pressure and flow setpoints",
                "verify robot path consistency",
                "review the latest QC batch",
            ]
        )

        task_text = ", ".join(task_parts)

        assignments.append(
            {
                "priority": f"P{index + 1}",
                "owner": responsibility.get("engineerRole", "Process Engineer"),
                "station": responsibility.get("stationName", station.get("lineId", "station")),
                "processLayer": responsibility.get("layerName", "process"),
                "email": responsibility.get("engineerEmail", ""),
                "issue": f"Risk score {evaluation['riskScore']} with primary issue: {evaluation['reasons'][0]}",
                "task": f"Review this station and {task_text}.",
                "due": "Immediate" if is_main_issue else "Within this shift",
                "status": "Open",
                "acceptance": (
                    f"Restore quality >= 92%, utilization >= {baseline.get('utilization_pct', 0):.1f}% "
                    f"and cycle time <= {baseline.get('cycle_time_sec', 0):.1f}s."
                ),
                "riskScore": evaluation["riskScore"],
                "riskReasons": evaluation["reasons"],
            }
        )

    return assignments


def _build_acceptance_checklist(
    main_evaluation: dict[str, Any],
    assignments: list[dict[str, Any]],
) -> list[str]:
    responsibility = main_evaluation.get("responsibility", {})
    main_station = responsibility.get("stationName", "Main station")
    main_layer = responsibility.get("layerName", "process")
    owner = responsibility.get("engineerRole", "Process Engineer")
    primary = assignments[0] if assignments else {}

    return [
        f"{main_station} / {main_layer} risk score is reduced below the warning threshold.",
        "Predicted or actual quality recovers to at least 92%.",
        "Utilization and cycle time return to station baseline.",
        f"{owner} acknowledges and closes the assigned corrective task.",
        primary.get("acceptance", "Primary action is validated by the manager view."),
    ]


def build_manager_summary(db: dict[str, Any]) -> dict[str, Any]:
    production = db.get("productionKpi", {})
    station_evaluations = [_evaluate_station_risk(db, station) for station in db.get("stationTelemetry", [])]
    station_evaluations.sort(key=lambda item: item["riskScore"], reverse=True)

    if not station_evaluations:
        return {
            "dataSource": db.get("responseMeta", {}).get("source", ""),
            "apiVersion": db.get("responseMeta", {}).get("apiVersion", ""),
            "generatedAt": db.get("responseMeta", {}).get("generatedAt", ""),
            "lineName": db.get("line", {}).get("lineName", "Spray Line Manager UI"),
            "stationEvaluations": [],
            "assignments": [],
            "acceptanceChecklist": [],
        }

    main_evaluation = station_evaluations[0]
    main_station = main_evaluation["station"]
    responsibility = main_evaluation["responsibility"]
    validation = db.get("qualityValidation", {})

    current_period = production.get("currentPeriod", {})
    previous_period = production.get("previousPeriod", {})
    yesterday_actual = production.get("yesterdayActual", {})
    today_estimate = production.get("todayEstimate", {})
    month_to_date = production.get("monthToDate", {})

    efficiency_change = _number(current_period.get("estimatedEfficiencyPct")) - _number(previous_period.get("actualEfficiencyPct"))
    today_vs_yesterday_change = _number(today_estimate.get("estimatedEfficiencyPct")) - _number(yesterday_actual.get("actualEfficiencyPct"))
    month_change = _number(month_to_date.get("estimatedEfficiencyPct")) - _number(month_to_date.get("lastMonthSamePeriodActualEfficiencyPct"))
    lost_production_pcs = max(0, round(_number(previous_period.get("producedPcs")) - _number(current_period.get("producedPcs"))))
    extra_predicted_ng_pcs = max(0, round(_number(current_period.get("predictedNgPcs")) - _number(previous_period.get("actualNgPcs"))))

    assignments = _build_assignments_from_stations(station_evaluations)

    return {
        "dataSource": db.get("responseMeta", {}).get("source", ""),
        "apiVersion": db.get("responseMeta", {}).get("apiVersion", ""),
        "generatedAt": db.get("responseMeta", {}).get("generatedAt", ""),
        "lineName": db.get("line", {}).get("lineName", "Spray Line Manager UI"),
        "mainIssueLineId": main_station.get("lineId", ""),
        "mainIssueStation": responsibility.get("stationName", ""),
        "mainIssueRobot": responsibility.get("machineName", ""),
        "mainIssueProcess": responsibility.get("layerName", ""),
        "responsibleEngineer": responsibility.get("engineerRole", ""),
        "responsibleEmail": responsibility.get("engineerEmail", ""),
        "mainStationState": main_station.get("state", ""),
        "mainStationRecipe": main_station.get("recipeId", ""),
        "mainStationMetrics": main_station.get("metrics", {}),
        "mainStationBaseline": main_station.get("baseline", {}),
        "mainStationComponents": main_station.get("componentHealth", {}),
        "mainStationRiskScore": main_evaluation["riskScore"],
        "mainRiskReasons": main_evaluation["reasons"],
        "stationEvaluations": station_evaluations,
        "estimatedThisWeekEfficiency": _number(current_period.get("estimatedEfficiencyPct")),
        "lastWeekActualEfficiency": _number(previous_period.get("actualEfficiencyPct")),
        "efficiencyChange": round(efficiency_change, 1),
        "todayEstimatedEfficiency": _number(today_estimate.get("estimatedEfficiencyPct")),
        "yesterdayActualEfficiency": _number(yesterday_actual.get("actualEfficiencyPct")),
        "todayVsYesterdayChange": round(today_vs_yesterday_change, 1),
        "monthToDateEstimatedEfficiency": _number(month_to_date.get("estimatedEfficiencyPct")),
        "lastMonthSamePeriodActualEfficiency": _number(month_to_date.get("lastMonthSamePeriodActualEfficiencyPct")),
        "monthChange": round(month_change, 1),
        "predictedOkRate": _number(current_period.get("estimatedOkRatePct")),
        "lastWeekActualOkRate": _number(previous_period.get("actualOkRatePct")),
        "predictedNgPcs": round(_number(current_period.get("predictedNgPcs"))),
        "lastWeekActualNgPcs": round(_number(previous_period.get("actualNgPcs"))),
        "utilization": _number(main_station.get("metrics", {}).get("utilization_pct")),
        "lastWeekUtilization": _number(main_station.get("baseline", {}).get("utilization_pct")),
        "performance": _estimate_performance_pct(main_station),
        "lastWeekPerformance": 100.0,
        "producedPcs": round(_number(current_period.get("producedPcs"))),
        "lastWeekProducedPcs": round(_number(previous_period.get("producedPcs"))),
        "lostProductionPcs": lost_production_pcs,
        "extraPredictedNgPcs": extra_predicted_ng_pcs,
        "extraDowntimeMinutes": round(_number(current_period.get("estimatedDowntimeMin"))),
        "futureNoActionEfficiency": _number(db.get("forecastNoAction", {}).get("estimatedEfficiencyPct")),
        "futureNoActionOkRate": _number(db.get("forecastNoAction", {}).get("estimatedOkRatePct")),
        "futureLostPcs": round(_number(db.get("forecastNoAction", {}).get("extraLostProductionPcs"))),
        "futureExtraNgPcs": round(_number(db.get("forecastNoAction", {}).get("extraPredictedNgPcs"))),
        "futureRiskText": db.get("forecastNoAction", {}).get("riskText", ""),
        "dataStatus": {
            "todayCompleteness": _number(db.get("responseMeta", {}).get("dataCompletenessPct")),
            "weekProgress": db.get("responseMeta", {}).get("weekProgress", ""),
            "source": db.get("responseMeta", {}).get("source", ""),
            "apiVersion": db.get("responseMeta", {}).get("apiVersion", ""),
            "dataWindow": db.get("responseMeta", {}).get("dataWindow", {}),
        },
        "predictionValidation": {
            "yesterdayPredictedOkRate": _number(validation.get("predictedOkRatePct")),
            "yesterdayActualOkRate": _number(validation.get("actualOkRatePct")),
            "predictionErrorPts": round(abs(_number(validation.get("actualOkRatePct")) - _number(validation.get("predictedOkRatePct"))), 1),
            "yesterdayPredictedNgPcs": round(_number(validation.get("predictedNgPcs"))),
            "yesterdayActualNgPcs": round(_number(validation.get("actualNgPcs"))),
            "modelTrustLevel": validation.get("modelTrustLevel", "medium"),
            "modelInputSource": validation.get("modelInputSource", ""),
        },
        "assignments": assignments,
        "acceptanceChecklist": _build_acceptance_checklist(main_evaluation, assignments),
    }


def _clean_batch_id(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _safe_hour(value: Any) -> int:
    try:
        hour = int(value)
    except (TypeError, ValueError):
        hour = 0
    return max(0, min(23, hour))


def _round_or_none(value: Any, digits: int = 1) -> float | None:
    try:
        if value is None:
            return None
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _average_or_none(values: list[Any], digits: int = 1) -> float | None:
    cleaned = [float(value) for value in values if value is not None]
    if not cleaned:
        return None
    return round(sum(cleaned) / len(cleaned), digits)


def _station_order_key(station_id: str) -> int:
    meta = STATION_META_BY_STATION_ID.get(station_id, {})
    line_id = str(meta.get("lineId") or "")
    try:
        return int(line_id.split("_")[-1])
    except (IndexError, ValueError):
        return 99


def _normalize_manager_daily_rows(api_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    dataset = api_bundle.get("managerDataset") or {}
    normalized_rows: list[dict[str, Any]] = []

    for raw in dataset.get("dailySensorRows") or []:
        station_id = str(raw.get("stationId") or raw.get("station_id") or "")
        meta = STATION_META_BY_STATION_ID.get(station_id)
        if not meta:
            continue

        normalized_rows.append(
            {
                "lineId": str(raw.get("lineId") or meta.get("lineId") or ""),
                "stationId": station_id,
                "stationName": meta.get("stationName", station_id),
                "processName": meta.get("layerName", ""),
                "batchId": _clean_batch_id(raw.get("batchId") or raw.get("batch_id")),
                "dataHour": _safe_hour(raw.get("dataHour") or raw.get("data_hour")),
                "qualityScorePct": _round_or_none(raw.get("quality_score_pct"), 2),
            }
        )

    return normalized_rows


def _series_entry(hour: int, value: Any, total_pcs: Any) -> dict[str, Any]:
    return {
        "hour": hour,
        "hourLabel": f"{hour:02d}:00",
        "value": _round_or_none(value),
        "totalPcs": int(total_pcs) if total_pcs not in (None, "") else None,
    }


def _build_station_hour_series(
    rows: list[dict[str, Any]],
    selected_batch_id: str | None = None,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    output: dict[str, dict[str, list[dict[str, Any]]]] = {}

    for station_id in STATION_META_BY_STATION_ID:
        station_rows = [
            row for row in rows
            if row["stationId"] == station_id and (selected_batch_id is None or row["batchId"] == selected_batch_id)
        ]
        utilization_series: list[dict[str, Any]] = []
        ok_series: list[dict[str, Any]] = []
        ng_series: list[dict[str, Any]] = []

        for hour in range(24):
            hour_rows = [row for row in station_rows if row["dataHour"] == hour]
            ok_rate = _average_or_none([row.get("qualityScorePct") for row in hour_rows])
            utilization_pct = round(min(100.0, len(hour_rows) / 60.0 * 100.0), 1) if hour_rows else None

            if selected_batch_id:
                total_pcs = MANAGER_BATCH_SIZE_PCS if hour_rows else None
            else:
                distinct_batch_count = len({row.get("batchId") for row in hour_rows if row.get("batchId")})
                total_pcs = distinct_batch_count * MANAGER_BATCH_SIZE_PCS if distinct_batch_count else None

            if total_pcs is not None and ok_rate is not None:
                estimated_ok_pcs = round(total_pcs * ok_rate / 100.0)
                estimated_ng_pcs = max(0, int(total_pcs - estimated_ok_pcs))
            else:
                estimated_ok_pcs = None
                estimated_ng_pcs = None

            utilization_series.append(_series_entry(hour, utilization_pct, total_pcs))
            ok_series.append(_series_entry(hour, estimated_ok_pcs, total_pcs))
            ng_series.append(_series_entry(hour, estimated_ng_pcs, total_pcs))

        output[station_id] = {
            "utilizationPct": utilization_series,
            "estimatedOkPcs": ok_series,
            "estimatedNgPcs": ng_series,
        }

    return output


def _filter_mode_alerts(alerts: list[dict[str, Any]], selected_batch_id: str | None) -> list[dict[str, Any]]:
    if selected_batch_id is None:
        return list(alerts)
    return [
        alert for alert in alerts
        if _clean_batch_id(alert.get("batch_id")) == selected_batch_id
    ]


def _issue_level_rank(level: str | None) -> int:
    return {"normal": 0, "warning": 1, "alarm": 2, "critical": 3}.get(str(level or "").lower(), 0)


def _build_issue_candidate(level: str, main_issue: str, recommendation: str, sort_index: int) -> dict[str, Any]:
    return {
        "level": level,
        "mainIssue": main_issue,
        "recommendation": recommendation,
        "sortIndex": sort_index,
    }


def _pick_primary_issue(
    ok_rate: float | None,
    current_ng_pcs: float | None,
    ng_series: list[dict[str, Any]],
    utilization_series: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    issues: list[dict[str, Any]] = []
    alarm_alert = any(str(item.get("state") or "").lower() in {"fault", "alarm", "critical"} for item in alerts)
    if alerts:
        issues.append(
            _build_issue_candidate(
                "alarm" if alarm_alert else "warning",
                "有未處理警報",
                "立即確認未處理警報與站點異常處置",
                0,
            )
        )

    if ok_rate is not None:
        ng_rate = max(0.0, round(100.0 - ok_rate, 1))
        if ng_rate >= 20.0:
            issues.append(_build_issue_candidate("alarm", "NG 率偏高", "檢查噴塗流量、空壓與噴幅設定", 1))
        elif ng_rate >= 1.0:
            issues.append(_build_issue_candidate("warning", "NG 率偏高", "檢查噴塗流量、空壓與噴幅設定", 1))

    avg_ng_pcs = _average_or_none([item.get("value") for item in ng_series])
    if current_ng_pcs is not None and avg_ng_pcs not in (None, 0):
        if current_ng_pcs >= avg_ng_pcs * 2.0:
            issues.append(_build_issue_candidate("alarm", "本小時 NG 上升", "比對本小時批次變化並檢查製程穩定性", 2))
        elif current_ng_pcs >= avg_ng_pcs * 1.5:
            issues.append(_build_issue_candidate("warning", "本小時 NG 上升", "比對本小時批次變化並檢查製程穩定性", 2))

    avg_utilization = _average_or_none([item.get("value") for item in utilization_series])
    if avg_utilization is not None:
        if avg_utilization < 50.0:
            issues.append(_build_issue_candidate("alarm", "稼動率偏低", "檢查設備稼動、上游供料與換線節奏", 3))
        elif avg_utilization < 70.0:
            issues.append(_build_issue_candidate("warning", "稼動率偏低", "檢查設備稼動、上游供料與換線節奏", 3))

    if not issues:
        return None

    issues.sort(key=lambda item: (-_issue_level_rank(item["level"]), item["sortIndex"]))
    return issues[0]


def _build_mode_payload(
    rows: list[dict[str, Any]],
    selected_hour: int,
    selected_batch_id: str | None,
    active_alerts_by_line: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, list[dict[str, Any]]]]]:
    series_by_station = _build_station_hour_series(rows, selected_batch_id=selected_batch_id)
    comparison_rows: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []

    for station_id, meta in sorted(STATION_META_BY_STATION_ID.items(), key=lambda item: _station_order_key(item[0])):
        station_rows_today = [row for row in rows if row["stationId"] == station_id]
        station_rows_for_batch_today = [
            row for row in station_rows_today
            if selected_batch_id is not None and row["batchId"] == selected_batch_id
        ]
        station_rows_current = [
            row for row in station_rows_today
            if row["dataHour"] == selected_hour and (selected_batch_id is None or row["batchId"] == selected_batch_id)
        ]

        has_data = bool(station_rows_current)
        not_arrived = False
        if selected_batch_id is not None:
            not_arrived = not has_data and not station_rows_for_batch_today

        ok_rate = _average_or_none([row.get("qualityScorePct") for row in station_rows_current])
        ng_rate = round(max(0.0, 100.0 - ok_rate), 1) if ok_rate is not None else None
        utilization_entry = series_by_station[station_id]["utilizationPct"][selected_hour]
        ok_entry = series_by_station[station_id]["estimatedOkPcs"][selected_hour]
        ng_entry = series_by_station[station_id]["estimatedNgPcs"][selected_hour]
        alerts = _filter_mode_alerts(active_alerts_by_line.get(meta["lineId"], []), selected_batch_id)
        primary_issue = (
            _pick_primary_issue(
                ok_rate,
                ng_entry.get("value"),
                series_by_station[station_id]["estimatedNgPcs"],
                series_by_station[station_id]["utilizationPct"],
                alerts,
            )
            if has_data
            else None
        )

        if primary_issue:
            main_issue = primary_issue["mainIssue"]
            issue_level = primary_issue["level"]
        elif not_arrived:
            main_issue = "尚未到站"
            issue_level = None
        elif has_data:
            main_issue = "目前穩定"
            issue_level = None
        else:
            main_issue = "本小時無資料"
            issue_level = None

        comparison_row = {
            "stationId": station_id,
            "stationName": meta["stationName"],
            "processName": meta["layerName"],
            "hasData": has_data,
            "notArrived": not_arrived,
            "utilizationPct": utilization_entry.get("value") if has_data else None,
            "estimatedOkRatePct": ok_rate if has_data else None,
            "estimatedNgRatePct": ng_rate if has_data else None,
            "estimatedOkPcs": ok_entry.get("value") if has_data else None,
            "estimatedNgPcs": ng_entry.get("value") if has_data else None,
            "mainIssue": main_issue,
            "issueLevel": issue_level,
        }
        comparison_rows.append(comparison_row)

        if primary_issue:
            recommendations.append(
                {
                    "stationId": station_id,
                    "stationName": meta["stationName"],
                    "processName": meta["layerName"],
                    "batchId": selected_batch_id,
                    "mainIssue": primary_issue["mainIssue"],
                    "recommendation": primary_issue["recommendation"],
                    "level": primary_issue["level"],
                    "engineerName": meta["engineerRole"],
                    "engineerEmail": meta["engineerEmail"],
                }
            )

    recommendations.sort(
        key=lambda item: (
            -_issue_level_rank(item.get("level")),
            _station_order_key(item.get("stationId", "")),
        )
    )
    return comparison_rows, recommendations, series_by_station


def _metric_label(metric_key: str) -> str:
    return {
        "utilizationPct": "稼動率",
        "estimatedOkPcs": "預估 OK pcs",
        "estimatedNgPcs": "預估 NG pcs",
    }.get(metric_key, metric_key)


def _format_metric_value(metric_key: str, value: Any) -> str:
    if value in (None, ""):
        return "—"
    if metric_key == "utilizationPct":
        return f"{float(value):.1f}%"
    return f"{round(float(value))} pcs"


def _build_metric_summary_items(
    metric_key: str,
    series: list[dict[str, Any]],
    selected_hour: int,
    selected_batch_id: str | None,
    comparison_row: dict[str, Any],
) -> list[dict[str, str]]:
    if selected_batch_id:
        items = [
            {"label": "Batch", "value": selected_batch_id},
            {"label": "此批總數", "value": f"{MANAGER_BATCH_SIZE_PCS} pcs"},
        ]
        if metric_key == "utilizationPct":
            items.append({"label": "該站稼動率", "value": _format_metric_value(metric_key, comparison_row.get("utilizationPct"))})
            return items

        items.append({"label": "預估 OK pcs", "value": _format_metric_value("estimatedOkPcs", comparison_row.get("estimatedOkPcs"))})
        items.append({"label": "預估 NG pcs", "value": _format_metric_value("estimatedNgPcs", comparison_row.get("estimatedNgPcs"))})
        return items

    values = [item.get("value") for item in series if item.get("value") is not None]
    current_value = series[selected_hour].get("value") if 0 <= selected_hour < len(series) else None
    peak_value = max(values) if values else None

    if metric_key == "utilizationPct":
        average_value = _average_or_none(values)
        return [
            {"label": "今日平均", "value": _format_metric_value(metric_key, average_value)},
            {"label": "本小時", "value": _format_metric_value(metric_key, current_value)},
            {"label": "最高小時", "value": _format_metric_value(metric_key, peak_value)},
        ]

    return [
        {"label": "今日累計", "value": _format_metric_value(metric_key, sum(values) if values else None)},
        {"label": "本小時", "value": _format_metric_value(metric_key, current_value)},
        {"label": "最高小時", "value": _format_metric_value(metric_key, peak_value)},
    ]


def _build_trend_drawer(
    series_by_station: dict[str, dict[str, list[dict[str, Any]]]],
    comparison_rows: list[dict[str, Any]],
    selected_hour: int,
    selected_batch_id: str | None,
) -> dict[str, Any]:
    comparison_by_station = {row["stationId"]: row for row in comparison_rows}
    station_series: dict[str, Any] = {}

    for station_id, meta in sorted(STATION_META_BY_STATION_ID.items(), key=lambda item: _station_order_key(item[0])):
        station_series[station_id] = {
            "stationId": station_id,
            "stationName": meta["stationName"],
            "processName": meta["layerName"],
            "metrics": {},
        }
        for metric_key in ("utilizationPct", "estimatedOkPcs", "estimatedNgPcs"):
            series = series_by_station[station_id][metric_key]
            station_series[station_id]["metrics"][metric_key] = {
                "metricKey": metric_key,
                "label": _metric_label(metric_key),
                "title": f"{meta['stationName']} / {meta['layerName']} / {_metric_label(metric_key)} 今日每小時趨勢",
                "modeLabel": selected_batch_id or MANAGER_BATCH_MODE_LABEL,
                "unit": "%" if metric_key == "utilizationPct" else "pcs",
                "series": [
                    {
                        "hour": item["hour"],
                        "hourLabel": item["hourLabel"],
                        "value": item["value"],
                    }
                    for item in series
                ],
                "summaryItems": _build_metric_summary_items(
                    metric_key,
                    series,
                    selected_hour,
                    selected_batch_id,
                    comparison_by_station.get(station_id, {}),
                ),
            }

    return {
        "mode": "selected_batch" if selected_batch_id else "all_batches",
        "selectedBatchId": selected_batch_id,
        "defaultModeLabel": MANAGER_BATCH_MODE_LABEL,
        "stationSeries": station_series,
    }


def _build_batch_selector(
    rows: list[dict[str, Any]],
    selected_hour: int,
    active_alerts_by_line: dict[str, list[dict[str, Any]]],
    selected_batch_id: str | None,
) -> tuple[dict[str, Any], str | None]:
    available_batch_ids = sorted({
        row["batchId"]
        for row in rows
        if row["dataHour"] == selected_hour and row["batchId"]
    })
    normalized_selected_batch_id = selected_batch_id if selected_batch_id in available_batch_ids else None

    available_batches: list[dict[str, Any]] = []
    for batch_id in available_batch_ids:
        _comparison, batch_recommendations, _series = _build_mode_payload(
            rows,
            selected_hour,
            batch_id,
            active_alerts_by_line,
        )
        top_issue = batch_recommendations[0] if batch_recommendations else None
        issue_label = top_issue.get("mainIssue") if top_issue else None
        available_batches.append(
            {
                "batchId": batch_id,
                "hasIssue": bool(top_issue),
                "issueLabel": issue_label,
                "displayLabel": f"{batch_id}  ⚠ {issue_label}" if issue_label else batch_id,
            }
        )

    return {
        "selectedBatchId": normalized_selected_batch_id,
        "defaultModeLabel": MANAGER_BATCH_MODE_LABEL,
        "availableBatches": available_batches,
    }, normalized_selected_batch_id


def _pick_worst_station(comparison_rows: list[dict[str, Any]], recommendations: list[dict[str, Any]]) -> dict[str, Any]:
    if recommendations:
        top = recommendations[0]
        return {
            "stationId": top["stationId"],
            "stationName": top["stationName"],
            "processName": top["processName"],
            "mainIssue": top["mainIssue"],
        }

    sorted_rows = sorted(
        comparison_rows,
        key=lambda item: (
            -_issue_level_rank(item.get("issueLevel")),
            -(item.get("estimatedNgRatePct") or 0.0),
        ),
    )
    top = sorted_rows[0] if sorted_rows else None
    return {
        "stationId": top.get("stationId") if top else None,
        "stationName": top.get("stationName") if top else "-",
        "processName": top.get("processName") if top else "-",
        "mainIssue": top.get("mainIssue") if top else "目前穩定",
    }


def build_manager_view(api_bundle: dict[str, Any]) -> dict[str, Any]:
    selection_meta = api_bundle.get("selectionMeta") or {}
    dataset = api_bundle.get("managerDataset") or {}
    rows = _normalize_manager_daily_rows(api_bundle)
    active_alerts_by_line = {
        str(line_id): list(alerts or [])
        for line_id, alerts in (dataset.get("activeAlertsByLine") or {}).items()
    }
    selected_hour = _safe_hour(selection_meta.get("selectedHour"))
    requested_batch_id = _clean_batch_id(dataset.get("selectedBatchId") or selection_meta.get("selectedBatchId"))

    batch_selector, selected_batch_id = _build_batch_selector(
        rows,
        selected_hour,
        active_alerts_by_line,
        requested_batch_id,
    )
    default_comparison, default_recommendations, _default_series = _build_mode_payload(
        rows,
        selected_hour,
        None,
        active_alerts_by_line,
    )
    current_comparison, current_recommendations, current_series = _build_mode_payload(
        rows,
        selected_hour,
        selected_batch_id,
        active_alerts_by_line,
    )

    daily_ok_rate = _average_or_none([row.get("qualityScorePct") for row in rows]) or 0.0
    daily_ng_rate = round(max(0.0, 100.0 - daily_ok_rate), 1)
    distinct_batch_count = int(
        dataset.get("dailyDistinctBatchCount")
        or len({row.get("batchId") for row in rows if row.get("batchId")})
    )
    estimated_produced_pcs = distinct_batch_count * MANAGER_BATCH_SIZE_PCS
    production_achievement_pct = round(
        estimated_produced_pcs / MANAGER_DAILY_TARGET_PCS * 100.0,
        1,
    ) if MANAGER_DAILY_TARGET_PCS else 0.0

    return {
        "selectionContext": {
            "selectedDate": selection_meta.get("selectedDate"),
            "selectedHour": selected_hour,
            "selectedBatchId": selected_batch_id,
            "selectedBatchLabel": selected_batch_id or MANAGER_BATCH_MODE_LABEL,
        },
        "kpis": {
            "estimatedOkRatePct": round(daily_ok_rate, 1),
            "estimatedNgRatePct": daily_ng_rate,
            "productionAchievementPct": production_achievement_pct,
            "dailyProduction": {
                "batchSizePcs": MANAGER_BATCH_SIZE_PCS,
                "dailyTargetPcs": MANAGER_DAILY_TARGET_PCS,
                "distinctBatchCount": distinct_batch_count,
                "estimatedProducedPcs": estimated_produced_pcs,
                "achievementPct": production_achievement_pct,
            },
            "worstStation": _pick_worst_station(default_comparison, default_recommendations),
        },
        "batchSelector": batch_selector,
        "stationComparison": current_comparison,
        "recommendations": current_recommendations,
        "trendDrawer": _build_trend_drawer(
            current_series,
            current_comparison,
            selected_hour,
            selected_batch_id,
        ),
    }


def build_manager_dashboard_payload(api_bundle: dict[str, Any]) -> dict[str, Any]:
    generated_at = _parse_generated_at(api_bundle)
    selection_meta = api_bundle.get("selectionMeta") or {}
    selected_date = str(selection_meta.get("selectedDate") or "")
    try:
        selected_hour = int(selection_meta.get("selectedHour"))
    except (TypeError, ValueError):
        selected_hour = generated_at.hour
    current_hour = max(1, min(24, selected_hour + 1))
    selected_window_start = _parse_selection_datetime(selection_meta.get("selectedHourStart"), generated_at)
    selected_window_end = _parse_selection_datetime(
        selection_meta.get("anchorTime") or selection_meta.get("selectedHourEnd"),
        generated_at,
    )
    selection_anchor = _parse_selection_datetime(
        selection_meta.get("anchorTime") or selection_meta.get("selectedHourEnd"),
        generated_at,
    )

    station_responsibility: dict[str, dict[str, str]] = {}
    station_telemetry: list[dict[str, Any]] = []
    hourly_trends: dict[str, dict[str, list[float]]] = {}

    predicted_ok_rates: list[float] = []
    utilizations: list[float] = []
    cycles: list[float] = []
    predicted_ng_total = 0
    warning_count = 0
    produced_total = 0
    planned_total = 0
    downtime_total = 0.0

    for line_id, meta in STATION_META.items():
        latest = (api_bundle.get("stationLatest") or {}).get(line_id, {})
        signal = latest.get("signal") or {}
        reference = latest.get("reference") or {}
        metric = latest.get("metric") or {}
        components = latest.get("components") or []
        diagnosis = (api_bundle.get("diagnosisLatest") or {}).get(line_id, {})
        alerts = (api_bundle.get("pendingAlerts") or {}).get(line_id, {})
        kpi = (api_bundle.get("kpiSummary") or {}).get(line_id, {})

        component_health: dict[str, str] = {}
        for item in components:
            key = item.get("component_key") or item.get("key")
            if key:
                component_health[key] = str(item.get("level") or item.get("level_text") or item.get("status") or "normal")

        pressure_bar = _number(signal.get("pressure_bar", metric.get("pressure_bar", reference.get("pressure_bar", 0))))
        flow_rate = _number(signal.get("flow_rate_ml_min", metric.get("flow_rate_ml_min", 0)))
        spray_width = _number(signal.get("spray_width_mm", metric.get("spray_width_mm", 0)))
        target_min = _number(reference.get("target_min_mm", metric.get("target_min_mm", 0)))
        target_max = _number(reference.get("target_max_mm", metric.get("target_max_mm", 0)))
        temperature = _number(signal.get("temperature_c", metric.get("temperature_c", 0)))
        availability = _number(metric.get("availability_pct", 0))
        maintainability = _number(metric.get("maintainability_pct", 0))
        clog_rate = _number(metric.get("clog_rate_pct", 0))
        quality_score = _number(metric.get("quality_score_pct", kpi.get("predicted_ok_rate", 0)))
        utilization = _number(metric.get("utilization_pct", kpi.get("line_utilization", 0)))
        cycle_time = _number(metric.get("cycle_time_sec", kpi.get("avg_cycle_time_s", 0)))

        baseline_pressure = _number(reference.get("baseline_pressure_bar", reference.get("target_pressure_bar", pressure_bar)))
        baseline_flow = _number(reference.get("baseline_flow_rate_ml_min", flow_rate))
        baseline_quality = _number(reference.get("baseline_quality_score_pct", 94.0))
        baseline_utilization = _number(reference.get("baseline_utilization_pct", 85.0))
        baseline_cycle = _number(reference.get("baseline_cycle_time_sec", reference.get("baseline_cycle_time_s", cycle_time)))

        normalized_diagnoses: list[dict[str, Any]] = []
        for item in diagnosis.get("diagnoses", []) or []:
            normalized_diagnoses.append(
                {
                    "category": item.get("category") or item.get("diagnosis_category") or item.get("source_type") or "diagnosis",
                    "stateLabel": item.get("state_label") or item.get("label") or item.get("message") or item.get("title") or "Diagnosis",
                    "severity": _normalize_severity(item.get("severity") or item.get("level") or item.get("risk_level")),
                    "confidence": _number(item.get("confidence"), 0.0),
                    "evidence": item.get("evidence") or item.get("reason") or item.get("detail") or "",
                    "action": item.get("suggestion") or item.get("action") or "",
                }
            )

        predicted_ok_rate = _number(kpi.get("predicted_ok_rate", quality_score))
        predicted_ng_pcs = round(_number(kpi.get("predicted_ng_pcs"), 0))
        predicted_ng_total += predicted_ng_pcs
        if predicted_ok_rate:
            predicted_ok_rates.append(predicted_ok_rate)
        if utilization:
            utilizations.append(utilization)
        if cycle_time:
            cycles.append(cycle_time)

        produced = _estimate_station_output(cycle_time, utilization, current_hour)
        planned = _estimate_station_output(baseline_cycle, baseline_utilization, current_hour)
        produced_total += produced
        planned_total += planned
        downtime_total += max(0.0, baseline_utilization - utilization) * current_hour * 0.6

        if _number(alerts.get("total")) > 0 or any(item.get("severity") != "normal" for item in normalized_diagnoses):
            warning_count += 1

        station_responsibility[line_id] = {
            "stationName": meta["stationName"],
            "layerName": meta["layerName"],
            "machineName": meta["machineName"],
            "engineerRole": meta["engineerRole"],
            "engineerEmail": meta["engineerEmail"],
        }

        station_telemetry.append(
            {
                "lineId": line_id,
                "timestamp": latest.get("timestamp") or api_bundle.get("generated_at") or generated_at.isoformat(),
                "recipeId": signal.get("recipe_name") or meta["recipeId"],
                "state": _normalize_state(signal.get("state") or latest.get("state") or ("warning" if alerts.get("total") else "running")),
                "metrics": {
                    "pressure_bar": pressure_bar,
                    "flow_rate_ml_min": flow_rate,
                    "spray_width_mm": spray_width,
                    "target_min_mm": target_min,
                    "target_max_mm": target_max,
                    "temperature_c": temperature,
                    "availability_pct": availability,
                    "maintainability_pct": maintainability,
                    "clog_rate_pct": clog_rate,
                    "quality_score_pct": quality_score,
                    "utilization_pct": utilization,
                    "cycle_time_sec": cycle_time,
                },
                "baseline": {
                    "pressure_bar": baseline_pressure,
                    "flow_rate_ml_min": baseline_flow,
                    "quality_score_pct": baseline_quality,
                    "utilization_pct": baseline_utilization,
                    "cycle_time_sec": baseline_cycle,
                },
                "componentHealth": {
                    "nozzle": component_health.get("nozzle", "normal"),
                    "filter_mesh": component_health.get("filter_mesh", "normal"),
                    "spray_width": component_health.get("spray_width", "normal"),
                },
                "predictedQuality": {
                    "ok_rate_pct": predicted_ok_rate or quality_score,
                    "ng_pcs_next_qc": predicted_ng_pcs,
                    "riskLevel": "warning" if alerts.get("total") else "normal",
                    "riskText": latest.get("risk_text")
                    or " ".join(item["stateLabel"] for item in normalized_diagnoses)
                    or "No active diagnosis.",
                },
                "projectDiagnosis": normalized_diagnoses,
                "projectAlerts": alerts.get("alerts", []) or [],
                "projectSchemaSource": "v1 bundle normalization",
            }
        )

        hourly_trends[line_id] = {
            "quality_score_pct": _normalize_quality_trend((api_bundle.get("qualityTrend") or {}).get(line_id)),
            "utilization_pct": _normalize_single_series_trend((api_bundle.get("utilizationTrend") or {}).get(line_id)),
            "cycle_time_sec": _normalize_single_series_trend((api_bundle.get("cycleTimeTrend") or {}).get(line_id)),
        }

    line_quality = round(_average(predicted_ok_rates), 1)  # 整線估算品質；取各站 predicted OK rate 平均
    line_utilization = round(_average(utilizations), 1)  # 整線平均稼動率；取各站 utilization 平均
    avg_cycle_time = round(_average(cycles), 1)  # 平均 cycle time；取 cycles 平均

    accuracy_items = list((api_bundle.get("predictionAccuracy") or {}).values())  # 取出 predictionAccuracy 內所有準確度資料
    accuracy_pct = _number(accuracy_items[0].get("accuracy_pct") if accuracy_items else 88.0, 88.0)  # 取第一筆 accuracy_pct；沒有資料時預設 88.0%
    prediction_error_pts = round(max(0.6, (100.0 - accuracy_pct) / 10.0), 1)  # 將準確率換算成預測誤差點數；最低 0.6

    actual_ok_rate = round(min(99.9, line_quality + min(1.5, prediction_error_pts * 0.4)), 1)  # 用估算品質加上誤差補正，推估 actual OK rate；最高 99.9%
    actual_ng_pcs = round(max(0, produced_total * (100.0 - actual_ok_rate) / 100.0))  # 用產出總數與 actual OK rate 推估 actual NG 件數
    predicted_ng_total = predicted_ng_total or round(max(0, produced_total * (100.0 - line_quality) / 100.0))  # 若 predicted_ng_total 沒值，則用產出總數與 line_quality 推估 NG 件數

    previous_efficiency = round(min(99.0, max(line_utilization + 4.0, _average([  # 推估上一期效率；至少比目前稼動率高 4.0，最高 99.0
        station["baseline"]["utilization_pct"] for station in station_telemetry  # 取各站 baseline utilization
    ]) or line_utilization)), 1)  # 若 baseline 平均無效，則 fallback 用 line_utilization

    previous_ok_rate = round(min(99.0, line_quality + 2.2), 1)  # 推估上一期 OK rate；目前品質加 2.2，最高 99.0
    previous_produced = max(produced_total, planned_total)  # 推估上一期產量；取目前產出與計畫產量較大者
    previous_actual_ng = round(max(0, previous_produced * (100.0 - previous_ok_rate) / 100.0))  # 用上一期產量與上一期 OK rate 推估上一期 NG 件數
    yesterday_efficiency = round(max(0.0, previous_efficiency - 1.5), 1)  # 推估昨日效率；上一期效率減 1.5，最低 0
    month_efficiency = round(_average([line_utilization, previous_efficiency]), 1)  # 推估本月效率；目前效率與上一期效率取平均
    last_month_efficiency = round(min(99.0, previous_efficiency + 1.8), 1)  # 推估上月效率；上一期效率加 1.8，最高 99.0

    quality_validation_date = selected_date or (selection_anchor - timedelta(days=1)).date().isoformat()  # 品質驗證日期；優先用 selected_date，否則用 anchor 前一天
    future_efficiency = round(max(0.0, line_utilization - (6.0 + warning_count * 2.0)), 1)  # 預測不處理時的未來效率；依 warning 數扣分
    future_ok_rate = round(max(0.0, line_quality - (2.4 + warning_count * 0.8)), 1)  # 預測不處理時的未來 OK rate；依 warning 數扣分
    future_lost_pcs = max(0, round(planned_total * 0.08 + warning_count * 40))  # 預測不處理時的未來損失件數；計畫量 8% 加上每個 warning 40 pcs
    future_extra_ng = max(0, round(predicted_ng_total * 0.35 + warning_count * 25))  # 預測不處理時的額外 NG 件數；目前 NG 的 35% 加上每個 warning 25 pcs

    quality_history = [
        {
            "qcDate": quality_validation_date,
            "workOrder": f"WO-{quality_validation_date.replace('-', '')}-001",
            "partNo": "Cover-A",
            "colorCode": "White",
            "okPcs": max(0, produced_total - actual_ng_pcs),
            "ngPcs": actual_ng_pcs,
            "defectTypes": ["orange peel", "spray width drift"] if warning_count else ["none"],
        },
        {
            "qcDate": (generated_at - timedelta(days=2)).date().isoformat(),
            "workOrder": f"WO-{(generated_at - timedelta(days=2)).date().isoformat().replace('-', '')}-001",
            "partNo": "Cover-A",
            "colorCode": "White",
            "okPcs": max(0, previous_produced - previous_actual_ng),
            "ngPcs": previous_actual_ng,
            "defectTypes": ["none"] if previous_actual_ng == 0 else ["clog trace"],
        },
    ]

    payload = {
        "responseMeta": {
            "requestId": f"manager-dashboard-{int(generated_at.timestamp())}",
            "source": str(api_bundle.get("source") or "Manager Dashboard API"),
            "apiVersion": "manager-dashboard-v1",
            "generatedAt": generated_at.isoformat(),
            "dataWindow": {
                "currentStart": selected_window_start.isoformat(),
                "currentEnd": selected_window_end.isoformat(),
                "historicalBaseline": "station baseline/reference values",
                "forecastHorizonDays": 7,
            },
            "dataCompletenessPct": 100,
            "weekProgress": f"{selection_anchor.isocalendar().week} week / manager dashboard aggregation",
            "selectedDate": selected_date,
            "selectedHour": selected_hour,
            "dateSource": selection_meta.get("dateSource") or "db_latest",
            "availableDates": selection_meta.get("availableDates") or [],
            "availableHours": selection_meta.get("availableHours") or [],
            "availableHoursByDate": selection_meta.get("availableHoursByDate") or {},
            "latestDate": selection_meta.get("latestDate"),
            "latestHour": selection_meta.get("latestHour"),
            "selectedBatchId": _clean_batch_id((api_bundle.get("managerDataset") or {}).get("selectedBatchId")),
        },
        "line": {
            "lineId": "spray_line_1",
            "lineName": "Spray Line Manager UI",
            "plant": "Smart Manufacturing Lab",
            "processFlow": [meta["layerName"] for meta in STATION_META.values()],
        },
        "currentBatch": api_bundle.get("currentBatch"),
        "stationResponsibility": station_responsibility,
        "stationTelemetry": station_telemetry,
        "hourlyTrends": hourly_trends,
        "productionKpi": {
            "currentPeriod": {
                "producedPcs": produced_total,
                "plannedPcs": planned_total,
                "estimatedEfficiencyPct": line_utilization,
                "estimatedOkRatePct": line_quality,
                "predictedNgPcs": predicted_ng_total,
                "estimatedDowntimeMin": round(downtime_total),
            },
            "previousPeriod": {
                "producedPcs": previous_produced,
                "actualEfficiencyPct": previous_efficiency,
                "actualOkRatePct": previous_ok_rate,
                "actualNgPcs": previous_actual_ng,
                "utilizationPct": previous_efficiency,
                "performancePct": round(max(0.0, min(100.0, 3600.0 / max(avg_cycle_time, 1.0))), 1),
            },
            "yesterdayActual": {
                "actualEfficiencyPct": yesterday_efficiency,
                "actualOkRatePct": actual_ok_rate,
                "actualNgPcs": actual_ng_pcs,
            },
            "todayEstimate": {
                "estimatedEfficiencyPct": line_utilization,
                "estimatedOkRatePct": line_quality,
                "predictedNgPcs": predicted_ng_total,
            },
            "monthToDate": {
                "estimatedEfficiencyPct": month_efficiency,
                "lastMonthSamePeriodActualEfficiencyPct": last_month_efficiency,
            },
            "apiKpiSummary": api_bundle.get("kpiSummary", {}),
        },
        "qualityValidation": {
            "validationDate": quality_validation_date,
            "predictedOkRatePct": line_quality,
            "actualOkRatePct": actual_ok_rate,
            "predictedNgPcs": predicted_ng_total,
            "actualNgPcs": actual_ng_pcs,
            "modelTrustLevel": "high" if prediction_error_pts <= 1.5 else "medium",
            "modelInputSource": "stationLatest + diagnosisLatest + pendingAlerts + kpiSummary + predictionAccuracy",
        },
        "qualityHistory": quality_history,
        "forecastNoAction": {
            "horizonDays": 7,
            "estimatedEfficiencyPct": future_efficiency,
            "estimatedOkRatePct": future_ok_rate,
            "extraLostProductionPcs": future_lost_pcs,
            "extraPredictedNgPcs": future_extra_ng,
            "riskText": (
                f"If no action is taken, {warning_count or 1} station(s) may keep quality below target "
                f"and add about {future_extra_ng} extra NG pieces within the next 7 days."
            ),
        },
    }

    payload["managerSummary"] = build_manager_summary(payload)
    payload["managerView"] = build_manager_view(api_bundle)
    payload["managerRecommendations"] = payload["managerView"]["recommendations"]
    return payload
