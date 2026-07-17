// =======================================
// Project API normalization and fetch helpers
// Split from the original dashboard.js to keep files focused and maintainable.
// =======================================
let PROJECT_SCHEMA_MOCK_BUNDLE = null;

function getProjectSchemaMockBundle() {
  if (CONFIG.SIMULATED_API_ENABLED) {
    return buildProjectSchemaMockBundle();
  }

  if (!PROJECT_SCHEMA_MOCK_BUNDLE) {
    PROJECT_SCHEMA_MOCK_BUNDLE = buildProjectSchemaMockBundle();
  }
  return PROJECT_SCHEMA_MOCK_BUNDLE;
}

function normalizeProjectApiBundleToManagerDb(apiBundle) {
  if (!apiBundle || !apiBundle.stationLatest) return MOCK_DATABASE_RESPONSE;

  const apiDateKey = getDateKeyFromTimestamp(apiBundle.generated_at) || getActiveApiDateKey();
  const lineIds = CONFIG.API_LINE_IDS;
  const stationResponsibility = {};
  const stationTelemetry = [];
  const hourlyTrends = {};
  let warningCount = 0;
  let totalPredictedNg = 0;
  let predictedOkRates = [];
  let utilizations = [];
  let cycles = [];

  lineIds.forEach(lineId => {
    const meta = PROJECT_STATION_META[lineId];
    const latest = apiBundle.stationLatest[lineId] || {};
    const signal = latest.signal || {};
    const reference = latest.reference || {};
    const metric = latest.metric || {};
    const components = latest.components || [];
    const diagnosis = apiBundle.diagnosisLatest?.[lineId] || { diagnoses: [] };
    const alerts = apiBundle.pendingAlerts?.[lineId] || { total: 0, alerts: [] };
    const kpi = apiBundle.kpiSummary?.[lineId] || {};

    const componentHealth = components.reduce((acc, item) => {
      const key = item.component_key || item.key;
      if (key) acc[key] = item.level || item.level_text || item.status || "normal";
      return acc;
    }, {});

    const metrics = {
      pressure_bar: Number(signal.pressure_bar ?? metric.pressure_bar ?? reference.pressure_bar ?? 0),
      flow_rate_ml_min: Number(signal.flow_rate_ml_min ?? metric.flow_rate_ml_min ?? 0),
      spray_width_mm: Number(signal.spray_width_mm ?? metric.spray_width_mm ?? 0),
      target_min_mm: Number(reference.target_min_mm ?? metric.target_min_mm ?? 0),
      target_max_mm: Number(reference.target_max_mm ?? metric.target_max_mm ?? 0),
      temperature_c: Number(signal.temperature_c ?? metric.temperature_c ?? 0),
      availability_pct: Number(metric.availability_pct ?? 0),
      maintainability_pct: Number(metric.maintainability_pct ?? 0),
      clog_rate_pct: Number(metric.clog_rate_pct ?? 0),
      quality_score_pct: Number(metric.quality_score_pct ?? kpi.predicted_ok_rate ?? 0),
      utilization_pct: Number(metric.utilization_pct ?? kpi.line_utilization ?? 0),
      cycle_time_sec: Number(metric.cycle_time_sec ?? kpi.avg_cycle_time_s ?? 0)
    };

    const baseline = {
      pressure_bar: Number(reference.baseline_pressure_bar ?? reference.target_pressure_bar ?? metrics.pressure_bar),
      flow_rate_ml_min: Number(reference.baseline_flow_rate_ml_min ?? metrics.flow_rate_ml_min),
      quality_score_pct: Number(reference.baseline_quality_score_pct ?? 94),
      utilization_pct: Number(reference.baseline_utilization_pct ?? 85),
      cycle_time_sec: Number(reference.baseline_cycle_time_sec ?? reference.baseline_cycle_time_s ?? metrics.cycle_time_sec)
    };

    const normalizedDiagnoses = (diagnosis.diagnoses || []).map(item => ({
      category: item.category || item.diagnosis_category || item.source_type || "diagnosis",
      stateLabel: item.state_label || item.label || item.message || item.title || "診斷結果",
      severity: normalizeSeverity(item.severity || item.level || item.risk_level),
      confidence: Number(item.confidence ?? 0),
      evidence: item.evidence || item.reason || item.detail || "",
      action: item.suggestion || item.action || ""
    }));

    const predictedOkRate = Number(kpi.predicted_ok_rate ?? metric.quality_score_pct ?? 0);
    const predictedNgPcs = Number(kpi.predicted_ng_pcs ?? 0);
    totalPredictedNg += predictedNgPcs;
    if (predictedOkRate) predictedOkRates.push(predictedOkRate);
    if (metrics.utilization_pct) utilizations.push(metrics.utilization_pct);
    if (metrics.cycle_time_sec) cycles.push(metrics.cycle_time_sec);
    if (alerts.total > 0 || normalizedDiagnoses.some(item => item.severity !== "normal")) warningCount += 1;

    stationResponsibility[lineId] = {
      stationName: meta.stationName,
      layerName: meta.layerName,
      machineName: meta.machineName,
      engineerRole: meta.engineerRole,
      engineerEmail: meta.engineerEmail
    };

    stationTelemetry.push({
      lineId,
      timestamp: apiBundle.generated_at || latest.generated_at || new Date().toISOString(),
      recipeId: signal.recipe_name || meta.recipeId,
      state: normalizeState(signal.state || latest.state || (alerts.total > 0 ? "warning" : "running")),
      metrics,
      baseline,
      componentHealth: {
        nozzle: componentHealth.nozzle || "normal",
        filter_mesh: componentHealth.filter_mesh || "normal",
        spray_width: componentHealth.spray_width || "normal"
      },
      predictedQuality: {
        ok_rate_pct: predictedOkRate || metrics.quality_score_pct,
        ng_pcs_next_qc: predictedNgPcs,
        riskLevel: alerts.total > 0 ? "warning" : "normal",
        riskText: metric.risk_text || normalizedDiagnoses.map(item => item.stateLabel).join("；") || ""
      },
      projectDiagnosis: normalizedDiagnoses,
      projectAlerts: alerts.alerts || [],
      projectSchemaSource: "station_latest + diagnosis_latest + pending_alerts + kpi_summary"
    });

    hourlyTrends[lineId] = {
      quality_score_pct: normalizeQualityTrend(apiBundle.qualityTrend?.[lineId]),
      utilization_pct: normalizeSingleSeriesTrend(apiBundle.utilizationTrend?.[lineId]),
      cycle_time_sec: normalizeSingleSeriesTrend(apiBundle.cycleTimeTrend?.[lineId])
    };
  });

  const lineQuality = average(predictedOkRates);
  const lineUtilization = average(utilizations);
  const avgCycle = average(cycles);
  const predictionAccuracy = apiBundle.predictionAccuracy?.line_2 || Object.values(apiBundle.predictionAccuracy || {})[0] || {};

  return {
    responseMeta: {
      requestId: `project-schema-${Date.now()}`,
      source: CONFIG.SIMULATED_API_ENABLED ? "Simulated Project API" : (CONFIG.USE_MOCK_DATA ? "Project schema mock" : "Project API"),
      apiVersion: "dashboard-v15-db-schema-v2",
      generatedAt: apiBundle.generated_at || new Date().toISOString(),
      dataWindow: {
        currentStart: `${apiDateKey}T00:00:00+08:00`,
        currentEnd: apiBundle.generated_at || `${apiDateKey}T10:20:00+08:00`,
        historicalBaseline: "DB Schema v2 baseline/reference",
        forecastHorizonDays: 7
      },
      dataCompletenessPct: CONFIG.SIMULATED_API_ENABLED ? 100 : (CONFIG.USE_MOCK_DATA ? 65 : 100),
      weekProgress: "由 kpi_summary / trend API 決定"
    },
    line: {
      lineId: "spray_line_1",
      lineName: "Spray Line Manager UI",
      plant: "Demo Factory",
      processFlow: ["底色層", "顏色層", "保護層"]
    },
    currentBatch: apiBundle.currentBatch || null,
    stationResponsibility,
    stationTelemetry,
    hourlyTrends,
    projectApi: {
      schemaMap: PROJECT_SCHEMA_DB_MAP,
      rawBundle: apiBundle
    },
    productionKpi: {
      currentPeriod: {
        producedPcs: MOCK_DATABASE_RESPONSE.productionKpi.currentPeriod.producedPcs,
        plannedPcs: MOCK_DATABASE_RESPONSE.productionKpi.currentPeriod.plannedPcs,
        currentBatch: apiBundle.currentBatch || null,
        batchId: apiBundle.currentBatch?.batchId || "",
        workOrderId: apiBundle.currentBatch?.workOrderId || "",
        estimatedEfficiencyPct: lineUtilization || MOCK_DATABASE_RESPONSE.productionKpi.currentPeriod.estimatedEfficiencyPct,
        estimatedOkRatePct: lineQuality || MOCK_DATABASE_RESPONSE.productionKpi.currentPeriod.estimatedOkRatePct,
        predictedNgPcs: totalPredictedNg || MOCK_DATABASE_RESPONSE.productionKpi.currentPeriod.predictedNgPcs,
        estimatedDowntimeMin: MOCK_DATABASE_RESPONSE.productionKpi.currentPeriod.estimatedDowntimeMin
      },
      previousPeriod: MOCK_DATABASE_RESPONSE.productionKpi.previousPeriod,
      yesterdayActual: MOCK_DATABASE_RESPONSE.productionKpi.yesterdayActual,
      todayEstimate: {
        estimatedEfficiencyPct: lineUtilization || MOCK_DATABASE_RESPONSE.productionKpi.todayEstimate.estimatedEfficiencyPct,
        estimatedOkRatePct: lineQuality || MOCK_DATABASE_RESPONSE.productionKpi.todayEstimate.estimatedOkRatePct,
        predictedNgPcs: totalPredictedNg || MOCK_DATABASE_RESPONSE.productionKpi.todayEstimate.predictedNgPcs
      },
      monthToDate: MOCK_DATABASE_RESPONSE.productionKpi.monthToDate,
      apiKpiSummary: apiBundle.kpiSummary
    },
    qualityValidation: {
      validationDate: predictionAccuracy.date || MOCK_DATABASE_RESPONSE.qualityValidation.validationDate,
      predictedOkRatePct: Number(predictionAccuracy.yesterday_predicted_ok ?? MOCK_DATABASE_RESPONSE.qualityValidation.predictedOkRatePct),
      actualOkRatePct: Number(predictionAccuracy.yesterday_actual_ok ?? MOCK_DATABASE_RESPONSE.qualityValidation.actualOkRatePct),
      predictedNgPcs: MOCK_DATABASE_RESPONSE.qualityValidation.predictedNgPcs,
      actualNgPcs: MOCK_DATABASE_RESPONSE.qualityValidation.actualNgPcs,
      modelTrustLevel: Number(predictionAccuracy.prediction_error_pts ?? 99) <= 2 ? "良好" : "需觀察",
      modelInputSource: "qc_result + ml_prediction_result + prediction_accuracy.schema.json"
    },
    qualityHistory: MOCK_DATABASE_RESPONSE.qualityHistory,
    forecastNoAction: MOCK_DATABASE_RESPONSE.forecastNoAction
  };
}

function normalizeState(state) {
  const value = String(state || "").toLowerCase();
  if (["warning", "alarm", "fault", "down"].includes(value)) return "warning";
  return "running";
}

function normalizeSeverity(value) {
  const text = String(value || "").toLowerCase();
  if (["alarm", "critical", "danger", "緊急", "危險"].includes(text)) return "alarm";
  if (["warning", "warn", "警告"].includes(text)) return "warning";
  if (["monitor", "observe", "觀察"].includes(text)) return "monitor";
  return "normal";
}

function normalizeQualityTrend(trend) {
  const values = Array(24).fill(null);
  if (!trend) return values.map(value => Number(value || 0));
  ["actual_series", "predicted_series", "forecast_series"].forEach(key => {
    (trend[key] || []).forEach((row, index) => {
      const hour = getTrendRowHour(row, index);
      const value = getTrendRowValue(row);
      if (hour >= 0 && hour < 24 && value !== null) values[hour] = value;
    });
  });
  return values.map((value, hour) => Number(value ?? values[Math.max(0, hour - 1)] ?? 0));
}

function normalizeSingleSeriesTrend(trend) {
  const values = Array(24).fill(null);
  if (!trend) return values.map(value => Number(value || 0));
  (trend.series || []).forEach((row, index) => {
    const hour = getTrendRowHour(row, index);
    const value = getTrendRowValue(row);
    if (hour >= 0 && hour < 24 && value !== null) values[hour] = value;
  });
  return values.map((value, hour) => Number(value ?? values[Math.max(0, hour - 1)] ?? 0));
}

function getTrendRowHour(row, fallbackIndex) {
  const raw = row.hour ?? row.index ?? row.t ?? row.label ?? row.timestamp ?? fallbackIndex;
  const match = String(raw).match(/(\d{1,2})/);
  const hour = match ? Number(match[1]) : Number(fallbackIndex);
  return Number.isFinite(hour) ? Math.max(0, Math.min(23, hour)) : 0;
}

function getTrendRowValue(row) {
  const candidates = [row.value, row.quality_score_pct, row.predicted_ok_rate, row.ok_rate, row.utilization_pct, row.cycle_time_sec, row.cycle_time_s, row.y];
  const found = candidates.find(value => value !== undefined && value !== null && value !== "");
  return found === undefined ? null : Number(found);
}

function buildProjectApiUrl(route, lineId, params = {}) {
  const base = String(CONFIG.API_BASE_URL || "").replace(/\/$/, "");
  let url = `${base}${route.replace("{line_id}", encodeURIComponent(lineId))}`;
  const query = new URLSearchParams(params);
  return query.toString() ? `${url}?${query.toString()}` : url;
}

async function fetchJsonOrNull(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}: ${url}`);
  return response.json();
}

async function fetchProjectSchemaApiBundle() {
  if (CONFIG.SIMULATED_API_ENABLED) return getProjectSchemaMockBundle();
  if (CONFIG.USE_MOCK_DATA || !CONFIG.API_BASE_URL) return getProjectSchemaMockBundle();

  const lineIds = CONFIG.API_LINE_IDS;
  const bundle = {
    schemaSource: "Project-SprayLine / Dashboard v15 / DB Schema v2",
    generated_at: new Date().toISOString(),
    stationLatest: {},
    qualityTrend: {},
    utilizationTrend: {},
    cycleTimeTrend: {},
    diagnosisLatest: {},
    pendingAlerts: {},
    kpiSummary: {},
    predictionAccuracy: {}
  };

  await Promise.all(lineIds.map(async lineId => {
    const apiDate = selectedReportDate || getActiveApiDateKey();
    const params = { timestep: CONFIG.API_TREND_TIMESTEP, date: apiDate };
    const [station, quality, utilization, cycle, diagnosis, alerts, kpi, accuracy] = await Promise.all([
      fetchJsonOrNull(buildProjectApiUrl("/api/v1/lines/{line_id}/stations/latest", lineId)),
      fetchJsonOrNull(buildProjectApiUrl("/api/v1/lines/{line_id}/charts/quality-trend", lineId, params)),
      fetchJsonOrNull(buildProjectApiUrl("/api/v1/lines/{line_id}/charts/utilization-trend", lineId, params)),
      fetchJsonOrNull(buildProjectApiUrl("/api/v1/lines/{line_id}/charts/cycle-time-trend", lineId, params)),
      fetchJsonOrNull(buildProjectApiUrl("/api/v1/lines/{line_id}/diagnosis/latest", lineId)),
      fetchJsonOrNull(buildProjectApiUrl("/api/v1/lines/{line_id}/alerts/pending", lineId)),
      fetchJsonOrNull(buildProjectApiUrl("/api/v1/lines/{line_id}/kpi", lineId, { date: apiDate })),
      fetchJsonOrNull(buildProjectApiUrl("/api/v1/lines/{line_id}/prediction-accuracy", lineId, { date: apiDate }))
    ]);

    bundle.stationLatest[lineId] = station;
    bundle.qualityTrend[lineId] = quality;
    bundle.utilizationTrend[lineId] = utilization;
    bundle.cycleTimeTrend[lineId] = cycle;
    bundle.diagnosisLatest[lineId] = diagnosis;
    bundle.pendingAlerts[lineId] = alerts;
    bundle.kpiSummary[lineId] = kpi;
    bundle.predictionAccuracy[lineId] = accuracy;
  }));

  return bundle;
}

function getHourlyValuesFromDb(lineId, metricKey) {
  const db = currentDatabaseResponse || MOCK_DATABASE_RESPONSE;
  const values = db?.hourlyTrends?.[lineId]?.[metricKey];
  if (Array.isArray(values) && values.length) return values;
  return null;
}

hydrateSimulatedApiStateFromLocalStorage();

// ==============================
// Manager UI state
// ==============================

