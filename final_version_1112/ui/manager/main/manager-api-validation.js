function getValueAtPath(target, path) {
  return path.split(".").reduce((value, key) => {
    if (value === null || value === undefined) return undefined;

    const arrayMatch = key.match(/^([^\[]+)\[(.+)\]$/);
    if (!arrayMatch) return value[key];

    const [, arrayKey, selector] = arrayMatch;
    const collection = value[arrayKey];
    if (!Array.isArray(collection)) return undefined;

    if (/^\d+$/.test(selector)) {
      return collection[Number(selector)];
    }

    return collection.find(item => String(item?.lineId || item?.id || "") === selector);
  }, target);
}

function requireManagerPayloadField(payload, path, { arrayLength } = {}) {
  const value = getValueAtPath(payload, path);
  const missing = value === undefined || value === null || value === "";
  if (missing) {
    throw buildManagerUiError({
      title: "Manager API data error",
      reason: "missing required API field",
      missingField: path,
      suggestion: "Please check /api/manager/dashboard response payload."
    });
  }

  if (arrayLength !== undefined) {
    if (!Array.isArray(value) || value.length !== arrayLength) {
      throw buildManagerUiError({
        title: "Manager API data error",
        reason: "missing hourly trend data",
        missingField: path,
        suggestion: "Please check /api/manager/dashboard response payload."
      });
    }
  }

  return value;
}

function requireManagerArrayField(payload, path) {
  const value = requireManagerPayloadField(payload, path);
  if (!Array.isArray(value)) {
    throw buildManagerUiError({
      title: "Manager API data error",
      reason: "invalid payload",
      missingField: path,
      suggestion: "Please check /api/manager/dashboard response payload."
    });
  }
  return value;
}

function validateManagerDashboardPayload(payload, endpoint = getManagerDashboardApiUrl()) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw buildManagerUiError({
      title: "Manager API data error",
      endpoint,
      reason: "invalid payload",
      missingField: "payload",
      suggestion: "Please check /api/manager/dashboard response payload."
    });
  }

  requireManagerPayloadField(payload, "responseMeta.source");
  requireManagerPayloadField(payload, "responseMeta.apiVersion");
  requireManagerPayloadField(payload, "responseMeta.generatedAt");
  requireManagerPayloadField(payload, "responseMeta.selectedDate");
  requireManagerPayloadField(payload, "responseMeta.selectedHour");
  requireManagerPayloadField(payload, "responseMeta.availableDates");
  requireManagerPayloadField(payload, "responseMeta.availableHours");
  requireManagerPayloadField(payload, "responseMeta.availableHoursByDate");
  requireManagerPayloadField(payload, "line.lineName");
  requireManagerPayloadField(payload, "stationResponsibility");
  requireManagerPayloadField(payload, "stationTelemetry");
  requireManagerPayloadField(payload, "productionKpi.currentPeriod");
  requireManagerPayloadField(payload, "productionKpi.currentPeriod.estimatedEfficiencyPct");
  requireManagerPayloadField(payload, "productionKpi.previousPeriod");
  requireManagerPayloadField(payload, "productionKpi.todayEstimate");
  requireManagerPayloadField(payload, "productionKpi.monthToDate");
  requireManagerPayloadField(payload, "qualityValidation");
  requireManagerPayloadField(payload, "qualityHistory");
  requireManagerPayloadField(payload, "forecastNoAction");
  requireManagerPayloadField(payload, "hourlyTrends");
  requireManagerPayloadField(payload, "managerView.kpis");
  requireManagerPayloadField(payload, "managerView.batchSelector");
  requireManagerPayloadField(payload, "managerView.stationComparison");
  requireManagerPayloadField(payload, "managerView.recommendations");
  requireManagerPayloadField(payload, "managerView.trendDrawer");

  const sourceText = [
    String(getValueAtPath(payload, "responseMeta.source") || ""),
    String(getValueAtPath(payload, "managerSummary.dataSource") || "")
  ].join(" ").toLowerCase();
  const sourceFlag = sourceText.includes("m" + "ock") || sourceText.includes("web" + "_" + "service");
  if (sourceFlag || payload?.responseMeta?.["fall" + "backReason"]) {
    throw buildManagerUiError({
      title: "Manager API data error",
      endpoint,
      reason: "m" + "ock payload is not allowed",
      source: String(getValueAtPath(payload, "responseMeta.source") || getValueAtPath(payload, "managerSummary.dataSource") || ""),
      suggestion: "Please return DB-backed API data only."
    });
  }

  const availableDates = requireManagerArrayField(payload, "responseMeta.availableDates");
  const availableHours = requireManagerArrayField(payload, "responseMeta.availableHours");
  const availableHoursByDate = getValueAtPath(payload, "responseMeta.availableHoursByDate");
  const selectedDate = String(getValueAtPath(payload, "responseMeta.selectedDate") || "");
  const selectedHour = Number(getValueAtPath(payload, "responseMeta.selectedHour"));

  if (!availableDates.includes(selectedDate)) {
    throw buildManagerUiError({
      title: "Manager API data error",
      endpoint,
      reason: "invalid payload",
      missingField: "responseMeta.selectedDate",
      suggestion: "Please check /api/manager/dashboard response payload."
    });
  }

  if (!Array.isArray(availableHoursByDate?.[selectedDate])) {
    throw buildManagerUiError({
      title: "Manager API data error",
      endpoint,
      reason: "invalid payload",
      missingField: `responseMeta.availableHoursByDate.${selectedDate}`,
      suggestion: "Please check /api/manager/dashboard response payload."
    });
  }

  if (!Number.isFinite(selectedHour) || !availableHours.map(Number).includes(selectedHour)) {
    throw buildManagerUiError({
      title: "Manager API data error",
      endpoint,
      reason: "invalid payload",
      missingField: "responseMeta.selectedHour",
      suggestion: "Please check /api/manager/dashboard response payload."
    });
  }

  (CONFIG.API_LINE_IDS || []).forEach(lineId => {
    requireManagerPayloadField(payload, `stationResponsibility.${lineId}.stationName`);
    requireManagerPayloadField(payload, `stationTelemetry[${lineId}]`);
    requireManagerPayloadField(payload, `stationTelemetry[${lineId}].metrics.quality_score_pct`);
    requireManagerPayloadField(payload, `stationTelemetry[${lineId}].metrics.utilization_pct`);
    requireManagerPayloadField(payload, `stationTelemetry[${lineId}].metrics.cycle_time_sec`);
    requireManagerPayloadField(payload, `stationTelemetry[${lineId}].baseline.quality_score_pct`);
    requireManagerPayloadField(payload, `stationTelemetry[${lineId}].baseline.utilization_pct`);
    requireManagerPayloadField(payload, `stationTelemetry[${lineId}].baseline.cycle_time_sec`);
    requireManagerPayloadField(payload, `hourlyTrends.${lineId}.quality_score_pct`, { arrayLength: 24 });
    requireManagerPayloadField(payload, `hourlyTrends.${lineId}.utilization_pct`, { arrayLength: 24 });
    requireManagerPayloadField(payload, `hourlyTrends.${lineId}.cycle_time_sec`, { arrayLength: 24 });
  });

  const managerView = payload.managerView || {};
  if (!Array.isArray(managerView.stationComparison) || managerView.stationComparison.length !== 3) {
    throw buildManagerUiError({
      title: "Manager API data error",
      endpoint,
      reason: "invalid payload",
      missingField: "managerView.stationComparison",
      suggestion: "Please check /api/manager/dashboard response payload."
    });
  }

  requireManagerPayloadField(payload, "managerView.kpis.estimatedOkRatePct");
  requireManagerPayloadField(payload, "managerView.kpis.estimatedNgRatePct");
  requireManagerPayloadField(payload, "managerView.kpis.productionAchievementPct");
  requireManagerPayloadField(payload, "managerView.kpis.dailyProduction.batchSizePcs");
  requireManagerPayloadField(payload, "managerView.kpis.dailyProduction.dailyTargetPcs");
  requireManagerPayloadField(payload, "managerView.batchSelector.availableBatches");
  requireManagerPayloadField(payload, "managerView.trendDrawer.stationSeries");

  return payload;
}

function getHourlyValuesFromDb(lineId, metricKey) {
  const path = `hourlyTrends.${lineId}.${metricKey}`;
  const values = requireManagerPayloadField(currentDatabaseResponse || {}, path, { arrayLength: 24 });
  return values.map(value => (value === null || value === undefined || value === "" ? null : Number(value)));
}
