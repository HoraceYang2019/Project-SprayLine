// ==============================
// Config
// ==============================

const CONFIG = {
  USE_MOCK_DATA: true,
  // ===== 資料輸入端點：測試後在此連接真實資料 =====
  // 歷史實際品質控制 API：應傳回昨天/過去一整天的實際品質控制記錄。
  HISTORICAL_ACTUAL_API_URL: "",
  // 目前流程資料庫 API：應傳回今天從 00:00 到現在的 20 分鐘流程記錄。
  DB_API_URL: "",
  // 未來預測 API/模型端點：可選。留空表示使用來自最新預測的本地模擬預測。
  FORECAST_API_URL: "",
  // Google Apps Script Web 應用程式 URL：收到管理員 Gmail 通知的高警告負載。
  WARNING_APP_SCRIPT_URL: "https://script.google.com/macros/s/AKfycbyvPzX3epFpOH9AUFLLlD_-W4EXCOULHInUZKfmnCyJHlrCOY_HYTNSCBLtm3ZVzoWnBQ/exec",
  DB_POLL_INTERVAL_MS: 20 * 60 * 1000,
  // 演示模式：目前沒有資料庫可用，因此模擬資料會自動快速推進
  // 就好像有新的 20 分鐘資料庫記錄到達一樣。
  MOCK_POLL_INTERVAL_MS: 5000
};

const TARGETS = {
  utilization: 85,
  cycleTime: 40,
  predictedOkRate: 90,
  predictedNgPcs: 35
};

const TIME_RANGE_LABELS = {
  past: "Past Actual QC",
  current: "Current Predicted Quality Risk",
  future: "Future Forecast NG Risk",
  all: "All View"
};

const HOURS = Array.from({ length: 24 }, (_, index) => `${String(index).padStart(2, "0")}:00`);
const STATIONS = [
  { key: "station1", label: "Station 1", robot: "Robot 1", processStep: "Base Coat", baselineCycleTime: 39, mainIssue: "Minor nozzle cleaning delay causes short micro-stops." },
  { key: "station2", label: "Station 2", robot: "Robot 2", processStep: "Top Coat", baselineCycleTime: 40, mainIssue: "Spray pressure instability and robot path deviation." },
  { key: "station3", label: "Station 3", robot: "Robot 3", processStep: "Edge Touch-up", baselineCycleTime: 39.5, mainIssue: "Paint supply fluctuation during edge coverage correction." }
];

// ==============================
// State
// ==============================

let currentTimeRangeMode = "current";
let selectedHour = null;
let mockRealtimeCursor = 44; // 00:00 through 14:40 for initial demo data.
let realtimePollingTimer = null;

let historicalActualRecords = [];
let todayRealtimeRecords = [];
let hourlyPredictedRecords = [];
let predictionHistory = [];
let futureForecastRecords = [];
let notificationHistory = [];

const notifiedWarnings = new Set();
const notificationHistoryKeys = new Set();

let okNgTrendChart = null;
let utilizationTrendChart = null;
let cycleTimeTrendChart = null;

// ==============================
// Helpers
// ==============================

function average(values) {
  if (!values.length) return 0;
  return values.reduce((total, value) => total + value, 0) / values.length;
}

function sum(values) {
  return values.reduce((total, value) => total + value, 0);
}

function formatPercent(value, digits = 1) {
  return `${Number(value || 0).toFixed(digits)}%`;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function riskOrder(level) {
  if (level === "High") return 3;
  if (level === "Medium") return 2;
  return 1;
}

function highestRisk(levels) {
  return levels.slice().sort((a, b) => riskOrder(b) - riskOrder(a))[0] || "Low";
}

function getRiskClass(level) {
  return `risk-${String(level || "Low").toLowerCase()}`;
}

function getTextRiskClass(level) {
  return `text-${String(level || "Low").toLowerCase()}`;
}

function canRenderCharts() {
  return typeof Chart !== "undefined";
}

function showChartFallback(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const container = canvas.closest(".chart-container");
  if (!container) return;
  canvas.style.display = "none";
  if (container.querySelector(".chart-fallback")) return;
  const fallback = document.createElement("div");
  fallback.className = "chart-fallback";
  fallback.textContent = "Chart.js is not loaded. KPI cards, Time Bar, station data, tables, and warnings still show mock data.";
  container.appendChild(fallback);
}

function getBadgeClass(status) {
  if (status === "Actual QC") return "actual-badge badge-actual";
  if (status === "Forecast") return "forecast-badge badge-forecast";
  if (status === "Predicted") return "predicted-badge badge-predicted";
  return "pending-badge badge-pending";
}

function hourFromSlot(slotIndex) {
  return `${String(Math.floor(slotIndex / 3)).padStart(2, "0")}:00`;
}

function timestampFromSlot(slotIndex) {
  const hour = Math.floor(slotIndex / 3);
  const minute = (slotIndex % 3) * 20;
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function setNotificationStatus(text, cssClass = "notify-idle") {
  const element = document.getElementById("notifyStatusText");
  if (!element) return;
  element.textContent = text;
  element.className = `notify-status ${cssClass}`;
}

function showToast(message, level = "high") {
  const stack = document.getElementById("toastStack");
  if (!stack) return;

  const toast = document.createElement("div");
  toast.className = `toast notification-toast ${String(level).toLowerCase()}`;
  toast.textContent = message;
  stack.appendChild(toast);

  setTimeout(() => toast.remove(), 4500);
}

function addNotificationHistory(entry) {
  const key = `${entry.warningId}|${entry.status}`;
  if (notificationHistoryKeys.has(key)) return;
  notificationHistoryKeys.add(key);
  notificationHistory.unshift(entry);
}

// ==============================
// Data Ingress Interfaces
// ==============================
// Keep all external data entry points here. When real data is ready:
// 1. Fill CONFIG.*_API_URL.
// 2. Set CONFIG.USE_MOCK_DATA = false.
// 3. Adjust only the normalize*() functions below to match backend field names.
// Rendering, risk calculation, Time Bar, charts, and warning logic should not need edits.

async function fetchHistoricalActualData() {
  // Interface: Past / Actual QC data input.
  // Expected normalized output fields:
  // timestamp, hourKey, actualOkRate, actualNgRate, actualNgPcs, producedPcs,
  // station1Utilization, station2Utilization, station3Utilization,
  // station1CycleTime, station2CycleTime, station3CycleTime,
  // riskLevel, mainCause, relatedStation, status: "Actual QC"
  if (CONFIG.USE_MOCK_DATA || !CONFIG.HISTORICAL_ACTUAL_API_URL) {
    return generateMockHistoricalActualRecords();
  }

  const response = await fetch(CONFIG.HISTORICAL_ACTUAL_API_URL);
  const data = await response.json();
  return normalizeHistoricalActualData(data);
}

async function fetchRealtimeDataFromDB() {
  // Interface: Current / Predicted process DB input.
  // Expected raw data interval: one record every 20 minutes.
  // Expected normalized output fields:
  // timestamp, hourKey, station1Utilization, station2Utilization, station3Utilization,
  // station1CycleTime, station2CycleTime, station3CycleTime,
  // station1AlarmCount, station2AlarmCount, station3AlarmCount,
  // producedPcs, batchId, isPendingQC
  if (CONFIG.USE_MOCK_DATA || !CONFIG.DB_API_URL) {
    return generateMockRealtimeDataUntilNow();
  }

  const response = await fetch(CONFIG.DB_API_URL);
  const data = await response.json();
  return normalizeDbData(data);
}

async function fetchFutureForecastData(latestPrediction) {
  // Interface: Future forecast input.
  // Leave CONFIG.FORECAST_API_URL empty to use the local mock forecast.
  // When backend/model is ready, return records using the same fields as generateFutureForecastFromCurrentPrediction().
  if (CONFIG.USE_MOCK_DATA || !CONFIG.FORECAST_API_URL) {
    return generateMockFutureForecastFromCurrentPrediction(latestPrediction);
  }

  const response = await fetch(CONFIG.FORECAST_API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ latestPrediction })
  });
  const data = await response.json();
  return normalizeFutureForecastData(data);
}
async function sendDirectTestGmailByAppsScript() {
  const now = new Date();
  const timestamp = now.toLocaleString("zh-TW", {
    timeZone: "Asia/Taipei"
  });

  const payload = {
    warningId: "DASHBOARD-DIRECT-TEST-" + Date.now(),
    timestamp: timestamp,
    time: timestamp,
    hourKey: "TEST",
    riskLevel: "High",
    line: "Spray Line 1",
    station: "Station 2",
    robot: "Robot 2",
    processStep: "Top Coat",
    batchId: "DASHBOARD-TEST",
    message: "Direct test notification from dashboard.js. If you receive this email, frontend POST to Apps Script is working.",
    mainCause: "Frontend direct Gmail test.",
    suggestedAction: "No action required. This is a dashboard POST test.",
    predictedNgPcs: 42,
    predictedOkRate: 86.5,
    metrics: {
      predictedOkRate: "86.5%",
      ngPcs: "42",
      utilization: "68.0%",
      cycleTime: "46.5 sec"
    },
    recipientRole: "manager",
    debugSource: "dashboard-direct-test"
  };

  setNotificationStatus("Sending direct Gmail test...", "notify-idle");
  console.log("[MAIL DEBUG] Direct test payload:", payload);

  try {
    const result = await postWarningNotificationPayload(payload);

    addNotificationHistory({
      ...payload,
      status: "Direct Test Sent"
    });

    setNotificationStatus(
      "Direct Gmail test sent. Check Gmail and Apps Script Executions.",
      "notify-success"
    );

    showToast("Direct Gmail test sent", "high");
    renderNotificationHistory();

    console.log("[MAIL DEBUG] Direct test result:", result);
    return result;

  } catch (error) {
    console.error("[MAIL DEBUG] Direct Gmail test failed:", error);

    addNotificationHistory({
      ...payload,
      status: "Direct Test Failed"
    });

    setNotificationStatus(
      "Direct Gmail test failed. Check browser console.",
      "notify-error"
    );

    renderNotificationHistory();
    return null;
  }
}
async function postWarningNotificationPayload(payload) {
  if (!CONFIG.WARNING_APP_SCRIPT_URL) {
    console.log("[MAIL DEBUG] Mock Apps Script warning payload", payload);
    return { ok: true, mock: true };
  }

  return new Promise((resolve, reject) => {
    try {
      const url = CONFIG.WARNING_APP_SCRIPT_URL + "?source=dashboard_form&ts=" + Date.now();

      console.log("[MAIL DEBUG] Posting by hidden form to Apps Script:", url);
      console.log("[MAIL DEBUG] Payload:", payload);

      const iframeName = "appsScriptMailFrame_" + Date.now();

      const iframe = document.createElement("iframe");
      iframe.name = iframeName;
      iframe.style.display = "none";

      const form = document.createElement("form");
      form.method = "POST";
      form.action = url;
      form.target = iframeName;
      form.style.display = "none";

      const input = document.createElement("input");
      input.type = "hidden";
      input.name = "payload";
      input.value = JSON.stringify(payload);

      form.appendChild(input);
      document.body.appendChild(iframe);
      document.body.appendChild(form);

      let resolved = false;

      iframe.onload = function () {
        if (resolved) return;
        resolved = true;

        console.log("[MAIL DEBUG] Hidden form POST completed. Check Apps Script Executions and Gmail.");

        setTimeout(() => {
          form.remove();
          iframe.remove();
        }, 1000);

        resolve({
          ok: true,
          method: "hidden-form-post",
          note: "Form POST submitted. Browser cannot read Apps Script response reliably."
        });
      };

      form.submit();

      // 保險：有些瀏覽器/Google redirect 不一定穩定觸發 iframe.onload，
      // 但 form.submit() 已經送出，所以 5 秒後先視為 submitted。
      setTimeout(() => {
        if (resolved) return;
        resolved = true;

        console.log("[MAIL DEBUG] Hidden form POST submitted by timeout. Check Apps Script Executions and Gmail.");

        form.remove();
        iframe.remove();

        resolve({
          ok: true,
          method: "hidden-form-post-timeout",
          note: "Form submitted; iframe load event did not confirm response."
        });
      }, 5000);

    } catch (error) {
      console.error("[MAIL DEBUG] Hidden form POST failed before submit:", error);
      reject(error);
    }
  });
}

function normalizeHistoricalActualData(data) {
  const rows = Array.isArray(data) ? data : data.records || [];

  return rows.map(row => ({
    timestamp: row.timestamp,
    hourKey: row.hourKey || `${String(row.timestamp).slice(0, 2)}:00`,
    actualOkRate: Number(row.actualOkRate),
    actualNgRate: Number(row.actualNgRate),
    actualNgPcs: Number(row.actualNgPcs),
    producedPcs: Number(row.producedPcs),
    station1Utilization: Number(row.station1Utilization),
    station2Utilization: Number(row.station2Utilization),
    station3Utilization: Number(row.station3Utilization),
    station1CycleTime: Number(row.station1CycleTime),
    station2CycleTime: Number(row.station2CycleTime),
    station3CycleTime: Number(row.station3CycleTime),
    riskLevel: row.riskLevel || "Low",
    mainCause: row.mainCause || "Actual QC data from backend.",
    relatedStation: row.relatedStation || "Line summary",
    status: "Actual QC"
  }));
}

function normalizeDbData(data) {
  const rows = Array.isArray(data) ? data : data.records || [];

  return rows.map(row => ({
    timestamp: row.timestamp,
    hourKey: row.hourKey || `${String(row.timestamp).slice(0, 2)}:00`,
    station1Utilization: Number(row.station1Utilization),
    station2Utilization: Number(row.station2Utilization),
    station3Utilization: Number(row.station3Utilization),
    station1CycleTime: Number(row.station1CycleTime),
    station2CycleTime: Number(row.station2CycleTime),
    station3CycleTime: Number(row.station3CycleTime),
    station1AlarmCount: Number(row.station1AlarmCount || 0),
    station2AlarmCount: Number(row.station2AlarmCount || 0),
    station3AlarmCount: Number(row.station3AlarmCount || 0),
    producedPcs: Number(row.producedPcs),
    batchId: row.batchId,
    isPendingQC: row.isPendingQC !== false
  }));
}

function normalizeFutureForecastData(data) {
  const rows = Array.isArray(data) ? data : data.records || [];

  return rows.map(row => ({
    timestamp: row.timestamp || row.hourKey,
    hourKey: row.hourKey || `${String(row.timestamp).slice(0, 2)}:00`,
    batchId: row.batchId || `F-${row.hourKey}`,
    predictedOkRate: Number(row.predictedOkRate),
    predictedNgRate: Number(row.predictedNgRate),
    predictedNgPcs: Number(row.predictedNgPcs),
    producedPcs: Number(row.producedPcs),
    riskLevel: row.riskLevel || "Low",
    relatedStation: row.relatedStation || "Line summary",
    mainCause: row.mainCause || "Forecast model output.",
    station1Utilization: Number(row.station1Utilization),
    station2Utilization: Number(row.station2Utilization),
    station3Utilization: Number(row.station3Utilization),
    station1CycleTime: Number(row.station1CycleTime),
    station2CycleTime: Number(row.station2CycleTime),
    station3CycleTime: Number(row.station3CycleTime)
  }));
}

// ==============================
// Mock Historical and Realtime Data
// ==============================

function generateMockHistoricalActualRecords() {
  return HOURS.map((hourKey, index) => {
    const station2Issue = index >= 10 && index <= 15;
    const producedPcs = 205 + (index % 5) * 8;
    const actualNgRate = station2Issue ? 8.2 + (index - 10) * 0.25 : 4.5 + (index % 4) * 0.35;
    const actualOkRate = 100 - actualNgRate;

    return {
      timestamp: hourKey,
      hourKey,
      actualOkRate: Number(actualOkRate.toFixed(1)),
      actualNgRate: Number(actualNgRate.toFixed(1)),
      actualNgPcs: Math.round(producedPcs * actualNgRate / 100),
      producedPcs,
      station1Utilization: 86 - (index % 3),
      station2Utilization: station2Issue ? 76 - (index - 10) : 84 - (index % 4),
      station3Utilization: 83 - (index % 3),
      station1CycleTime: Number((38.6 + (index % 3) * 0.4).toFixed(1)),
      station2CycleTime: Number((station2Issue ? 42.5 + (index - 10) * 0.6 : 40.2 + (index % 3) * 0.4).toFixed(1)),
      station3CycleTime: Number((39.8 + (index % 4) * 0.5).toFixed(1)),
      riskLevel: station2Issue && index >= 13 ? "Medium" : "Low",
      mainCause: station2Issue ? "Actual QC confirmed Station 2 coating instability." : "Actual QC confirmed stable spray quality.",
      relatedStation: station2Issue ? "Station 2" : "Station 1",
      status: "Actual QC"
    };
  });
}

function generateMockRealtimeDataUntilNow() {
  const records = [];
  const maxSlot = Math.min(mockRealtimeCursor, 23 * 3 + 2);

  for (let slot = 0; slot <= maxSlot; slot += 1) {
    const timestamp = timestampFromSlot(slot);
    const hourKey = hourFromSlot(slot);
    const hour = Math.floor(slot / 3);
    const batchIndex = Math.floor(hour / 3) + 1;
    const station2Issue = hour >= 9;
    const severeStation2Issue = hour >= 10;
    const station3Issue = hour >= 12;

    records.push({
      timestamp,
      hourKey,
      station1Utilization: Math.max(76, 88 - Math.floor(hour / 5) - (slot % 3)),
      station2Utilization: station2Issue ? Math.max(58, 78 - (hour - 9) * 3 - (slot % 3) * 2) : 85 - (slot % 3),
      station3Utilization: station3Issue ? Math.max(70, 80 - (hour - 12) * 2 - (slot % 3)) : 84 - (slot % 3),
      station1CycleTime: Number((38.8 + (slot % 3) * 0.2 + hour * 0.03).toFixed(1)),
      station2CycleTime: Number((station2Issue ? 42.0 + (hour - 9) * 1.15 + (slot % 3) * 0.6 : 40.2 + (slot % 3) * 0.4).toFixed(1)),
      station3CycleTime: Number((station3Issue ? 42.0 + (hour - 12) * 0.55 + (slot % 3) * 0.4 : 39.8 + (slot % 3) * 0.35).toFixed(1)),
      station1AlarmCount: hour >= 13 && slot % 3 === 2 ? 1 : 0,
      station2AlarmCount: severeStation2Issue ? 2 + (slot % 3 === 2 ? 1 : 0) : station2Issue ? 1 : 0,
      station3AlarmCount: station3Issue ? 1 : 0,
      producedPcs: Math.max(58, 76 - (station2Issue ? hour - 9 : 0) - (slot % 3)),
      batchId: `B20260524-${String(batchIndex).padStart(3, "0")}`,
      isPendingQC: true
    });
  }

  return records;
}

// ==============================
// Prediction and Aggregation
// ==============================

function calculateRiskLevel(record) {
  const stationRisks = STATIONS.map((station, index) => {
    const stationNumber = index + 1;
    const utilization = record[`station${stationNumber}Utilization`];
    const cycleTime = record[`station${stationNumber}CycleTime`];
    const alarmCount = record[`station${stationNumber}AlarmCount`];
    const cycleTimeIncreasePct = ((cycleTime - station.baselineCycleTime) / station.baselineCycleTime) * 100;

    if (utilization < 70 || cycleTimeIncreasePct > 15 || alarmCount >= 3) return "High";
    if ((utilization >= 70 && utilization <= 80) || cycleTimeIncreasePct >= 8 || alarmCount >= 1) return "Medium";
    return "Low";
  });

  if (record.predictedOkRate !== undefined && record.predictedOkRate < TARGETS.predictedOkRate) stationRisks.push("Medium");
  if (record.predictedNgPcs !== undefined && record.predictedNgPcs >= TARGETS.predictedNgPcs) stationRisks.push("High");

  return highestRisk(stationRisks);
}

function getDominantCause(record) {
  const stationScores = STATIONS.map((station, index) => {
    const stationNumber = index + 1;
    const utilization = record[`station${stationNumber}Utilization`];
    const cycleTime = record[`station${stationNumber}CycleTime`];
    const alarmCount = record[`station${stationNumber}AlarmCount`];
    const cycleTimeIncreasePct = ((cycleTime - station.baselineCycleTime) / station.baselineCycleTime) * 100;

    return {
      station: station.label,
      robot: station.robot,
      issue: station.mainIssue,
      score: Math.max(0, TARGETS.utilization - utilization) * 1.2 + Math.max(0, cycleTimeIncreasePct) * 1.5 + alarmCount * 4,
      utilization,
      cycleTime,
      cycleTimeIncreasePct
    };
  });

  return stationScores.sort((a, b) => b.score - a.score)[0];
}

function updatePredictedDataFromRealtime(records) {
  return records.map(record => {
    const dominant = getDominantCause(record);
    const alarmTotal = record.station1AlarmCount + record.station2AlarmCount + record.station3AlarmCount;
    const station2CycleIncreasePct = ((record.station2CycleTime - STATIONS[1].baselineCycleTime) / STATIONS[1].baselineCycleTime) * 100;
    const station3CycleIncreasePct = ((record.station3CycleTime - STATIONS[2].baselineCycleTime) / STATIONS[2].baselineCycleTime) * 100;
    const utilizationPenalty =
      Math.max(0, TARGETS.utilization - record.station1Utilization) * 0.08 +
      Math.max(0, TARGETS.utilization - record.station2Utilization) * 0.28 +
      Math.max(0, TARGETS.utilization - record.station3Utilization) * 0.16;
    const cyclePenalty = Math.max(0, station2CycleIncreasePct) * 0.2 + Math.max(0, station3CycleIncreasePct) * 0.12;

    const predictedOkRate = Math.max(75, Number((94.5 - utilizationPenalty - cyclePenalty - alarmTotal * 0.75).toFixed(1)));
    const predictedNgRate = Number((100 - predictedOkRate).toFixed(1));
    const predictedNgPcs = Math.max(1, Math.round(record.producedPcs * predictedNgRate / 100));
    const enriched = {
      ...record,
      predictedOkRate,
      predictedNgRate,
      predictedNgPcs,
      relatedStation: dominant.station,
      mainCause: dominant.issue,
      alarmCount: alarmTotal,
      isPendingQC: true
    };

    return {
      ...enriched,
      riskLevel: calculateRiskLevel(enriched)
    };
  });
}

function appendPredictionHistory(predictions) {
  const existingKeys = new Set(predictionHistory.map(item => `${item.timestamp}|${item.batchId}`));
  predictions.forEach(prediction => {
    const key = `${prediction.timestamp}|${prediction.batchId}`;
    if (existingKeys.has(key)) return;
    predictionHistory.push({
      timestamp: prediction.timestamp,
      hourKey: prediction.hourKey,
      batchId: prediction.batchId,
      predictedOkRate: prediction.predictedOkRate,
      predictedNgPcs: prediction.predictedNgPcs,
      riskLevel: prediction.riskLevel,
      relatedStation: prediction.relatedStation
    });
  });
}

function aggregateDataByHour(records) {
  const grouped = new Map();
  records.forEach(record => {
    if (!grouped.has(record.hourKey)) grouped.set(record.hourKey, []);
    grouped.get(record.hourKey).push(record);
  });

  return Array.from(grouped.entries()).map(([hourKey, hourRecords]) => {
    const highest = highestRisk(hourRecords.map(record => record.riskLevel));
    const relatedBatches = [...new Set(hourRecords.map(record => record.batchId))];
    const mainRecord = hourRecords.slice().sort((a, b) => riskOrder(b.riskLevel) - riskOrder(a.riskLevel) || b.predictedNgPcs - a.predictedNgPcs)[0];

    return {
      hourKey,
      records: hourRecords,
      recordCount: hourRecords.length,
      averagePredictedOkRate: Number(average(hourRecords.map(record => record.predictedOkRate)).toFixed(1)),
      averagePredictedNgRate: Number(average(hourRecords.map(record => record.predictedNgRate)).toFixed(1)),
      totalPredictedNgPcs: sum(hourRecords.map(record => record.predictedNgPcs)),
      totalProducedPcs: sum(hourRecords.map(record => record.producedPcs)),
      averageStation1Utilization: Number(average(hourRecords.map(record => record.station1Utilization)).toFixed(1)),
      averageStation2Utilization: Number(average(hourRecords.map(record => record.station2Utilization)).toFixed(1)),
      averageStation3Utilization: Number(average(hourRecords.map(record => record.station3Utilization)).toFixed(1)),
      averageStation1CycleTime: Number(average(hourRecords.map(record => record.station1CycleTime)).toFixed(1)),
      averageStation2CycleTime: Number(average(hourRecords.map(record => record.station2CycleTime)).toFixed(1)),
      averageStation3CycleTime: Number(average(hourRecords.map(record => record.station3CycleTime)).toFixed(1)),
      totalAlarmCount: sum(hourRecords.map(record => record.alarmCount)),
      highestRiskLevel: highest,
      mainCause: mainRecord.mainCause,
      relatedStation: mainRecord.relatedStation,
      affectedBatchCount: relatedBatches.length,
      relatedBatchIds: relatedBatches,
      hasWarning: riskOrder(highest) >= 2 || hourRecords.filter(record => record.riskLevel === "High").length >= 2
    };
  });
}

async function generateFutureForecastFromCurrentPrediction() {
  const latest = todayRealtimeRecords[todayRealtimeRecords.length - 1];
  if (!latest) return [];
  return fetchFutureForecastData(latest);
}

function generateMockFutureForecastFromCurrentPrediction(latest) {
  const latestHour = Number(latest.hourKey.slice(0, 2));
  const startHour = Math.min(23, latestHour + 1);
  const endHour = Math.min(23, latestHour + 6);
  const forecasts = [];

  for (let hour = startHour; hour <= endHour; hour += 1) {
    const riskCarry = latest.riskLevel === "High" ? 1.7 : latest.riskLevel === "Medium" ? 0.9 : 0.2;
    const drift = (hour - startHour + 1) * riskCarry;
    const predictedOkRate = Math.max(72, Number((latest.predictedOkRate - drift).toFixed(1)));
    const predictedNgRate = Number((100 - predictedOkRate).toFixed(1));
    const predictedNgPcs = Math.max(1, Math.round(latest.producedPcs * predictedNgRate / 100));
    const riskLevel = predictedOkRate < 84 || latest.riskLevel === "High" ? "High" : predictedOkRate < 90 ? "Medium" : "Low";

    forecasts.push({
      timestamp: `${String(hour).padStart(2, "0")}:00`,
      hourKey: `${String(hour).padStart(2, "0")}:00`,
      predictedOkRate,
      predictedNgRate,
      predictedNgPcs,
      producedPcs: latest.producedPcs,
      riskLevel,
      mainCause: latest.mainCause,
      relatedStation: latest.relatedStation,
      batchId: `F20260524-${String(hour).padStart(2, "0")}`,
      isForecast: true,
      station1Utilization: Math.max(60, latest.station1Utilization - (hour - latestHour) * 0.5),
      station2Utilization: Math.max(50, latest.station2Utilization - (hour - latestHour) * 1.2),
      station3Utilization: Math.max(58, latest.station3Utilization - (hour - latestHour) * 0.7),
      station1CycleTime: Number((latest.station1CycleTime + (hour - latestHour) * 0.2).toFixed(1)),
      station2CycleTime: Number((latest.station2CycleTime + (hour - latestHour) * 0.7).toFixed(1)),
      station3CycleTime: Number((latest.station3CycleTime + (hour - latestHour) * 0.3).toFixed(1))
    });
  }

  return forecasts;
}

async function refreshRealtimeData() {
  const rawRecords = await fetchRealtimeDataFromDB();
  todayRealtimeRecords = updatePredictedDataFromRealtime(rawRecords);
  appendPredictionHistory(todayRealtimeRecords);
  hourlyPredictedRecords = aggregateDataByHour(todayRealtimeRecords);
  futureForecastRecords = await generateFutureForecastFromCurrentPrediction();
  updateDataSourceStatus();
}

function startRealtimePolling() {
  if (realtimePollingTimer) clearInterval(realtimePollingTimer);
  const intervalMs = CONFIG.USE_MOCK_DATA || !CONFIG.DB_API_URL
    ? CONFIG.MOCK_POLL_INTERVAL_MS
    : CONFIG.DB_POLL_INTERVAL_MS;

  realtimePollingTimer = setInterval(async () => {
    if (CONFIG.USE_MOCK_DATA || !CONFIG.DB_API_URL) {
      const maxCursor = 23 * 3 + 2;
      if (mockRealtimeCursor >= maxCursor) {
        updateDataSourceStatus();
        return;
      }
      mockRealtimeCursor += 1;
    }

    await refreshRealtimeData();
    renderTimeBar();
    updateDashboardBySelectedHour(selectedHour);
  }, intervalMs);
}

async function simulateNext20MinUpdate() {
  mockRealtimeCursor = Math.min(mockRealtimeCursor + 1, 23 * 3 + 2);
  await refreshRealtimeData();
  renderTimeBar();
  updateDashboardBySelectedHour(selectedHour);
}

function updateDataSourceStatus() {
  const latestTimestamp = todayRealtimeRecords[todayRealtimeRecords.length - 1]?.timestamp || "--";
  const isMockMode = CONFIG.USE_MOCK_DATA || !CONFIG.DB_API_URL;

  document.getElementById("dataSourceMode").textContent = isMockMode
    ? `Mock Auto Data Mode - new 20-min record every ${CONFIG.MOCK_POLL_INTERVAL_MS / 1000}s`
    : "Connected to DB";
  document.getElementById("lastDbUpdate").textContent = `Last DB Update: ${latestTimestamp}`;
  document.getElementById("simulateNextUpdateBtn").style.display = CONFIG.USE_MOCK_DATA ? "inline-flex" : "none";
}

// ==============================
// Filtering
// ==============================

function renderTimeRangeButtons() {
  const modes = [
    { id: "past", label: "Past" },
    { id: "current", label: "Current / Predict" },
    { id: "future", label: "Future" },
    { id: "all", label: "All" }
  ];

  document.getElementById("timeRangeButtons").innerHTML = modes.map(mode => `
    <button type="button" class="time-range-btn ${currentTimeRangeMode === mode.id ? "active" : ""}" data-mode="${mode.id}">
      ${escapeHtml(mode.label)}
    </button>
  `).join("");

  document.getElementById("timeRangeDescription").textContent =
    currentTimeRangeMode === "past"
      ? "Past shows 00:00 to next day 00:00 exclusive Actual QC for the full day."
      : currentTimeRangeMode === "current"
        ? "Current / Predict shows today's predicted quality from 20-minute DB-style records and Pending QC batches."
        : currentTimeRangeMode === "future"
          ? "Future uses the latest Current Predicted result to forecast the next few hours."
          : "All connects Past Actual, Current Predicted, and Future Forecast without mixing labels.";
}

function setTimeRangeMode(mode) {
  currentTimeRangeMode = mode;
  selectedHour = null;
  renderTimeRangeButtons();
  renderTimeBar();
  updateDashboardBySelectedHour(selectedHour);
}

function getHourStatus(hourKey) {
  let source = [];
  let type = "none";

  if (currentTimeRangeMode === "past") {
    source = historicalActualRecords.filter(record => record.hourKey === hourKey);
    type = "actual";
  } else if (currentTimeRangeMode === "current") {
    source = hourlyPredictedRecords.filter(record => record.hourKey === hourKey);
    type = "predicted";
  } else if (currentTimeRangeMode === "future") {
    source = futureForecastRecords.filter(record => record.hourKey === hourKey);
    type = "forecast";
  } else {
    source = [
      ...historicalActualRecords.filter(record => record.hourKey === hourKey),
      ...hourlyPredictedRecords.filter(record => record.hourKey === hourKey),
      ...futureForecastRecords.filter(record => record.hourKey === hourKey)
    ];
    type = source.length ? "mixed" : "none";
  }

  if (!source.length) {
    return { hourKey, type, disabled: true, riskLevel: "Low", hasWarning: false, label: "No Data" };
  }

  const riskLevel = highestRisk(source.map(record => record.riskLevel || record.highestRiskLevel));
  const hasWarning = source.some(record => record.hasWarning || riskOrder(record.riskLevel || record.highestRiskLevel) >= 2);
  return { hourKey, type, disabled: false, riskLevel, hasWarning, label: type === "actual" ? "Actual" : type === "forecast" ? "Forecast" : "Predicted" };
}

function renderTimeBar() {
  const statuses = HOURS.map(getHourStatus);
  document.getElementById("timeBarTitle").textContent = "24-Hour Time Bar";
  document.getElementById("selectedHourSummary").textContent = selectedHour
    ? `Showing ${selectedHour} to ${selectedHour.slice(0, 2)}:59 in ${TIME_RANGE_LABELS[currentTimeRangeMode]}.`
    : `Showing all available hours in ${TIME_RANGE_LABELS[currentTimeRangeMode]}.`;

  document.getElementById("timeBar").innerHTML = statuses.map(status => `
    <button
      type="button"
      class="time-hour-btn time-hour-button ${selectedHour === status.hourKey ? "active" : ""} ${status.disabled ? "disabled" : ""} ${String(status.riskLevel).toLowerCase()} ${status.hasWarning ? "has-warning" : ""}"
      data-hour="${escapeHtml(status.hourKey)}"
      ${status.disabled ? "disabled" : ""}
    >
      <div class="time-hour-label">${escapeHtml(status.hourKey)}</div>
      <div class="time-hour-meta">
        <span>${escapeHtml(status.label)}</span>
        <span class="time-hour-dot ${String(status.riskLevel).toLowerCase()}"></span>
      </div>
    </button>
  `).join("");
}

function setSelectedHour(hour) {
  selectedHour = selectedHour === hour ? null : hour;
  renderTimeBar();
  updateDashboardBySelectedHour(selectedHour);
}

function filterDataBySelectedHour(hour) {
  const filterByHour = records => hour ? records.filter(record => record.hourKey === hour) : records;
  const actual = filterByHour(historicalActualRecords);
  const predicted = filterByHour(hourlyPredictedRecords);
  const forecast = filterByHour(futureForecastRecords);

  if (currentTimeRangeMode === "past") {
    return { mode: "past", actual, predicted: [], forecast: [], batchMode: "actual", batchRows: buildActualBatchRows(actual) };
  }

  if (currentTimeRangeMode === "current") {
    return { mode: "current", actual: [], predicted, forecast: [], batchMode: "predicted", batchRows: buildPendingBatchRows(predicted) };
  }

  if (currentTimeRangeMode === "future") {
    return { mode: "future", actual: [], predicted: [], forecast, batchMode: "forecast", batchRows: buildForecastBatchRows(forecast) };
  }

  return {
    mode: "all",
    actual,
    predicted,
    forecast,
    batchMode: predicted.length ? "predicted" : forecast.length ? "forecast" : "actual",
    batchRows: predicted.length ? buildPendingBatchRows(predicted) : forecast.length ? buildForecastBatchRows(forecast) : buildActualBatchRows(actual)
  };
}

function buildActualBatchRows(records) {
  return records.map((record, index) => ({
    batchId: `A20260523-${record.hourKey.replace(":", "")}-${index + 1}`,
    startTime: record.hourKey,
    pcs: record.producedPcs,
    status: "Actual QC",
    okRate: record.actualOkRate,
    ngPcs: record.actualNgPcs,
    riskLevel: record.riskLevel,
    mainCause: record.mainCause,
    relatedStation: record.relatedStation
  }));
}

function buildPendingBatchRows(records) {
  const grouped = new Map();
  records.forEach(record => {
    record.relatedBatchIds.forEach(batchId => {
      if (!grouped.has(batchId)) grouped.set(batchId, []);
      grouped.get(batchId).push(record);
    });
  });

  return Array.from(grouped.entries()).map(([batchId, rows]) => {
    const main = rows.slice().sort((a, b) => b.totalPredictedNgPcs - a.totalPredictedNgPcs)[0];
    return {
      batchId,
      startTime: rows[0].hourKey,
      pcs: sum(rows.map(row => row.totalProducedPcs)),
      status: "Pending QC",
      okRate: average(rows.map(row => row.averagePredictedOkRate)),
      ngPcs: sum(rows.map(row => row.totalPredictedNgPcs)),
      riskLevel: highestRisk(rows.map(row => row.highestRiskLevel)),
      mainCause: main.mainCause,
      relatedStation: main.relatedStation
    };
  });
}

function buildForecastBatchRows(records) {
  return records.map(record => ({
    batchId: record.batchId,
    startTime: record.hourKey,
    pcs: record.producedPcs,
    status: "Forecast",
    okRate: record.predictedOkRate,
    ngPcs: record.predictedNgPcs,
    riskLevel: record.riskLevel,
    mainCause: record.mainCause,
    relatedStation: record.relatedStation
  }));
}

// ==============================
// Render
// ==============================

function getSeriesRecords(viewData) {
  return [...viewData.actual, ...viewData.predicted, ...viewData.forecast];
}

function renderKpiCards(viewData) {
  const records = getSeriesRecords(viewData);
  const actualRecords = viewData.actual;
  const predictedRecords = [...viewData.predicted, ...viewData.forecast];
  const stationRecords = records.length ? records : hourlyPredictedRecords;
  const topRisk = highestRisk(records.map(record => record.riskLevel || record.highestRiskLevel));

  const actualOkRate = actualRecords.length ? average(actualRecords.map(record => record.actualOkRate)) : null;
  const actualNgPcs = actualRecords.length ? sum(actualRecords.map(record => record.actualNgPcs)) : null;
  const predictedOkRate = predictedRecords.length ? average(predictedRecords.map(record => record.averagePredictedOkRate || record.predictedOkRate)) : null;
  const predictedNgPcs = predictedRecords.length ? sum(predictedRecords.map(record => record.totalPredictedNgPcs || record.predictedNgPcs)) : null;
  const stationValues = normalizeStationValues(stationRecords);

  document.getElementById("yesterdayActualOkRate").textContent = actualOkRate === null ? "--" : formatPercent(actualOkRate);
  document.getElementById("yesterdayActualNgPcs").textContent = actualNgPcs === null ? "--" : String(actualNgPcs);
  document.getElementById("todayPredictedOkRate").textContent = predictedOkRate === null ? "--" : formatPercent(predictedOkRate);
  document.getElementById("todayPredictedNgPcs").textContent = predictedNgPcs === null ? "--" : String(predictedNgPcs);
  document.getElementById("lineUtilization").textContent = formatPercent(average(stationValues.map(item => item.utilization)));
  document.getElementById("avgCycleTime").textContent = `${average(stationValues.map(item => item.cycleTime)).toFixed(1)} sec`;

  document.getElementById("yesterdayActualOkRateSub").textContent = actualOkRate === null ? "Actual hidden in this mode" : "Past 00:00 to next day 00:00 exclusive";
  document.getElementById("yesterdayActualNgPcsSub").textContent = actualNgPcs === null ? "Current / Future never show Actual QC" : "Confirmed quality result";
  document.getElementById("todayPredictedOkRateSub").textContent = predictedOkRate === null ? "Predicted hidden in Past mode" : "Current Predicted Quality Risk";
  document.getElementById("todayPredictedNgPcsSub").textContent = predictedNgPcs === null ? "No Pending QC in Past mode" : `${viewData.batchRows.filter(row => row.status === "Pending QC").length} Pending QC Batch`;
  document.getElementById("lineUtilizationSub").textContent = `${TIME_RANGE_LABELS[currentTimeRangeMode]} station average`;
  document.getElementById("avgCycleTimeSub").textContent = `Baseline ${TARGETS.cycleTime} sec / pcs`;

  [
    ["kpiYesterdayOk", actualOkRate !== null && actualOkRate < 92 ? "Medium" : "Low"],
    ["kpiYesterdayNg", actualNgPcs !== null && actualNgPcs > 35 ? "Medium" : "Low"],
    ["kpiTodayPredictedOk", predictedOkRate !== null && predictedOkRate < 85 ? "High" : predictedOkRate !== null && predictedOkRate < TARGETS.predictedOkRate ? "Medium" : "Low"],
    ["kpiTodayPredictedNg", predictedNgPcs !== null && predictedNgPcs >= TARGETS.predictedNgPcs ? "High" : predictedNgPcs !== null && predictedNgPcs >= 20 ? "Medium" : "Low"],
    ["kpiUtilization", topRisk],
    ["kpiCycleTime", topRisk]
  ].forEach(([id, risk]) => {
    const card = document.getElementById(id);
    card.classList.remove("is-low", "is-medium", "is-high");
    card.classList.add(`is-${String(risk).toLowerCase()}`);
  });
}

function normalizeStationValues(records) {
  if (!records.length) return STATIONS.map(station => ({ station: station.label, robot: station.robot, utilization: TARGETS.utilization, cycleTime: station.baselineCycleTime, riskLevel: "Low", alarmCount: 0, mainIssue: station.mainIssue }));

  return STATIONS.map((station, index) => {
    const number = index + 1;
    const utilization = average(records.map(record => record[`averageStation${number}Utilization`] ?? record[`station${number}Utilization`]));
    const cycleTime = average(records.map(record => record[`averageStation${number}CycleTime`] ?? record[`station${number}CycleTime`]));
    const alarmCount = sum(records.map(record => record[`station${number}AlarmCount`] ?? 0));
    const riskLevel = calculateRiskLevel({
      station1Utilization: number === 1 ? utilization : 85,
      station2Utilization: number === 2 ? utilization : 85,
      station3Utilization: number === 3 ? utilization : 85,
      station1CycleTime: number === 1 ? cycleTime : 39,
      station2CycleTime: number === 2 ? cycleTime : 40,
      station3CycleTime: number === 3 ? cycleTime : 39.5,
      station1AlarmCount: number === 1 ? alarmCount : 0,
      station2AlarmCount: number === 2 ? alarmCount : 0,
      station3AlarmCount: number === 3 ? alarmCount : 0,
      predictedOkRate: 95,
      predictedNgPcs: 0
    });

    return {
      station: station.label,
      robot: station.robot,
      processStep: station.processStep,
      utilization: Number(utilization.toFixed(1)),
      cycleTime: Number(cycleTime.toFixed(1)),
      alarmCount,
      riskLevel,
      mainIssue: station.mainIssue
    };
  });
}

function renderOverallStatus(viewData, warnings) {
  const panel = document.getElementById("overallStatusPanel");
  const badge = document.getElementById("overallStatusBadge");
  const topWarning = warnings[0];

  if (!topWarning) {
    document.getElementById("overallReason").textContent = `${TIME_RANGE_LABELS[currentTimeRangeMode]} has no High warning in the selected scope.`;
    badge.textContent = "LOW";
    panel.style.borderLeftColor = "#15803d";
    badge.style.background = "#dcfce7";
    badge.style.color = "#166534";
    return;
  }

  document.getElementById("overallReason").textContent = topWarning.message;
  badge.textContent = topWarning.riskLevel.toUpperCase();
  panel.style.borderLeftColor = topWarning.riskLevel === "High" ? "#b91c1c" : "#b45309";
  badge.style.background = topWarning.riskLevel === "High" ? "#fee2e2" : "#fef3c7";
  badge.style.color = topWarning.riskLevel === "High" ? "#991b1b" : "#92400e";
}

function renderStationOverview(viewData) {
  const stations = normalizeStationValues(getSeriesRecords(viewData));
  document.getElementById("stationOverview").innerHTML = stations
    .sort((a, b) => riskOrder(b.riskLevel) - riskOrder(a.riskLevel))
    .map(station => `
      <article class="station-card ${getRiskClass(station.riskLevel)}">
        <div class="station-head">
          <div>
            <h3>${escapeHtml(station.station)} / ${escapeHtml(station.robot)}</h3>
            <div class="station-sub">${escapeHtml(station.processStep)}</div>
          </div>
          <span class="risk-pill ${String(station.riskLevel).toLowerCase()}">${escapeHtml(station.riskLevel)}</span>
        </div>
        <div class="station-metrics">
          <div class="metric-block"><div class="metric-label">Utilization</div><div class="metric-value ${getTextRiskClass(station.riskLevel)}">${formatPercent(station.utilization)}</div></div>
          <div class="metric-block"><div class="metric-label">Cycle Time</div><div class="metric-value">${station.cycleTime.toFixed(1)} sec</div></div>
          <div class="metric-block"><div class="metric-label">Alarm Count</div><div class="metric-value">${station.alarmCount}</div></div>
          <div class="metric-block"><div class="metric-label">Risk Level</div><div class="metric-value">${station.riskLevel}</div></div>
        </div>
        <div class="station-issue"><strong>Main Issue / Cause:</strong> ${escapeHtml(station.mainIssue)}</div>
      </article>
    `).join("");
}

function getChartPoint(record, type) {
  const okRate = type === "Actual" ? record.actualOkRate : record.averagePredictedOkRate ?? record.predictedOkRate;
  const ngPcs = type === "Actual" ? record.actualNgPcs : record.totalPredictedNgPcs ?? record.predictedNgPcs;
  return {
    x: record.hourKey,
    y: okRate,
    type,
    ngPcs,
    riskLevel: record.riskLevel || record.highestRiskLevel,
    relatedStation: record.relatedStation,
    batchId: record.relatedBatchIds ? record.relatedBatchIds.join(", ") : record.batchId || "Actual QC"
  };
}

function renderOkNgTrendChart(viewData) {
  if (!canRenderCharts()) {
    showChartFallback("okNgTrendChart");
    return;
  }

  const labels = [...new Set([...viewData.actual, ...viewData.predicted, ...viewData.forecast].map(record => record.hourKey))];
  const actualData = viewData.actual.map(record => getChartPoint(record, "Actual"));
  const predictedData = viewData.predicted.map(record => getChartPoint(record, "Predicted"));
  const forecastData = viewData.forecast.map(record => getChartPoint(record, "Forecast"));

  if (okNgTrendChart) okNgTrendChart.destroy();
  okNgTrendChart = new Chart(document.getElementById("okNgTrendChart").getContext("2d"), {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "Past Actual OK Rate", data: actualData, parsing: { xAxisKey: "x", yAxisKey: "y" }, borderColor: "#2563eb", backgroundColor: "#2563eb", borderWidth: 3, pointRadius: 4, tension: 0.25 },
        { label: "Current Predicted OK Rate", data: predictedData, parsing: { xAxisKey: "x", yAxisKey: "y" }, borderColor: "#0f766e", backgroundColor: "#0f766e", borderDash: [7, 5], borderWidth: 3, pointRadius: 4, tension: 0.25 },
        { label: "Future Forecast OK Rate", data: forecastData, parsing: { xAxisKey: "x", yAxisKey: "y" }, borderColor: "#7c3aed", backgroundColor: "rgba(124,58,237,0.45)", borderDash: [8, 6], borderWidth: 3, pointRadius: 4, tension: 0.25 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top" },
        tooltip: {
          callbacks: {
            label(context) {
              const point = context.raw;
              return [
                `${point.type} | ${point.x}`,
                `OK Rate: ${formatPercent(point.y)}`,
                `${point.type === "Actual" ? "Actual" : "Predicted"} NG pcs: ${point.ngPcs}`,
                `Risk level: ${point.riskLevel || "Low"}`,
                `Station: ${point.relatedStation || "Line summary"}`,
                `Batch: ${point.batchId}`
              ];
            }
          }
        }
      },
      scales: {
        x: { title: { display: true, text: currentTimeRangeMode === "past" ? "Past Actual 00:00-23:59" : currentTimeRangeMode === "current" ? "Current Predicted 00:00-now" : currentTimeRangeMode === "future" ? "Future Forecast" : "Past Actual / Current Predicted / Future Forecast" } },
        y: { min: 70, max: 100, title: { display: true, text: "OK Rate (%)" } }
      }
    }
  });
}

function renderUtilizationTrendChart(viewData) {
  if (!canRenderCharts()) {
    showChartFallback("utilizationTrendChart");
    return;
  }

  const records = getSeriesRecords(viewData);
  const labels = records.map(record => record.hourKey);
  const makeData = stationNumber => records.map(record => record[`averageStation${stationNumber}Utilization`] ?? record[`station${stationNumber}Utilization`]);

  if (utilizationTrendChart) utilizationTrendChart.destroy();
  utilizationTrendChart = new Chart(document.getElementById("utilizationTrendChart").getContext("2d"), {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "Station 1 utilization", data: makeData(1), borderColor: "#2563eb", backgroundColor: "#2563eb", borderWidth: 3, pointRadius: 4, tension: 0.25 },
        { label: "Station 2 utilization", data: makeData(2), borderColor: "#dc2626", backgroundColor: "#dc2626", borderWidth: 3, pointRadius: 4, tension: 0.25 },
        { label: "Station 3 utilization", data: makeData(3), borderColor: "#f59e0b", backgroundColor: "#f59e0b", borderWidth: 3, pointRadius: 4, tension: 0.25 },
        { label: "Target utilization 85%", data: labels.map(() => TARGETS.utilization), borderColor: "#64748b", borderDash: [6, 6], borderWidth: 2, pointRadius: 0 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "top" } },
      scales: { y: { min: 45, max: 95, title: { display: true, text: "Utilization (%)" } } }
    }
  });
}

function renderCycleTimeTrendChart(viewData) {
  if (!canRenderCharts()) {
    showChartFallback("cycleTimeTrendChart");
    return;
  }

  const records = getSeriesRecords(viewData);
  const labels = records.map(record => record.hourKey);
  const makeData = stationNumber => records.map(record => record[`averageStation${stationNumber}CycleTime`] ?? record[`station${stationNumber}CycleTime`]);

  if (cycleTimeTrendChart) cycleTimeTrendChart.destroy();
  cycleTimeTrendChart = new Chart(document.getElementById("cycleTimeTrendChart").getContext("2d"), {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "Station 1 cycle time", data: makeData(1), borderColor: "#2563eb", backgroundColor: "#2563eb", borderWidth: 3, pointRadius: 4, tension: 0.25 },
        { label: "Station 2 cycle time", data: makeData(2), borderColor: "#dc2626", backgroundColor: "#dc2626", borderWidth: 3, pointRadius: 4, tension: 0.25 },
        { label: "Station 3 cycle time", data: makeData(3), borderColor: "#f59e0b", backgroundColor: "#f59e0b", borderWidth: 3, pointRadius: 4, tension: 0.25 },
        { label: "Baseline cycle time 40 sec / pcs", data: labels.map(() => TARGETS.cycleTime), borderColor: "#64748b", borderDash: [6, 6], borderWidth: 2, pointRadius: 0 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "top" } },
      scales: { y: { min: 35, max: 58, title: { display: true, text: "Cycle Time (sec / pcs)" } } }
    }
  });
}

function renderBatchRiskTable(viewData) {
  document.getElementById("batchQualityRateHeader").textContent = viewData.batchMode === "actual" ? "Actual OK Rate" : viewData.batchMode === "forecast" ? "Forecast OK Rate" : "Today Predicted OK Rate";
  document.getElementById("batchQualityNgHeader").textContent = viewData.batchMode === "actual" ? "Actual NG pcs" : viewData.batchMode === "forecast" ? "Forecast NG pcs" : "Today Predicted NG pcs";

  const tbody = document.getElementById("batchRiskTableBody");
  if (!viewData.batchRows.length) {
    tbody.innerHTML = `<tr><td colspan="9">No batch data in the selected hour.</td></tr>`;
    return;
  }

  tbody.innerHTML = viewData.batchRows
    .sort((a, b) => riskOrder(b.riskLevel) - riskOrder(a.riskLevel) || b.ngPcs - a.ngPcs)
    .map(row => `
      <tr class="batch-row ${getRiskClass(row.riskLevel)}">
        <td>${escapeHtml(row.batchId)}</td>
        <td>${escapeHtml(row.startTime)}</td>
        <td>${row.pcs}</td>
        <td><span class="state-badge ${getBadgeClass(row.status)}">${escapeHtml(row.status)}</span></td>
        <td>${formatPercent(row.okRate)}</td>
        <td>${row.ngPcs}</td>
        <td><span class="risk-pill ${String(row.riskLevel).toLowerCase()}">${escapeHtml(row.riskLevel)}</span></td>
        <td>${escapeHtml(row.mainCause)}</td>
        <td>${escapeHtml(row.relatedStation)}</td>
      </tr>
    `).join("");
}

function renderPredictionHistory() {
  const rows = selectedHour
    ? predictionHistory.filter(row => row.hourKey === selectedHour)
    : predictionHistory.slice(-36);

  const tbody = document.getElementById("predictionHistoryBody");
  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="6">No prediction history in the selected scope.</td></tr>`;
    return;
  }

  tbody.innerHTML = rows.slice().reverse().map(row => `
    <tr class="batch-row ${getRiskClass(row.riskLevel)}">
      <td>${escapeHtml(row.timestamp)}</td>
      <td>${escapeHtml(row.batchId)}</td>
      <td>${formatPercent(row.predictedOkRate)}</td>
      <td>${row.predictedNgPcs}</td>
      <td><span class="risk-pill ${String(row.riskLevel).toLowerCase()}">${escapeHtml(row.riskLevel)}</span></td>
      <td>${escapeHtml(row.relatedStation)}</td>
    </tr>
  `).join("");
}

// ==============================
// Warnings and Notification
// ==============================

function hasConsecutiveStationIssue(records, stationNumber) {
  let streak = 0;
  for (const record of records) {
    const utilization = record[`station${stationNumber}Utilization`];
    const cycleTime = record[`station${stationNumber}CycleTime`];
    const alarm = record[`station${stationNumber}AlarmCount`];
    const baseline = STATIONS[stationNumber - 1].baselineCycleTime;
    const abnormal = utilization < 70 || ((cycleTime - baseline) / baseline) * 100 > 15 || alarm >= 3;
    streak = abnormal ? streak + 1 : 0;
    if (streak >= 2) return true;
  }
  return false;
}

function generateRealtimeWarnings(viewData) {
  const warnings = [];

  viewData.predicted.forEach(hourRecord => {
    const records = hourRecord.records || [];
    const station2CycleIncrease = ((hourRecord.averageStation2CycleTime - STATIONS[1].baselineCycleTime) / STATIONS[1].baselineCycleTime) * 100;
    const highRiskCount = records.filter(record => record.riskLevel === "High").length;
    const station2Consecutive = hasConsecutiveStationIssue(records, 2);
    const shouldWarn =
      hourRecord.averagePredictedOkRate < TARGETS.predictedOkRate ||
      hourRecord.totalPredictedNgPcs >= TARGETS.predictedNgPcs ||
      hourRecord.averageStation2Utilization < 70 ||
      station2CycleIncrease > 15 ||
      hourRecord.totalAlarmCount >= 3 ||
      station2Consecutive ||
      highRiskCount >= 2;

    if (!shouldWarn) return;

    warnings.push({
      warningId: `WARN-${hourRecord.hourKey.replace(":", "")}-S2`,
      timestamp: `${hourRecord.hourKey}~${hourRecord.hourKey.slice(0, 2)}:59`,
      hourKey: hourRecord.hourKey,
      riskType: "Station2PredictedQuality",
      riskLevel: hourRecord.highestRiskLevel,
      station: "Station 2",
      batchId: hourRecord.relatedBatchIds.join(", "),
      predictedNgPcs: hourRecord.totalPredictedNgPcs,
      predictedOkRate: hourRecord.averagePredictedOkRate,
      mainCause: hourRecord.mainCause,
      message:
        `Station 2 Risk ${hourRecord.highestRiskLevel}: Between ${records[0].timestamp} and ${records[records.length - 1].timestamp}, ` +
        `cycle time increased by ${station2CycleIncrease.toFixed(1)}% and utilization dropped to ${hourRecord.averageStation2Utilization}%. ` +
        `This may affect ${hourRecord.affectedBatchCount} pending QC batches and increase predicted NG by ${hourRecord.totalPredictedNgPcs} pcs. ` +
        `Suggested checks: nozzle condition, spray pressure, robot path, and paint supply.`,
      suggestedAction: "Check nozzle condition, spray pressure, robot path, and paint supply."
    });
  });

  viewData.forecast.forEach(record => {
    if (riskOrder(record.riskLevel) < 2) return;
    warnings.push({
      warningId: `WARN-${record.hourKey.replace(":", "")}-FC`,
      timestamp: record.hourKey,
      hourKey: record.hourKey,
      riskType: "ForecastStationRisk",
      riskLevel: record.riskLevel,
      station: record.relatedStation,
      batchId: record.batchId,
      predictedNgPcs: record.predictedNgPcs,
      predictedOkRate: record.predictedOkRate,
      mainCause: record.mainCause,
      message:
        `Future Forecast NG Risk: ${record.hourKey} may continue ${record.relatedStation} risk with predicted OK rate ${formatPercent(record.predictedOkRate)} ` +
        `and forecast NG ${record.predictedNgPcs} pcs. Suggested checks: review recovery actions before this hour.`,
      suggestedAction: "Review current recovery actions before the forecast hour."
    });
  });

  if (selectedHour) {
    return warnings.filter(warning => warning.hourKey === selectedHour);
  }

  return warnings;
}

function shouldSendNotification(warning) {
  const duplicateKey = `${warning.hourKey}|${warning.station}|${warning.riskType}`;

  if (riskOrder(warning.riskLevel) < 3) {
    return { shouldSend: false, status: "Dashboard Only", duplicateKey };
  }

  if (notifiedWarnings.has(duplicateKey)) {
    return { shouldSend: false, status: "Cooldown Skipped", duplicateKey };
  }

  return { shouldSend: true, status: CONFIG.WARNING_APP_SCRIPT_URL ? "Sent" : "Mock Sent", duplicateKey };
}

async function sendWarningToGmailByAppsScript(warning) {
  const decision = shouldSendNotification(warning);
  const payload = {
    warningId: warning.warningId,
    timestamp: warning.timestamp,
    hourKey: warning.hourKey,
    riskLevel: warning.riskLevel,
    station: warning.station,
    batchId: warning.batchId,
    message: warning.message,
    mainCause: warning.mainCause,
    suggestedAction: warning.suggestedAction,
    predictedNgPcs: warning.predictedNgPcs,
    predictedOkRate: warning.predictedOkRate,
    recipientRole: "manager"
  };

  if (!decision.shouldSend) {
    addNotificationHistory({ ...payload, status: decision.status });
    return decision.status;
  }

  try {
    await postWarningNotificationPayload(payload);
    markWarningAsNotified(warning, decision.duplicateKey);
    showToast(`${warning.station} ${warning.riskLevel}: ${warning.batchId}`, String(warning.riskLevel).toLowerCase());
    addNotificationHistory({ ...payload, status: decision.status });
    return decision.status;
  } catch (error) {
    console.error("Warning notification failed", error);
    addNotificationHistory({ ...payload, status: "Failed" });
    return "Failed";
  }
}

function markWarningAsNotified(warning, duplicateKey) {
  notifiedWarnings.add(duplicateKey);
}

function isRealtimeNotificationScope(warning) {
  const latestHourKey = todayRealtimeRecords[todayRealtimeRecords.length - 1]?.hourKey;
  return currentTimeRangeMode === "current" && warning.hourKey === latestHourKey;
}

function recordDashboardOnlyNotification(warning) {
  addNotificationHistory({
    warningId: warning.warningId,
    timestamp: warning.timestamp,
    hourKey: warning.hourKey,
    riskLevel: warning.riskLevel,
    station: warning.station,
    batchId: warning.batchId,
    message: warning.message,
    mainCause: warning.mainCause,
    suggestedAction: warning.suggestedAction,
    predictedNgPcs: warning.predictedNgPcs,
    predictedOkRate: warning.predictedOkRate,
    recipientRole: "manager",
    status: "Dashboard Only"
  });
}

function renderWarningMessages(viewData) {
  const warnings = generateRealtimeWarnings(viewData);
  const container = document.getElementById("warningMessageList");

  if (!warnings.length) {
    container.innerHTML = `
      <article class="warning-message risk-low">
        <h3>No major manager warning</h3>
        <p>${escapeHtml(TIME_RANGE_LABELS[currentTimeRangeMode])} has no High warning in the selected scope.</p>
      </article>
    `;
    return warnings;
  }

  warnings.forEach(async warning => {
    if (isRealtimeNotificationScope(warning)) {
      warning.notificationStatus = await sendWarningToGmailByAppsScript(warning);
    } else {
      warning.notificationStatus = "Dashboard Only";
      recordDashboardOnlyNotification(warning);
    }
    renderNotificationHistory();
  });

  container.innerHTML = warnings.map(warning => `
    <article class="warning-message ${getRiskClass(warning.riskLevel)}">
      <h3>${escapeHtml(warning.station)} / ${escapeHtml(warning.batchId)}</h3>
      <p>${escapeHtml(warning.message)}</p>
      <div class="warning-meta">
        <span>Hour: ${escapeHtml(warning.hourKey)}</span>
        <span>Predicted NG pcs: ${warning.predictedNgPcs}</span>
        <span class="warning-status">${escapeHtml(warning.riskLevel === "High" ? "Notification evaluated" : "Dashboard Only")}</span>
      </div>
    </article>
  `).join("");

  return warnings;
}

function renderNotificationHistory() {
  const tbody = document.getElementById("notificationHistoryBody");
  if (!notificationHistory.length) {
    tbody.innerHTML = `<tr><td colspan="7">No notification history yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = notificationHistory.slice(0, 30).map(item => `
    <tr class="batch-row ${getRiskClass(item.riskLevel)}">
      <td>${escapeHtml(item.timestamp)}</td>
      <td>${escapeHtml(item.hourKey)}</td>
      <td><span class="risk-pill ${String(item.riskLevel).toLowerCase()}">${escapeHtml(item.riskLevel)}</span></td>
      <td>${escapeHtml(item.station)}</td>
      <td>${escapeHtml(item.batchId)}</td>
      <td>${escapeHtml(item.message)}</td>
      <td>${escapeHtml(item.status)}</td>
    </tr>
  `).join("");
}

// function triggerTestNotification() {
//   const viewData = filterDataBySelectedHour(selectedHour);
//   const warning = generateRealtimeWarnings(viewData).find(item => item.riskLevel === "High");

//   if (!warning) {
//     showToast("No High warning in the selected scope.", "low");
//     setNotificationStatus("No High warning available for test notification.", "notify-idle");
//     return;
//   }

//   sendWarningToGmailByAppsScript({ ...warning, warningId: `${warning.warningId}-TEST`, riskType: `${warning.riskType}-TEST` }).then(status => {
//     setNotificationStatus(`Test warning notification status: ${status}.`, status === "Failed" ? "notify-error" : "notify-success");
//     renderNotificationHistory();
//   });
// }
function triggerTestNotification() {
  sendDirectTestGmailByAppsScript();
}

// ==============================
// Validation
// ==============================

function renderTomorrowValidation() {
  const data = {
    yesterdayPredictedOkRate: 91.4,
    yesterdayActualOkRate: 92.6,
    predictionError: -1.2,
    modelAccuracy: 94.8,
    yesterdayPredictedNgPcs: 41,
    yesterdayActualNgPcs: 35
  };

  const cards = [
    { title: "Yesterday Predicted OK Rate", value: formatPercent(data.yesterdayPredictedOkRate), risk: "Low", sub: "Prediction made before QC confirmation." },
    { title: "Yesterday Actual OK Rate", value: formatPercent(data.yesterdayActualOkRate), risk: "Low", sub: "Confirmed by QC result available today." },
    { title: "Prediction Error", value: `${data.predictionError > 0 ? "+" : ""}${data.predictionError.toFixed(1)} pts`, risk: Math.abs(data.predictionError) > 2 ? "High" : "Low", sub: "Predicted OK rate minus actual OK rate." },
    { title: "Model Accuracy", value: formatPercent(data.modelAccuracy), risk: data.modelAccuracy >= 94 ? "Low" : "Medium", sub: "Manager can judge model trust here." },
    { title: "Yesterday Predicted NG pcs", value: `${data.yesterdayPredictedNgPcs}`, risk: "Medium", sub: "Predicted before actual QC confirmation." },
    { title: "Yesterday Actual NG pcs", value: `${data.yesterdayActualNgPcs}`, risk: "Medium", sub: "Confirmed by actual QC." }
  ];

  document.getElementById("tomorrowValidation").innerHTML = cards.map(card => `
    <article class="validation-card">
      <div class="validation-title">${escapeHtml(card.title)}</div>
      <div class="validation-value ${getTextRiskClass(card.risk)}">${escapeHtml(card.value)}</div>
      <div class="validation-sub">${escapeHtml(card.sub)}</div>
    </article>
  `).join("");
}

// ==============================
// Dashboard Flow
// ==============================

function updateDashboardBySelectedHour(hour) {
  const viewData = filterDataBySelectedHour(hour);
  renderKpiCards(viewData);
  renderStationOverview(viewData);
  renderOkNgTrendChart(viewData);
  renderUtilizationTrendChart(viewData);
  renderCycleTimeTrendChart(viewData);
  renderBatchRiskTable(viewData);
  renderPredictionHistory();
  const warnings = renderWarningMessages(viewData);
  renderOverallStatus(viewData, warnings);
  renderNotificationHistory();
  renderTomorrowValidation();
}

function bindControls() {
  document.getElementById("timeRangeButtons").addEventListener("click", event => {
    const button = event.target.closest("[data-mode]");
    if (!button) return;
    setTimeRangeMode(button.dataset.mode);
  });

  document.getElementById("timeBar").addEventListener("click", event => {
    const button = event.target.closest("[data-hour]");
    if (!button || button.disabled) return;
    setSelectedHour(button.dataset.hour);
  });

  document.getElementById("simulateNextUpdateBtn").addEventListener("click", () => {
    simulateNext20MinUpdate();
  });

  document.getElementById("testNotifyBtn").addEventListener("click", () => {
    triggerTestNotification();
  });
}

async function initDashboard() {
  historicalActualRecords = await fetchHistoricalActualData();
  await refreshRealtimeData();
  renderTimeRangeButtons();
  renderTimeBar();
  bindControls();
  updateDashboardBySelectedHour(selectedHour);
  startRealtimePolling();
  setNotificationStatus("Current Predicted data loaded. High risk warnings use mock notification until Apps Script URL is configured.", "notify-idle");
}

initDashboard();
