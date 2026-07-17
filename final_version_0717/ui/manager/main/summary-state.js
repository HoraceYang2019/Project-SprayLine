let lastDataUpdateAt = null;
let latestDataError = "";
let selectedReportDate = getInitialReportDateKey();
let selectedReportHourMode = "hour";
let selectedReportHour = null;
let selectedBatchId = null;
let isTrendDrawerOpen = false;
let activeTrendDrawer = null;

let currentDatabaseResponse = null;
let MANAGER_SUMMARY = null;
let CURRENT_RECOMMENDATION_ASSIGNMENTS = [];

const notificationButtonResetTimers = {};

function normalizeManagerSummary(summary, db) {
  return {
    ...summary,
    rawDatabaseResponse: db,
    batchSelector: summary?.batchSelector || {
      selectedBatchId: null,
      defaultModeLabel: "全部批號 / 該小時累計",
      availableBatches: []
    },
    stationComparison: Array.isArray(summary?.stationComparison) ? summary.stationComparison : [],
    recommendations: Array.isArray(summary?.recommendations) ? summary.recommendations : [],
    trendDrawer: summary?.trendDrawer || { stationSeries: {} }
  };
}

function getManagerSummaryFromDatabase(db) {
  if (!db || typeof db !== "object") return null;
  if (!db.managerView || typeof db.managerView !== "object") return null;
  return normalizeManagerSummary(db.managerView, db);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatPercent(value, digits = 1) {
  if (value === null || value === undefined || value === "") return "—";
  return `${Number(value).toFixed(digits)}%`;
}

function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "—";
  return Number(value).toLocaleString("en-US");
}

function formatPcs(value) {
  if (value === null || value === undefined || value === "") return "—";
  return `${formatNumber(value)} pcs`;
}

function formatMetricValue(metricKey, value) {
  if (value === null || value === undefined || value === "") return "—";
  if (metricKey === "utilizationPct") return formatPercent(value);
  return formatPcs(value);
}

function levelClass(level) {
  const text = String(level || "").toLowerCase();
  if (text === "alarm" || text === "critical") return "level-alarm";
  if (text === "warning") return "level-warning";
  return "level-normal";
}

function statusClass(level) {
  return levelClass(level);
}

function formatLevelLabel(level) {
  const text = String(level || "").toLowerCase();
  if (text === "alarm" || text === "critical") return "警報";
  if (text === "warning") return "警示";
  return "正常";
}

function getSelectedBatchLabel() {
  if (selectedBatchId) return selectedBatchId;
  return MANAGER_SUMMARY?.batchSelector?.defaultModeLabel || "全部批號 / 該小時累計";
}

function getManagerKpis() {
  return MANAGER_SUMMARY?.kpis || {};
}

function getStationComparisonRows() {
  return Array.isArray(MANAGER_SUMMARY?.stationComparison) ? MANAGER_SUMMARY.stationComparison : [];
}

function getRecommendationItems() {
  return Array.isArray(MANAGER_SUMMARY?.recommendations) ? MANAGER_SUMMARY.recommendations : [];
}

function getBatchOptions() {
  return Array.isArray(MANAGER_SUMMARY?.batchSelector?.availableBatches)
    ? MANAGER_SUMMARY.batchSelector.availableBatches
    : [];
}

function getComparisonRowByStationId(stationId) {
  return getStationComparisonRows().find(row => row.stationId === stationId) || null;
}

function getTrendDrawerMetricData(stationId, metricKey) {
  return MANAGER_SUMMARY?.trendDrawer?.stationSeries?.[stationId]?.metrics?.[metricKey] || null;
}

function getTrendDrawerStationTitle(stationId) {
  const stationSeries = MANAGER_SUMMARY?.trendDrawer?.stationSeries?.[stationId];
  if (!stationSeries) return "-";
  return `${stationSeries.stationName} / ${stationSeries.processName}`;
}

function clearNotificationResetTimer(key) {
  if (!notificationButtonResetTimers[key]) return;
  window.clearTimeout(notificationButtonResetTimers[key]);
  delete notificationButtonResetTimers[key];
}
