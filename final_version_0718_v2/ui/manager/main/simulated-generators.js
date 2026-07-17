// =======================================
// Simulated scenario generation and project-schema mock bundle assembly
// Split from the original dashboard.js to keep files focused and maintainable.
// =======================================
function getSimulatedDayMetricOffset(lineId, metricKey, dateKey = getActiveApiDateKey()) {
  const dayIndex = getSimulationDayIndexForDate(dateKey);
  const lineNo = Number(String(lineId || "1").replace(/\D/g, "")) || 1;
  const wave = Math.sin((dayIndex + 1) * (lineNo + 0.35));

  const ranges = {
    pressure_bar: 0.03,
    flow_rate_ml_min: 1.4,
    spray_width_mm: 0.8,
    temperature_c: 0.35,
    availability_pct: 0.6,
    maintainability_pct: 0.5,
    clog_rate_pct: 0.45,
    quality_score_pct: 0.35,
    utilization_pct: 0.8,
    cycle_time_sec: 0.45
  };

  return Number((wave * (ranges[metricKey] || 0)).toFixed(2));
}

function makeSimulatedStationMetric(lineId, scenario) {
  const base = structuredClone(SIMULATED_BASE_METRICS[lineId] || SIMULATED_BASE_METRICS.line_1);

  [
    "pressure_bar",
    "flow_rate_ml_min",
    "spray_width_mm",
    "temperature_c",
    "availability_pct",
    "maintainability_pct",
    "clog_rate_pct",
    "quality_score_pct",
    "utilization_pct",
    "cycle_time_sec"
  ].forEach(metricKey => {
    if (typeof base[metricKey] === "number") {
      base[metricKey] = Number((base[metricKey] + getSimulatedDayMetricOffset(lineId, metricKey)).toFixed(2));
    }
  });

  const override = scenario.overrides?.[lineId] || {};
  const componentOverride = override.componentHealth || {};
  return {
    ...base,
    ...override,
    componentHealth: {
      ...base.componentHealth,
      ...componentOverride
    }
  };
}

function makeTrendValue(lineId, metricKey, hour, currentHour, latestMetric, scenario) {
  const baseMetric = SIMULATED_BASE_METRICS[lineId] || SIMULATED_BASE_METRICS.line_1;
  const baseValue = Number(baseMetric[metricKey] || 0) + getSimulatedDayMetricOffset(lineId, metricKey);
  const latestValue = Number(latestMetric[metricKey] ?? baseValue);
  const active = scenario.activeLineId === lineId;
  const distanceToCurrent = currentHour - Number(hour || 0);
  const afterCurrent = Number(hour || 0) - currentHour;
  const wave = Math.sin((Number(hour || 0) + lineId.length) * 0.72) * 0.16;

  if (Number(hour) === currentHour) return latestValue;

  if (Number(hour) < currentHour) {
    if (!active) return baseValue + wave;
    const influence = Math.max(0, Math.min(1, (4 - distanceToCurrent) / 4));
    return baseValue + (latestValue - baseValue) * influence + wave;
  }

  if (!active) return baseValue + wave;

  const severityDirection = {
    quality_score_pct: -1,
    utilization_pct: -1,
    cycle_time_sec: 1
  }[metricKey] || 0;

  const continuation = Math.min(1.2, afterCurrent * 0.08);
  const futureValue = latestValue + (latestValue - baseValue) * continuation * 0.45;
  const drift = severityDirection * afterCurrent * 0.05;
  return futureValue + drift;
}

function makeSimulatedTrend(lineId, metricKey, currentHour, latestMetric, scenario) {
  return Array.from({ length: 24 }, (_, hour) => Number(makeTrendValue(lineId, metricKey, hour, currentHour, latestMetric, scenario).toFixed(1)));
}

function makeTrendApiPayload(lineId, values, currentHour, targetKey, targetValue) {
  const labels = Array.from({ length: 24 }, (_, hour) => `${String(hour).padStart(2, "0")}:00`);
  const basePayload = {
    line_id: lineId,
    timestep: "hour",
    labels,
    now_index: currentHour,
    forecast_start_index: currentHour + 1,
    cache_ttl_s: 30
  };

  if (targetKey === "quality") {
    return {
      ...basePayload,
      actual_series: labels.map((label, hour) => ({ hour, label, value: hour < currentHour ? values[hour] : null })).filter(row => row.value !== null),
      predicted_series: labels.map((label, hour) => ({ hour, label, value: hour === currentHour ? values[hour] : null })).filter(row => row.value !== null),
      forecast_series: labels.map((label, hour) => ({ hour, label, value: hour > currentHour ? values[hour] : null })).filter(row => row.value !== null),
      target: targetValue
    };
  }

  return {
    ...basePayload,
    series: labels.map((label, hour) => ({ hour, label, value: values[hour] })),
    target: targetKey === "utilization" ? targetValue : undefined,
    baseline_cycle_time_s: targetKey === "cycle" ? targetValue : undefined
  };
}

function buildSimulatedDiagnoses(lineId, latestMetric) {
  const diagnoses = [];
  const component = latestMetric.componentHealth || {};
  const flowDelta = latestMetric.flow_rate_ml_min - (latestMetric.baseline_flow_rate_ml_min || SIMULATED_BASE_METRICS[lineId]?.flow_rate_ml_min || 0);

  if ((component.nozzle && component.nozzle !== "normal") || latestMetric.clog_rate_pct >= 10) {
    diagnoses.push({
      category: "nozzle",
      state_label: "噴嘴可能堵塞 / 霧化不穩",
      severity: latestMetric.clog_rate_pct >= 14 ? "alarm" : "warning",
      confidence: 0.82,
      evidence: `堵塞率 ${latestMetric.clog_rate_pct}%；流量 ${latestMetric.flow_rate_ml_min} ml/min`
    });
  }

  if ((component.filter_mesh && component.filter_mesh !== "normal") || (latestMetric.clog_rate_pct >= 10 && flowDelta < -5)) {
    diagnoses.push({
      category: "filter_mesh",
      state_label: "濾網可能堵塞 / 供漆阻力變大",
      severity: latestMetric.clog_rate_pct >= 14 ? "alarm" : "warning",
      confidence: 0.78,
      evidence: `濾網狀態 ${component.filter_mesh || "normal"}；流量差 ${flowDelta.toFixed(1)} ml/min`
    });
  }

  if (latestMetric.spray_width_mm < latestMetric.target_min_mm || latestMetric.spray_width_mm > latestMetric.target_max_mm) {
    diagnoses.push({
      category: "spray_width",
      state_label: "噴幅偏離目標範圍",
      severity: "alarm",
      confidence: 0.9,
      evidence: `噴幅 ${latestMetric.spray_width_mm} mm；目標 ${latestMetric.target_min_mm}-${latestMetric.target_max_mm} mm`
    });
  }

  if (latestMetric.quality_score_pct < 92) {
    diagnoses.push({
      category: "quality",
      state_label: "品質分數低於管理線",
      severity: latestMetric.quality_score_pct < 90 ? "alarm" : "warning",
      confidence: 0.86,
      evidence: `品質分數 ${latestMetric.quality_score_pct}%；管理線 92%`
    });
  }

  if (latestMetric.utilization_pct < latestMetric.baseline_utilization_pct - 5) {
    diagnoses.push({
      category: "utilization",
      state_label: "稼動率低於 baseline",
      severity: latestMetric.utilization_pct < latestMetric.baseline_utilization_pct - 10 ? "alarm" : "warning",
      confidence: 0.74,
      evidence: `稼動率 ${latestMetric.utilization_pct}%；baseline ${latestMetric.baseline_utilization_pct}%`
    });
  }

  if (latestMetric.cycle_time_sec > latestMetric.baseline_cycle_time_sec * 1.08) {
    diagnoses.push({
      category: "cycle_time",
      state_label: "Cycle Time 高於 baseline",
      severity: latestMetric.cycle_time_sec > latestMetric.baseline_cycle_time_sec * 1.14 ? "alarm" : "warning",
      confidence: 0.72,
      evidence: `Cycle Time ${latestMetric.cycle_time_sec}s；baseline ${latestMetric.baseline_cycle_time_sec}s`
    });
  }

  return diagnoses;
}

function getSimulatedApiStatusText() {
  const currentHour = getSimulatedApiCurrentHour();
  const dateKey = getActiveApiDateKey();
  const scenario = getSimulatedScenario(currentHour, dateKey);
  return {
    uploadNo: SIMULATED_API_UPLOAD_INDEX + 1,
    dateKey: getActiveApiDateKey(),
    currentHour,
    generatedAt: getSimulatedGeneratedAt(),
    scenarioName: scenario.name,
    scenarioNote: scenario.note,
    intervalMs: CONFIG.SIMULATED_API_UPLOAD_INTERVAL_MS
  };
}


function makeSimulatedBatchInfo(dateKey, hour, scenario) {
  const normalizedDate = String(dateKey || getActiveApiDateKey());
  const dateCompact = normalizedDate.replace(/-/g, "");
  const currentHour = Math.max(0, Math.min(23, Number(hour || 0)));
  // In the simulation, assume one production batch spans about 2 hours.
  // Real API mode should replace this with the batch currently returned by DB/API.
  const batchSeq = Math.floor(currentHour / 2) + 1;
  const batchStartHour = Math.floor(currentHour / 2) * 2;
  const activeLineId = scenario?.activeLineId || "line_all";
  const lineSuffix = activeLineId === "line_all" ? "ALL" : activeLineId.replace("line_", "S").toUpperCase();
  const dayIndex = getSimulationDayIndexForDate(normalizedDate);
  const plannedPcs = 680 + ((dayIndex + batchSeq) % 5) * 24;
  const producedPcsToCurrent = Math.round(plannedPcs * (currentHour % 2 === 0 ? 0.52 : 1));
  const hourlyBatchCount = 2 + ((dayIndex + currentHour) % 3);
  const meta = PROJECT_STATION_META[activeLineId] || {};

  return {
    batchId: `B${dateCompact}-${String(batchSeq).padStart(3, "0")}-${lineSuffix}`,
    workOrderId: `WO-${dateCompact}-${String(batchSeq).padStart(3, "0")}`,
    batchDate: normalizedDate,
    batchHour: currentHour,
    batchWindow: `${String(batchStartHour).padStart(2, "0")}:00-${String(Math.min(23, batchStartHour + 1)).padStart(2, "0")}:59`,
    stationLineId: activeLineId,
    stationName: meta.stationName || "整線",
    processLayer: meta.layerName || "整線",
    recipeId: meta.recipeId || "MIXED-RECIPE",
    partNo: "Cover-A",
    colorCode: "White",
    plannedPcs,
    producedPcsToCurrent,
    hourlyBatchCount,
    qualityScoreSource: "hourly_all_batches_average",
    isPendingQc: true,
    source: "simulated API current_batch"
  };
}

function clampValue(value, min, max) {
  const number = Number(value || 0);
  return Math.max(min, Math.min(max, Number.isFinite(number) ? number : min));
}

function getActualQualityOffset(dateKey, lineId, hour) {
  const dayIndex = getSimulationDayIndexForDate(dateKey);
  const lineNo = Number(String(lineId || "1").replace(/\D/g, "")) || 1;
  const h = Number(hour || 0);
  const wave = Math.sin((dayIndex + 1) * 1.73 + lineNo * 0.91 + h * 0.41);
  const secondWave = Math.cos((dayIndex + 2) * 0.67 + lineNo * 1.21 + h * 0.18);
  return Number((wave * 0.42 + secondWave * 0.18).toFixed(2));
}

function getActualQualityScoreFromDb(predictedValue, dateKey, lineId, hour) {
  const predicted = Number(predictedValue || 0);
  if (!predicted) return 0;
  const offset = getActualQualityOffset(dateKey, lineId, hour);
  return Number(clampValue(predicted + offset, 0, 100).toFixed(1));
}

function actualizeQualityTrendFromDb(values, dateKey, lineId) {
  return Array.from({ length: 24 }, (_, hour) =>
    getActualQualityScoreFromDb(values?.[hour] ?? 0, dateKey, lineId, hour)
  );
}

function updateBatchToActualQc(batch, dateKey) {
  if (!batch) return batch;
  return {
    ...batch,
    batchDate: batch.batchDate || dateKey,
    isPendingQc: false,
    qualityScoreSource: "db_qc_result_hourly_batch_average",
    source: "DB qc_result actual batch snapshot"
  };
}

function actualizeDatabaseResponseFromDb(dbResponse, dateKey = null) {
  if (!dbResponse) return dbResponse;

  const db = JSON.parse(JSON.stringify(dbResponse));
  const targetDate = dateKey || getResponseDateKeyFromDb(db);
  const currentHour = getResponseHourFromDb(db);
  const stationValuesAtCurrentHour = [];

  db.qualityDataMode = {
    type: "actual",
    date: targetDate,
    source: "DB qc_result",
    qualityScoreField: "actual_quality_score_pct",
    aggregation: "hourly_all_batches_average",
    note: "隔天 QC 完成後，實際品質分數由 DB qc_result 重新查詢，不沿用前一天預測結果。"
  };

  if (db.responseMeta) {
    db.responseMeta.source = "Simulated DB qc_result actual";
    db.responseMeta.apiVersion = `${db.responseMeta.apiVersion || "manager-ui"}+actual-qc-db`;
  }

  if (db.currentBatch) {
    db.currentBatch = updateBatchToActualQc(db.currentBatch, targetDate);
  }

  if (db.productionKpi?.currentPeriod?.currentBatch) {
    db.productionKpi.currentPeriod.currentBatch = updateBatchToActualQc(db.productionKpi.currentPeriod.currentBatch, targetDate);
  }

  (db.stationTelemetry || []).forEach(station => {
    const lineId = station.lineId;
    const predictedTrend = db.hourlyTrends?.[lineId]?.quality_score_pct || [];
    const actualTrend = actualizeQualityTrendFromDb(predictedTrend, targetDate, lineId);

    if (!db.hourlyTrends) db.hourlyTrends = {};
    if (!db.hourlyTrends[lineId]) db.hourlyTrends[lineId] = {};
    db.hourlyTrends[lineId].quality_score_pct = actualTrend;
    db.hourlyTrends[lineId].quality_score_source = "DB qc_result hourly all-batch average";

    const actualAtCurrentHour = Number(actualTrend[currentHour] ?? station.metrics?.quality_score_pct ?? 0);
    stationValuesAtCurrentHour.push(actualAtCurrentHour);

    if (station.metrics) {
      station.metrics.quality_score_pct = actualAtCurrentHour;
      station.metrics.quality_score_type = "actual";
      station.metrics.quality_score_source = "DB qc_result hourly all-batch average";
    }

    if (station.predictedQuality) {
      station.predictedQuality.ok_rate_pct = actualAtCurrentHour;
      station.predictedQuality.riskText = `已完成 QC，${PROJECT_STATION_META[lineId]?.stationName || lineId} 實際品質分數由 DB qc_result 取得，不沿用當天預測值。`;
    }
  });

  const actualLineOkRate = Number(average(stationValuesAtCurrentHour.filter(value => value > 0)).toFixed(1));
  if (actualLineOkRate) {
    if (db.productionKpi?.currentPeriod) {
      db.productionKpi.currentPeriod.actualOkRatePct = actualLineOkRate;
      db.productionKpi.currentPeriod.estimatedOkRatePct = actualLineOkRate;
      db.productionKpi.currentPeriod.qualityScoreType = "actual";
      db.productionKpi.currentPeriod.qualityScoreSource = "DB qc_result hourly all-batch average";
    }

    if (db.productionKpi?.todayEstimate) {
      db.productionKpi.todayEstimate.actualOkRatePct = actualLineOkRate;
      db.productionKpi.todayEstimate.estimatedOkRatePct = actualLineOkRate;
    }

    if (db.qualityValidation) {
      db.qualityValidation.validationDate = targetDate;
      db.qualityValidation.actualOkRatePct = actualLineOkRate;
      db.qualityValidation.modelInputSource = "DB qc_result actual hourly batch average + previous prediction record";
      db.qualityValidation.modelTrustLevel = Math.abs(Number(db.qualityValidation.predictedOkRatePct || actualLineOkRate) - actualLineOkRate) <= 2 ? "良好" : "需觀察";
    }
  }

  return db;
}

function ensureHistoricalActualQualityData(dbResponse, dateKey = null) {
  const targetDate = dateKey || getResponseDateKeyFromDb(dbResponse);
  if (!targetDate) return dbResponse;
  if (targetDate >= getActiveApiDateKey()) return dbResponse;
  if (dbResponse?.qualityDataMode?.type === "actual") return dbResponse;
  return actualizeDatabaseResponseFromDb(dbResponse, targetDate);
}

function buildProjectSchemaMockBundle() {
  const currentHour = getSimulatedApiCurrentHour();
  const generatedAt = getSimulatedGeneratedAt();
  const currentDateKey = getActiveApiDateKey();
  const previousDateKey = addDaysToDateKey(currentDateKey, -1);
  const scenario = getSimulatedScenario(currentHour, currentDateKey);
  const currentBatch = makeSimulatedBatchInfo(currentDateKey, currentHour, scenario);
  const labels = Array.from({ length: 24 }, (_, hour) => `${String(hour).padStart(2, "0")}:00`);
  const lineIds = CONFIG.API_LINE_IDS;

  const stationLatest = {};
  const qualityTrend = {};
  const utilizationTrend = {};
  const cycleTimeTrend = {};
  const diagnosisLatest = {};
  const pendingAlerts = {};
  const kpiSummary = {};
  const predictionAccuracy = {};
  let warningCount = 0;

  lineIds.forEach(lineId => {
    const meta = PROJECT_STATION_META[lineId];
    const base = SIMULATED_BASE_METRICS[lineId] || SIMULATED_BASE_METRICS.line_1;
    const latest = makeSimulatedStationMetric(lineId, scenario);
    latest.baseline_flow_rate_ml_min = base.flow_rate_ml_min;
    latest.baseline_utilization_pct = base.utilization_pct;
    latest.baseline_cycle_time_sec = base.cycle_time_sec;
    latest.baseline_quality_score_pct = base.quality_score_pct;

    const qualitySeries = makeSimulatedTrend(lineId, "quality_score_pct", currentHour, latest, scenario);
    const utilizationSeries = makeSimulatedTrend(lineId, "utilization_pct", currentHour, latest, scenario);
    const cycleSeries = makeSimulatedTrend(lineId, "cycle_time_sec", currentHour, latest, scenario);

    stationLatest[lineId] = {
      line_id: lineId,
      window_id: `rw_${lineId}_${currentDateKey.replace(/-/g, "")}_${String(currentHour).padStart(2, "0")}20`,
      generated_at: generatedAt,
      signal: {
        pressure_bar: latest.pressure_bar,
        flow_rate_ml_min: latest.flow_rate_ml_min,
        spray_width_mm: latest.spray_width_mm,
        temperature_c: latest.temperature_c,
        recipe_name: meta.recipeId,
        state: latest.state
      },
      reference: {
        target_min_mm: latest.target_min_mm,
        target_max_mm: latest.target_max_mm,
        baseline_pressure_bar: base.pressure_bar,
        baseline_flow_rate_ml_min: base.flow_rate_ml_min,
        baseline_quality_score_pct: base.quality_score_pct,
        baseline_utilization_pct: base.utilization_pct,
        baseline_cycle_time_sec: base.cycle_time_sec
      },
      metric: {
        availability_pct: latest.availability_pct,
        maintainability_pct: latest.maintainability_pct,
        clog_rate_pct: latest.clog_rate_pct,
        quality_score_pct: latest.quality_score_pct,
        utilization_pct: latest.utilization_pct,
        cycle_time_sec: latest.cycle_time_sec,
        risk_text: scenario.activeLineId === lineId ? scenario.note : "目前站別指標在可接受範圍。"
      },
      components: [
        { component_key: "nozzle", label_zh: "噴嘴", label_en: "Nozzle", level: latest.componentHealth.nozzle, level_text: latest.componentHealth.nozzle },
        { component_key: "filter_mesh", label_zh: "濾網", label_en: "Filter mesh", level: latest.componentHealth.filter_mesh, level_text: latest.componentHealth.filter_mesh },
        { component_key: "spray_width", label_zh: "噴幅", label_en: "Spray width", level: latest.componentHealth.spray_width, level_text: latest.componentHealth.spray_width }
      ],
      cache_ttl_s: 30
    };

    qualityTrend[lineId] = makeTrendApiPayload(lineId, qualitySeries, currentHour, "quality", 92);
    utilizationTrend[lineId] = makeTrendApiPayload(lineId, utilizationSeries, currentHour, "utilization", base.utilization_pct);
    cycleTimeTrend[lineId] = makeTrendApiPayload(lineId, cycleSeries, currentHour, "cycle", base.cycle_time_sec);

    const diagnoses = buildSimulatedDiagnoses(lineId, latest);
    if (diagnoses.length) warningCount += 1;

    diagnosisLatest[lineId] = {
      line_id: lineId,
      generated_at: generatedAt,
      diagnoses,
      threshold_sources: ["station_latest.schema.json", "diagnosis_latest.schema.json", "baseline/reference"],
      cache_ttl_s: 30
    };

    pendingAlerts[lineId] = {
      line_id: lineId,
      total: diagnoses.filter(item => ["warning", "alarm"].includes(String(item.severity))).length,
      alerts: diagnoses.filter(item => ["warning", "alarm"].includes(String(item.severity))).map((item, index) => ({
        alert_id: `sim_alert_${lineId}_${currentHour}_${index + 1}`,
        source_type: "simulated_api_diagnosis",
        source_id: `${lineId}_${item.category}`,
        severity: item.severity,
        message: item.state_label,
        status: "pending"
      }))
    };

    kpiSummary[lineId] = {
      line_id: lineId,
      date: currentDateKey,
      predicted_ok_rate: latest.quality_score_pct,
      predicted_ng_pcs: Math.max(0, Math.round((100 - latest.quality_score_pct) * 18)),
      line_utilization: latest.utilization_pct,
      avg_cycle_time_s: latest.cycle_time_sec,
      delta: {
        quality_vs_baseline_pts: Number((latest.quality_score_pct - base.quality_score_pct).toFixed(1)),
        utilization_vs_baseline_pts: Number((latest.utilization_pct - base.utilization_pct).toFixed(1)),
        cycle_time_vs_baseline_s: Number((latest.cycle_time_sec - base.cycle_time_sec).toFixed(1))
      },
      cache_ttl_s: 30
    };

    predictionAccuracy[lineId] = {
      line_id: lineId,
      date: previousDateKey,
      yesterday_predicted_ok: MOCK_DATABASE_RESPONSE.qualityValidation.predictedOkRatePct,
      yesterday_actual_ok: MOCK_DATABASE_RESPONSE.qualityValidation.actualOkRatePct,
      prediction_error_pts: Math.abs(MOCK_DATABASE_RESPONSE.qualityValidation.actualOkRatePct - MOCK_DATABASE_RESPONSE.qualityValidation.predictedOkRatePct),
      model_accuracy: 98.8
    };
  });

  return {
    schemaSource: "Project-SprayLine / Dashboard v15 / DB Schema v2 / simulated API upload",
    generated_at: generatedAt,
    simulation: getSimulatedApiStatusText(),
    currentBatch,
    lineSummary: {
      line_id: "spray_line_1",
      timestamp: generatedAt,
      total: 3,
      normal: lineIds.length - warningCount,
      warning: warningCount,
      predict_risk: warningCount,
      cache_ttl_s: 30
    },
    stationLatest,
    qualityTrend,
    utilizationTrend,
    cycleTimeTrend,
    diagnosisLatest,
    pendingAlerts,
    kpiSummary,
    predictionAccuracy
  };
}

