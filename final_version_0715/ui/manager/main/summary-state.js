// =======================================
// Application state, summary builders, and shared formatting utilities
// Split from the original dashboard.js to keep files focused and maintainable.
// =======================================
const CATEGORY_LIST = [
  { key: "monitor", label: "狀態實時監控表" },
  { key: "validation", label: "預測驗證" }
];

let activeCategory = "monitor";
let lastDataUpdateAt = new Date();
let latestDataError = "";
let selectedReportDate = getInitialReportDateKey();
let selectedReportHourMode = "live";
let selectedReportHour = null;
let isRecommendationDrawerOpen = false;
let isStationDetailOpen = false;
let selectedDetailLineId = "";

let currentDatabaseResponse = MOCK_DATABASE_RESPONSE;
let MANAGER_MOCK_SUMMARY = getManagerSummaryFromDatabase(currentDatabaseResponse);
let ASSIGNMENT_CARDS = MANAGER_MOCK_SUMMARY.assignments;
let ACCEPTANCE_CHECKLIST = MANAGER_MOCK_SUMMARY.acceptanceChecklist;
let CURRENT_RECOMMENDATION_ASSIGNMENTS = [];

// ==============================
// Data transformation layer
// Database/API response -> Manager report
// ==============================

function buildManagerReportFromDatabase(db) {
  const production = db.productionKpi;
  const stationEvaluations = db.stationTelemetry.map(station => evaluateStationRisk(db, station));
  stationEvaluations.sort((a, b) => b.riskScore - a.riskScore);

  const mainEvaluation = stationEvaluations[0];
  const mainStation = mainEvaluation.station;
  const responsibility = mainEvaluation.responsibility;
  const validation = db.qualityValidation;

  const efficiencyChange = production.currentPeriod.estimatedEfficiencyPct - production.previousPeriod.actualEfficiencyPct;
  const todayVsYesterdayChange = production.todayEstimate.estimatedEfficiencyPct - production.yesterdayActual.actualEfficiencyPct;
  const monthChange = production.monthToDate.estimatedEfficiencyPct - production.monthToDate.lastMonthSamePeriodActualEfficiencyPct;
  const lostProductionPcs = Math.max(0, production.previousPeriod.producedPcs - production.currentPeriod.producedPcs);
  const extraPredictedNgPcs = Math.max(0, production.currentPeriod.predictedNgPcs - production.previousPeriod.actualNgPcs);

  const assignments = buildAssignmentsFromStations(db, stationEvaluations);

  return {
    dataSource: db.responseMeta.source,
    apiVersion: db.responseMeta.apiVersion,
    generatedAt: db.responseMeta.generatedAt,
    rawDatabaseResponse: db,

    lineName: db.line.lineName,
    mainIssueLineId: mainStation.lineId,
    mainIssueStation: responsibility.stationName,
    mainIssueRobot: responsibility.machineName,
    mainIssueProcess: responsibility.layerName,
    responsibleEngineer: responsibility.engineerRole,
    responsibleEmail: responsibility.engineerEmail,
    mainStationState: mainStation.state,
    mainStationRecipe: mainStation.recipeId,
    mainStationMetrics: mainStation.metrics,
    mainStationBaseline: mainStation.baseline,
    mainStationComponents: mainStation.componentHealth,
    mainStationRiskScore: mainEvaluation.riskScore,
    mainRiskReasons: mainEvaluation.reasons,
    stationEvaluations,

    estimatedThisWeekEfficiency: production.currentPeriod.estimatedEfficiencyPct,
    lastWeekActualEfficiency: production.previousPeriod.actualEfficiencyPct,
    efficiencyChange,

    todayEstimatedEfficiency: production.todayEstimate.estimatedEfficiencyPct,
    yesterdayActualEfficiency: production.yesterdayActual.actualEfficiencyPct,
    todayVsYesterdayChange,

    monthToDateEstimatedEfficiency: production.monthToDate.estimatedEfficiencyPct,
    lastMonthSamePeriodActualEfficiency: production.monthToDate.lastMonthSamePeriodActualEfficiencyPct,
    monthChange,

    predictedOkRate: production.currentPeriod.estimatedOkRatePct,
    lastWeekActualOkRate: production.previousPeriod.actualOkRatePct,
    predictedNgPcs: production.currentPeriod.predictedNgPcs,
    lastWeekActualNgPcs: production.previousPeriod.actualNgPcs,

    utilization: mainStation.metrics.utilization_pct,
    lastWeekUtilization: mainStation.baseline.utilization_pct,

    performance: estimatePerformancePct(mainStation),
    lastWeekPerformance: estimateBaselinePerformancePct(mainStation),

    producedPcs: production.currentPeriod.producedPcs,
    lastWeekProducedPcs: production.previousPeriod.producedPcs,

    lostProductionPcs,
    extraPredictedNgPcs,
    extraDowntimeMinutes: production.currentPeriod.estimatedDowntimeMin,

    futureNoActionEfficiency: db.forecastNoAction.estimatedEfficiencyPct,
    futureNoActionOkRate: db.forecastNoAction.estimatedOkRatePct,
    futureLostPcs: db.forecastNoAction.extraLostProductionPcs,
    futureExtraNgPcs: db.forecastNoAction.extraPredictedNgPcs,
    futureRiskText: db.forecastNoAction.riskText,

    dataStatus: {
      todayCompleteness: db.responseMeta.dataCompletenessPct,
      weekProgress: db.responseMeta.weekProgress,
      source: db.responseMeta.source,
      apiVersion: db.responseMeta.apiVersion,
      dataWindow: db.responseMeta.dataWindow
    },

    predictionValidation: {
      yesterdayPredictedOkRate: validation.predictedOkRatePct,
      yesterdayActualOkRate: validation.actualOkRatePct,
      predictionErrorPts: Math.abs(validation.actualOkRatePct - validation.predictedOkRatePct),
      yesterdayPredictedNgPcs: validation.predictedNgPcs,
      yesterdayActualNgPcs: validation.actualNgPcs,
      modelTrustLevel: validation.modelTrustLevel,
      modelInputSource: validation.modelInputSource
    },

    assignments,
    acceptanceChecklist: buildAcceptanceChecklist(mainEvaluation, assignments)
  };
}

function getManagerSummaryFromDatabase(db) {
  if (db && db.managerSummary) {
    return {
      ...db.managerSummary,
      rawDatabaseResponse: db
    };
  }

  return buildManagerReportFromDatabase(db || MOCK_DATABASE_RESPONSE);
}

function evaluateStationRisk(db, station) {
  const responsibility = db.stationResponsibility[station.lineId];
  const metrics = station.metrics;
  const baseline = station.baseline;

  const qualityRisk = Math.max(0, (94 - metrics.quality_score_pct) * 4.2);
  const clogRisk = Math.max(0, (metrics.clog_rate_pct - 5) * 3.2);
  const utilizationRisk = Math.max(0, (baseline.utilization_pct - metrics.utilization_pct) * 2.0);
  const cycleRisk = Math.max(0, ((metrics.cycle_time_sec - baseline.cycle_time_sec) / baseline.cycle_time_sec) * 100 * 1.8);
  const sprayRisk = getSprayWidthStatus(station) === "out" ? 16 : getSprayWidthStatus(station) === "near" ? 6 : 0;
  const flowRisk = Math.max(0, ((baseline.flow_rate_ml_min - metrics.flow_rate_ml_min) / baseline.flow_rate_ml_min) * 100 * 1.4);
  const pressureRisk = Math.max(0, ((Math.abs(metrics.pressure_bar - baseline.pressure_bar) / baseline.pressure_bar) * 100 - 5) * 1.1);

  const riskScore = Math.round(
    qualityRisk + clogRisk + utilizationRisk + cycleRisk + sprayRisk + flowRisk + pressureRisk
  );

  return {
    station,
    responsibility,
    riskScore,
    riskLevel: getRiskLevelFromScore(riskScore),
    reasons: buildStationRiskReasons(station)
  };
}

function getRiskLevelFromScore(score) {
  if (score >= 70) return "緊急";
  if (score >= 35) return "警告";
  return "正常";
}

function buildStationRiskReasons(station) {
  const metrics = station.metrics;
  const baseline = station.baseline;
  const reasons = [];

  if (metrics.quality_score_pct < 92) {
    reasons.push(`品質分數 ${metrics.quality_score_pct.toFixed(1)}%，低於警戒值 92%。`);
  }

  if (metrics.clog_rate_pct >= 10) {
    reasons.push(`堵塞率 ${metrics.clog_rate_pct.toFixed(1)}%，噴嘴或濾網需優先確認。`);
  }

  if (metrics.utilization_pct < baseline.utilization_pct - 5) {
    reasons.push(`稼動率 ${metrics.utilization_pct.toFixed(1)}%，比基準 ${baseline.utilization_pct.toFixed(1)}% 低。`);
  }

  if (metrics.cycle_time_sec > baseline.cycle_time_sec * 1.08) {
    reasons.push(`Cycle Time ${metrics.cycle_time_sec.toFixed(1)} 秒，比基準 ${baseline.cycle_time_sec.toFixed(1)} 秒變慢。`);
  }

  if (metrics.spray_width_mm < metrics.target_min_mm || metrics.spray_width_mm > metrics.target_max_mm) {
    reasons.push(`噴幅 ${metrics.spray_width_mm.toFixed(0)} mm，超出目標 ${metrics.target_min_mm}-${metrics.target_max_mm} mm。`);
  }

  if (metrics.flow_rate_ml_min < baseline.flow_rate_ml_min * 0.92) {
    reasons.push(`流量 ${metrics.flow_rate_ml_min.toFixed(0)} ml/min，低於基準 ${baseline.flow_rate_ml_min.toFixed(0)} ml/min。`);
  }

  if (Math.abs(metrics.pressure_bar - baseline.pressure_bar) / baseline.pressure_bar > 0.08) {
    reasons.push(`壓力 ${metrics.pressure_bar.toFixed(2)} bar，和基準 ${baseline.pressure_bar.toFixed(2)} bar 偏差較大。`);
  }

  if (!reasons.length) {
    reasons.push("目前沒有明顯異常，但仍需持續觀察下一次資料更新。");
  }

  return reasons;
}

function getSprayWidthStatus(station) {
  const metrics = station.metrics;
  if (metrics.spray_width_mm < metrics.target_min_mm || metrics.spray_width_mm > metrics.target_max_mm) return "out";

  const margin = Math.min(
    Math.abs(metrics.spray_width_mm - metrics.target_min_mm),
    Math.abs(metrics.target_max_mm - metrics.spray_width_mm)
  );

  return margin <= 2 ? "near" : "normal";
}

function estimatePerformancePct(station) {
  const value = (station.baseline.cycle_time_sec / station.metrics.cycle_time_sec) * 100;
  return Math.max(0, Math.min(100, value));
}

function estimateBaselinePerformancePct(station) {
  return 100;
}

function buildAssignmentsFromStations(db, stationEvaluations) {
  return stationEvaluations.map((evaluation, index) => {
    const responsibility = evaluation.responsibility;
    const isMainIssue = index === 0;
    const priority = `P${index + 1}`;
    const stationName = responsibility.stationName;
    const layerName = responsibility.layerName;
    const taskCore = getStationTaskText(evaluation.station);

    return {
      priority,
      owner: responsibility.engineerRole,
      station: stationName,
      processLayer: layerName,
      email: responsibility.engineerEmail,
      issue: isMainIssue
        ? `${stationName} / ${layerName} 數據異常，風險分數最高`
        : `${stationName} / ${layerName} 需同步確認前後段影響`,
      task: isMainIssue
        ? `優先檢查${stationName}${layerName}：${taskCore}`
        : `同步確認${stationName}${layerName}：${taskCore}`,
      due: isMainIssue ? "下一次資料更新前" : "今天下班前",
      status: isMainIssue ? "優先處理" : "同步確認",
      acceptance: isMainIssue
        ? `${stationName}異常指標下降，${layerName}預測 NG 不再增加`
        : `${stationName}${layerName}沒有造成整線品質波動`,
      riskScore: evaluation.riskScore,
      riskReasons: evaluation.reasons
    };
  });
}

function getStationTaskText(station) {
  const tasks = [];
  const metrics = station.metrics;

  if (metrics.clog_rate_pct >= 10 || station.componentHealth.nozzle !== "normal") tasks.push("噴嘴狀態");
  if (station.componentHealth.filter_mesh !== "normal") tasks.push("濾網堵塞");
  if (getSprayWidthStatus(station) !== "normal") tasks.push("噴幅範圍");
  tasks.push("霧化空氣壓力");
  tasks.push("扇形氣壓");
  tasks.push("塗料壓力");
  tasks.push("供漆流量穩定性");
  tasks.push("噴塗節拍");

  return `${tasks.join("、")}。`;
}

function buildAcceptanceChecklist(mainEvaluation, assignments) {
  const main = mainEvaluation.responsibility;
  return [
    `${main.stationName}風險分數下降`,
    `${main.stationName}${main.layerName}預測 NG 不再增加`,
    `${main.stationName}壓力、流量、噴幅回到穩定範圍`,
    "其他站別未出現連鎖異常",
    `明天 QC 後確認 NG 類型沒有集中在${main.stationName}${main.layerName}`
  ];
}

// ==============================
// Helpers
// ==============================

function formatPercent(value, digits = 1) {
  return `${Number(value || 0).toFixed(digits)}%`;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("en-US");
}

function formatDeltaPercent(value) {
  const number = Number(value || 0);
  return `${number > 0 ? "+" : ""}${number.toFixed(1)}%`;
}

function formatDeltaNumber(value, unit = "") {
  const number = Number(value || 0);
  return `${number > 0 ? "+" : ""}${formatNumber(number)}${unit}`;
}

function formatDeltaPoints(value) {
  const number = Number(value || 0);
  return `${number > 0 ? "+" : ""}${number.toFixed(1)} pts`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatLastUpdateTime(date) {
  if (!date) return "--";
  return date.toLocaleTimeString("zh-TW", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit"
  });
}

function getOperationLevel(summary) {
  if (summary.mainStationRiskScore >= 70 || summary.efficiencyChange <= -8 || summary.extraPredictedNgPcs >= 220) {
    return "緊急";
  }

  if (
    summary.mainStationRiskScore >= 35 ||
    summary.efficiencyChange <= -3 ||
    summary.futureNoActionEfficiency < 73 ||
    summary.utilization < 80 ||
    summary.predictedOkRate < 92 ||
    summary.extraPredictedNgPcs >= 100
  ) {
    return "警告";
  }

  return "正常";
}

function statusClass(level) {
  if (level === "緊急") return "emergency";
  if (level === "警告") return "warning";
  return "normal";
}

function shouldShowCategoryAlert(level) {
  return level === "警告" || level === "緊急" || level === "危險";
}

function getCategoryAlertClass(level) {
  if (level === "緊急" || level === "危險") return "danger";
  if (level === "警告") return "warning";
  return "";
}

function assignmentStatusClass(status) {
  if (status.includes("等待")) return "waiting";
  if (status.includes("完成")) return "done";
  return "pending";
}

function changeClass(value) {
  const text = String(value || "");
  if (text.startsWith("-") || text.includes("少產") || text.includes("增加") || text.includes("下降") || text.includes("異常") || text.includes("惡化")) return "negative-text";
  if (text.startsWith("+") || text.includes("改善") || text.includes("正常")) return "good-text";
  return "";
}

function getDateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseDateKey(dateKey) {
  const [year, month, day] = String(dateKey).split("-").map(Number);
  return new Date(year, month - 1, day);
}

function formatDateLabel(dateKey) {
  const date = parseDateKey(dateKey);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}/${month}/${day}`;
}

function getTodayKey() {
  return CONFIG.SIMULATED_API_ENABLED ? getActiveApiDateKey() : getDateKey(new Date());
}

function getCurrentDataHour() {
  const db = currentDatabaseResponse || MOCK_DATABASE_RESPONSE;
  const rawTime =
    db?.responseMeta?.dataWindow?.currentEnd ||
    db?.responseMeta?.generatedAt ||
    new Date().toISOString();

  const match = String(rawTime).match(/T(\d{2}):/);
  const hour = match ? Number(match[1]) : new Date().getHours();

  return Math.max(0, Math.min(23, Number.isFinite(hour) ? hour : 0));
}

function getTimeSegment(hour) {
  const currentHour = getCurrentDataHour();
  const value = Number(hour || 0);

  if (value < currentHour) {
    return { key: "past", label: "Past / 過去" };
  }

  if (value === currentHour) {
    return { key: "current", label: "Current / 當下" };
  }

  return { key: "future", label: "Future / 預測" };
}

function getTimeSegmentLabel(hour) {
  return getTimeSegment(hour).label;
}

function getTimeSegmentSummaryText() {
  const currentHour = getCurrentDataHour();
  const currentLabel = `${String(currentHour).padStart(2, "0")}:00`;
  const pastEnd = currentHour > 0 ? `${String(currentHour - 1).padStart(2, "0")}:00` : "無";
  const futureStart = currentHour < 23 ? `${String(currentHour + 1).padStart(2, "0")}:00` : "無";

  return {
    currentHour,
    currentLabel,
    pastText: currentHour > 0 ? `Past：00:00-${pastEnd}` : "Past：無",
    currentText: `Current：${currentLabel}`,
    futureText: currentHour < 23 ? `Future：${futureStart}-24:00` : "Future：無"
  };
}

function splitSeriesByCurrentHour(series) {
  const currentHour = getCurrentDataHour();
  return {
    currentHour,
    pastRows: series.filter(row => Number(row.hour) <= currentHour),
    futureRows: series.filter(row => Number(row.hour) >= currentHour),
    currentRow: series.find(row => Number(row.hour) === currentHour) || series[Math.min(currentHour, series.length - 1)]
  };
}

function makeSvgPoints(rows, xForHour, yForValue, metricKey) {
  return rows
    .map(row => `${xForHour(row.hour).toFixed(1)},${yForValue(row[metricKey]).toFixed(1)}`)
    .join(" ");
}


function isSelectedDatePendingQC(dateKey) {
  return dateKey >= getActiveApiDateKey();
}

function generateDateOptions(daysBack = 14) {
  const activeDate = getActiveApiDateKey();
  const archivedKeys = getArchivedDateKeys();
  const keys = new Set([activeDate, ...archivedKeys]);

  if (!CONFIG.SIMULATED_API_ENABLED) {
    const today = new Date();
    for (let i = 0; i <= daysBack; i += 1) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);
      keys.add(getDateKey(date));
    }
  }

  return Array.from(keys)
    .sort()
    .reverse()
    .map(key => {
      let suffix = "";
      if (key === activeDate) suffix = " 目前模擬日";
      else if (archivedKeys.includes(key)) suffix = "";
      return { key, label: `${formatDateLabel(key)}${suffix}` };
    });
}

function getQualityGradeByOkRate(okRate) {
  const rate = Number(okRate || 0);

  if (rate >= 92) {
    return { grade: "良好", className: "quality-good", description: "品質穩定" };
  }

  if (rate >= 88) {
    return { grade: "警告", className: "quality-warning", description: "品質有下降風險" };
  }

  return { grade: "危險", className: "quality-danger", description: "品質風險偏高" };
}

function getSelectedQualityInfo(summary) {
  const pending = isSelectedDatePendingQC(selectedReportDate);

  if (pending) {
    const okRate = summary.predictedOkRate;
    const gradeInfo = getQualityGradeByOkRate(okRate);

    return {
      label: "選定日預測品質分數",
      value: formatPercent(okRate),
      sourceStatus: "待 QC / 預測品質",
      note: "當天為預測；隔天 QC 後才是實際品質",
      grade: gradeInfo.grade,
      gradeClass: gradeInfo.className,
      description: gradeInfo.description
    };
  }

  const db = summary?.rawDatabaseResponse || currentDatabaseResponse || {};
  const okRate = Number(
    db.productionKpi?.currentPeriod?.actualOkRatePct ??
    db.productionKpi?.currentPeriod?.estimatedOkRatePct ??
    summary.predictedOkRate ??
    summary.predictionValidation.yesterdayActualOkRate
  );
  const gradeInfo = getQualityGradeByOkRate(okRate);

  return {
    label: "選定日實際品質分數",
    value: formatPercent(okRate),
    sourceStatus: "已完成 QC / DB 實際品質",
    note: "隔天 QC 完成後由 DB qc_result 重新取得，不使用當天預測存檔",
    grade: gradeInfo.grade,
    gradeClass: gradeInfo.className,
    description: gradeInfo.description
  };
}


function getQualityScoreMode(dateKey = selectedReportDate) {
  const targetDate = dateKey || selectedReportDate || getActiveApiDateKey();
  const isPredicted = isSelectedDatePendingQC(targetDate);

  return {
    isPredicted,
    scoreLabel: isPredicted ? "預測品質分數" : "實際品質分數",
    shortLabel: isPredicted ? "預測品質" : "實際品質",
    hourlyAverageLabel: isPredicted ? "小時平均預測品質分數" : "小時平均實際品質分數",
    axisLabel: isPredicted ? "預測品質分數 %" : "實際品質分數 %",
    batchAverageNote: "該小時所有 batch 分數平均值",
    sourceStatus: isPredicted ? "待 QC / 預測品質" : "已完成 QC / 實際品質",
    explanation: isPredicted
      ? "當天尚未完成 QC，畫面上的品質分數是模型依照當小時所有 batch 計算出的平均預測品質分數；隔天 QC 完成後才會轉為實際品質分數。"
      : "此日期已完成 QC，畫面上的品質分數是從 DB qc_result 重新查詢的該小時所有 batch 實際 QC 平均品質分數，不是沿用當天預測結果。"
  };
}

function getCurrentQualityScoreMode() {
  const dbDate = getResponseDateKeyFromDb(currentDatabaseResponse || MANAGER_MOCK_SUMMARY?.rawDatabaseResponse || MOCK_DATABASE_RESPONSE);
  return getQualityScoreMode(dbDate);
}

function setRecommendationDrawerOpen(open) {
  isRecommendationDrawerOpen = Boolean(open);

  const panel = document.getElementById("recommendationPanel");
  const overlay = document.getElementById("drawerOverlay");
  const trigger = document.getElementById("recommendationDrawerTrigger");

  if (panel) {
    panel.classList.toggle("open", isRecommendationDrawerOpen);
    panel.setAttribute("aria-hidden", String(!isRecommendationDrawerOpen));
  }

  if (overlay) {
    overlay.classList.toggle("open", isRecommendationDrawerOpen);
  }

  if (trigger) {
    trigger.setAttribute("aria-expanded", String(isRecommendationDrawerOpen));
    trigger.classList.toggle("is-drawer-open-hidden", isRecommendationDrawerOpen);
    trigger.setAttribute("aria-hidden", String(isRecommendationDrawerOpen));
    trigger.tabIndex = isRecommendationDrawerOpen ? -1 : 0;
  }

  document.body.classList.toggle("drawer-open", isRecommendationDrawerOpen);
}

function toggleRecommendationDrawer() {
  setRecommendationDrawerOpen(!isRecommendationDrawerOpen);
}
// ==============================
// Content builders
// ==============================

