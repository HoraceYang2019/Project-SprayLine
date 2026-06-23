// ==============================
// Config - keep for future DB / Apps Script integration
// ==============================

const CONFIG = {
  // Simulate the UI as if it is connected to Project-SprayLine API.
  // The responses below still come from frontend mock data, but they use the same API/schema shape.
  USE_MOCK_DATA: false,
  SIMULATED_API_ENABLED: false,

  // Legacy single endpoint. If your backend returns the old Manager UI aggregate payload, fill this.
  HISTORICAL_ACTUAL_API_URL: "",
  DB_API_URL: "",
  FORECAST_API_URL: "",

  // Project-SprayLine Dashboard v15 / DB Schema v2 endpoints.
  // When API_BASE_URL is set and USE_MOCK_DATA is false, the UI will call these routes:
  // /api/v1/lines/{line_id}/stations/latest
  // /api/v1/lines/{line_id}/kpi
  // /api/v1/lines/{line_id}/charts/quality-trend
  // /api/v1/lines/{line_id}/charts/utilization-trend
  // /api/v1/lines/{line_id}/charts/cycle-time-trend
  // /api/v1/lines/{line_id}/diagnosis/latest
  // /api/v1/lines/{line_id}/alerts/pending
  // /api/v1/lines/{line_id}/prediction-accuracy
  API_BASE_URL: "http://localhost:8011",
  API_USE_PROJECT_SCHEMA: true,
  API_LINE_IDS: ["line_1", "line_2", "line_3"],
  API_TREND_TIMESTEP: "hour",
  API_DATE: "2026-06-08",
  SIMULATED_API_START_DATE: "2026-06-08",
  SIMULATED_API_START_HOUR: 0,
  SIMULATED_API_MAX_HOUR: 23,
  SIMULATED_API_STEP_HOURS: 1,

  WARNING_APP_SCRIPT_URL: "https://script.google.com/macros/s/AKfycbyvPzX3epFpOH9AUFLLlD_-W4EXCOULHInUZKfmnCyJHlrCOY_HYTNSCBLtm3ZVzoWnBQ/exec",
  DB_POLL_INTERVAL_MS: 30 * 1000,
  MOCK_POLL_INTERVAL_MS: 5000,
  SIMULATED_API_UPLOAD_INTERVAL_MS: 5000,
  SIMULATED_HISTORY_STORAGE_KEY: "spray_manager_daily_archive_v3",
  SIMULATED_HOURLY_STORAGE_KEY: "spray_manager_hourly_snapshots_v3",
  SIMULATED_STATE_STORAGE_KEY: "spray_manager_simulated_api_state_v3",

  // Keep old simulated archive keys readable so archived review does not disappear
  // after a version upgrade. New writes still go to v3, but v1/v2 data is migrated.
  SIMULATED_HISTORY_STORAGE_LEGACY_KEYS: [
    "spray_manager_daily_archive_v2",
    "spray_manager_daily_archive_v1"
  ],
  SIMULATED_HOURLY_STORAGE_LEGACY_KEYS: [
    "spray_manager_hourly_snapshots_v2",
    "spray_manager_hourly_snapshots_v1"
  ],
  SIMULATED_STATE_STORAGE_LEGACY_KEYS: [
    "spray_manager_simulated_api_state_v2",
    "spray_manager_simulated_api_state_v1"
  ]
};

// ==============================
// Mock database / web service response
// This object is intentionally shaped like an API response.
// Later, replace this with fetch(DB_API_URL).json().
// ==============================

const MOCK_DATABASE_RESPONSE = {
  responseMeta: {
    requestId: "mock-sprayline-manager-20260609-001",
    source: "mock_web_service",
    apiVersion: "manager-ui-v3",
    generatedAt: "2026-06-09T10:20:00+08:00",
    dataWindow: {
      currentStart: "2026-06-09T00:00:00+08:00",
      currentEnd: "2026-06-09T10:20:00+08:00",
      historicalBaseline: "last_week_same_period",
      forecastHorizonDays: 7
    },
    dataCompletenessPct: 65,
    weekProgress: "3 / 5 工作日"
  },

  line: {
    lineId: "spray_line_1",
    lineName: "Spray Line 1",
    plant: "Demo Factory",
    processFlow: ["底色層", "顏色層", "保護層"]
  },

  stationResponsibility: {
    line_1: {
      stationName: "第一站",
      layerName: "底色層",
      machineName: "第一站噴塗機",
      engineerRole: "第一站負責工程師",
      engineerEmail: "station1.engineer@example.com"
    },
    line_2: {
      stationName: "第二站",
      layerName: "顏色層",
      machineName: "第二站噴塗機",
      engineerRole: "第二站負責工程師",
      engineerEmail: "station2.engineer@example.com"
    },
    line_3: {
      stationName: "第三站",
      layerName: "保護層",
      machineName: "第三站噴塗機",
      engineerRole: "第三站負責工程師",
      engineerEmail: "station3.engineer@example.com"
    }
  },

  stationTelemetry: [
    {
      lineId: "line_1",
      timestamp: "2026-06-09T10:20:00+08:00",
      recipeId: "BASE-WHITE-01",
      state: "running",
      metrics: {
        pressure_bar: 2.18,
        flow_rate_ml_min: 124,
        spray_width_mm: 182,
        target_min_mm: 176,
        target_max_mm: 190,
        temperature_c: 27.8,
        availability_pct: 87.2,
        maintainability_pct: 92.4,
        clog_rate_pct: 6.8,
        quality_score_pct: 93.6,
        utilization_pct: 82.5,
        cycle_time_sec: 46.8
      },
      baseline: {
        pressure_bar: 2.2,
        flow_rate_ml_min: 126,
        quality_score_pct: 95.0,
        utilization_pct: 85.0,
        cycle_time_sec: 45.0
      },
      componentHealth: {
        nozzle: "normal",
        filter_mesh: "normal",
        spray_width: "normal"
      },
      predictedQuality: {
        ok_rate_pct: 93.4,
        ng_pcs_next_qc: 128,
        riskLevel: "normal",
        riskText: "底色層目前穩定，但仍需確認是否影響後段顏色層。"
      }
    },
    {
      lineId: "line_2",
      timestamp: "2026-06-09T10:20:00+08:00",
      recipeId: "COLOR-WHITE-01",
      state: "warning",
      metrics: {
        pressure_bar: 2.52,
        flow_rate_ml_min: 111,
        spray_width_mm: 196,
        target_min_mm: 178,
        target_max_mm: 190,
        temperature_c: 29.1,
        availability_pct: 78.1,
        maintainability_pct: 84.5,
        clog_rate_pct: 14.6,
        quality_score_pct: 89.1,
        utilization_pct: 74.6,
        cycle_time_sec: 52.4
      },
      baseline: {
        pressure_bar: 2.24,
        flow_rate_ml_min: 126,
        quality_score_pct: 95.2,
        utilization_pct: 85.8,
        cycle_time_sec: 45.2
      },
      componentHealth: {
        nozzle: "warning",
        filter_mesh: "warning",
        spray_width: "out_of_range"
      },
      predictedQuality: {
        ok_rate_pct: 90.2,
        ng_pcs_next_qc: 610,
        riskLevel: "warning",
        riskText: "第二站 / 顏色層風險最高，噴幅偏寬、流量偏低且堵塞率偏高。"
      }
    },
    {
      lineId: "line_3",
      timestamp: "2026-06-09T10:20:00+08:00",
      recipeId: "CLEAR-COAT-01",
      state: "running",
      metrics: {
        pressure_bar: 2.07,
        flow_rate_ml_min: 119,
        spray_width_mm: 187,
        target_min_mm: 180,
        target_max_mm: 192,
        temperature_c: 28.4,
        availability_pct: 84.8,
        maintainability_pct: 89.2,
        clog_rate_pct: 8.7,
        quality_score_pct: 92.0,
        utilization_pct: 80.4,
        cycle_time_sec: 48.1
      },
      baseline: {
        pressure_bar: 2.1,
        flow_rate_ml_min: 121,
        quality_score_pct: 94.1,
        utilization_pct: 84.0,
        cycle_time_sec: 46.0
      },
      componentHealth: {
        nozzle: "normal",
        filter_mesh: "monitor",
        spray_width: "normal"
      },
      predictedQuality: {
        ok_rate_pct: 92.1,
        ng_pcs_next_qc: 214,
        riskLevel: "monitor",
        riskText: "保護層需追蹤確認，避免放大顏色層造成的外觀不良。"
      }
    }
  ],

  productionKpi: {
    currentPeriod: {
      producedPcs: 11950,
      plannedPcs: 12800,
      estimatedEfficiencyPct: 78.2,
      estimatedOkRatePct: 90.2,
      predictedNgPcs: 610,
      estimatedDowntimeMin: 190
    },
    previousPeriod: {
      producedPcs: 12800,
      actualEfficiencyPct: 86.0,
      actualOkRatePct: 94.5,
      actualNgPcs: 420,
      utilizationPct: 85.8,
      performancePct: 92.0
    },
    yesterdayActual: {
      actualEfficiencyPct: 84.5,
      actualOkRatePct: 92.6,
      actualNgPcs: 35
    },
    todayEstimate: {
      estimatedEfficiencyPct: 76.8,
      estimatedOkRatePct: 90.2,
      predictedNgPcs: 41
    },
    monthToDate: {
      estimatedEfficiencyPct: 80.5,
      lastMonthSamePeriodActualEfficiencyPct: 85.2
    }
  },

  qualityValidation: {
    validationDate: "2026-06-08",
    predictedOkRatePct: 91.4,
    actualOkRatePct: 92.6,
    predictedNgPcs: 41,
    actualNgPcs: 35,
    modelTrustLevel: "良好",
    modelInputSource: "station_telemetry + production_kpi + qc_history"
  },

  qualityHistory: [
    {
      qcDate: "2026-06-08",
      workOrder: "WO-20260608-002",
      partNo: "Cover-A",
      colorCode: "White",
      okPcs: 721,
      ngPcs: 35,
      defectTypes: ["色差", "橘皮", "流掛"]
    },
    {
      qcDate: "2026-06-07",
      workOrder: "WO-20260607-004",
      partNo: "Cover-A",
      colorCode: "White",
      okPcs: 694,
      ngPcs: 42,
      defectTypes: ["膜厚不足", "色差"]
    }
  ],

  forecastNoAction: {
    horizonDays: 7,
    estimatedEfficiencyPct: 72.5,
    estimatedOkRatePct: 87.8,
    extraLostProductionPcs: 840,
    extraPredictedNgPcs: 175,
    riskText: "若第二站顏色層不改善，未來 7 天可能造成額外產量缺口與 NG 增加。"
  }
};


// ==============================
// Mock 24-hour quality score series
// 模擬今天 00:00-23:00 每小時品質分數，未來可由 DB/API 回傳。
// 建議 API 欄位格式：quality_score_hourly_today[lineId] = [{ hourKey, quality_score_pct }]
// ==============================

const MOCK_QUALITY_SCORE_HOURLY_TODAY = {
  line_1: [
    94.2, 94.1, 94.0, 93.9, 94.0, 93.8, 93.7, 93.6,
    93.8, 93.9, 93.7, 93.6, 93.8, 93.7, 93.5, 93.6,
    93.4, 93.5, 93.6, 93.8, 93.7, 93.6, 93.5, 93.6
  ],
  line_2: [
    92.8, 92.6, 92.4, 92.1, 91.8, 91.4, 91.1, 90.9,
    90.5, 90.2, 89.9, 89.7, 89.5, 89.2, 89.0, 88.8,
    88.6, 88.4, 88.7, 88.9, 89.0, 89.1, 89.2, 89.1
  ],
  line_3: [
    92.7, 92.8, 92.9, 93.0, 92.8, 92.7, 92.6, 92.7,
    92.8, 92.9, 93.0, 93.1, 93.0, 92.9, 92.8, 92.9,
    93.0, 93.1, 93.0, 92.9, 92.8, 92.9, 93.0, 92.8
  ]
};

const MOCK_STATION_DETAIL_HOURLY_TODAY = {
  line_1: {
    quality_score_pct: MOCK_QUALITY_SCORE_HOURLY_TODAY.line_1,
    utilization_pct: [84.8, 84.6, 84.5, 84.3, 84.1, 84.0, 83.8, 83.6, 83.4, 83.2, 83.1, 83.0, 82.9, 82.8, 82.7, 82.6, 82.5, 82.4, 82.3, 82.4, 82.5, 82.6, 82.5, 82.5],
    cycle_time_sec: [45.2, 45.3, 45.4, 45.5, 45.5, 45.6, 45.7, 45.8, 45.9, 46.0, 46.1, 46.0, 46.2, 46.3, 46.4, 46.5, 46.4, 46.6, 46.7, 46.8, 46.7, 46.8, 46.8, 46.8]
  },
  line_2: {
    quality_score_pct: MOCK_QUALITY_SCORE_HOURLY_TODAY.line_2,
    utilization_pct: [83.1, 82.5, 81.8, 80.7, 79.9, 79.0, 78.2, 77.4, 76.8, 76.1, 75.6, 75.0, 74.7, 74.2, 73.8, 73.4, 72.9, 72.4, 72.1, 72.6, 73.0, 73.5, 74.0, 74.6],
    cycle_time_sec: [46.1, 46.5, 47.0, 47.8, 48.4, 49.1, 49.8, 50.4, 51.0, 51.7, 52.2, 52.7, 53.1, 53.5, 53.8, 54.1, 54.4, 54.8, 54.2, 53.6, 53.0, 52.8, 52.6, 52.4]
  },
  line_3: {
    quality_score_pct: MOCK_QUALITY_SCORE_HOURLY_TODAY.line_3,
    utilization_pct: [82.0, 82.1, 82.2, 82.3, 82.2, 82.0, 81.8, 81.6, 81.5, 81.4, 81.2, 81.0, 80.9, 80.7, 80.6, 80.5, 80.4, 80.5, 80.6, 80.5, 80.4, 80.4, 80.5, 80.4],
    cycle_time_sec: [46.2, 46.3, 46.4, 46.5, 46.6, 46.7, 46.8, 47.0, 47.2, 47.4, 47.5, 47.6, 47.7, 47.9, 48.0, 48.1, 48.1, 48.2, 48.2, 48.1, 48.1, 48.1, 48.1, 48.1]
  }
};


// ==============================
// Project-SprayLine DB Schema v2 / Dashboard v15 integration layer
// Source in project: SprayLine_3/少榆0602ver_5/schema + templates + docs/api_v1_routes.csv
// This layer keeps the Manager UI connected to DB/web-service contracts without hard-coding UI-only data.
// ==============================

const PROJECT_STATION_META = {
  line_1: {
    stationName: "第一站",
    layerName: "底色層",
    machineName: "第一站噴塗機",
    stationNameZh: "底漆站",
    stationNameEn: "Primer Station",
    engineerRole: "第一站負責工程師",
    engineerEmail: "station1.engineer@example.com",
    recipeId: "BASE-WHITE-01"
  },
  line_2: {
    stationName: "第二站",
    layerName: "顏色層",
    machineName: "第二站噴塗機",
    stationNameZh: "面漆站",
    stationNameEn: "Topcoat Station",
    engineerRole: "第二站負責工程師",
    engineerEmail: "station2.engineer@example.com",
    recipeId: "COLOR-WHITE-01"
  },
  line_3: {
    stationName: "第三站",
    layerName: "保護層",
    machineName: "第三站噴塗機",
    stationNameZh: "金漆站",
    stationNameEn: "Clearcoat Station",
    engineerRole: "第三站負責工程師",
    engineerEmail: "station3.engineer@example.com",
    recipeId: "CLEAR-COAT-01"
  }
};

const PROJECT_SCHEMA_DB_MAP = {
  station_latest: {
    route: "/api/v1/lines/{line_id}/stations/latest",
    schema: "station_latest.schema.json",
    dbTables: ["runtime_window", "runtime_signal", "runtime_reference", "runtime_metric", "robot_pose"],
    uiUse: "三站最新壓力、流量、噴幅、品質分數、稼動率、Cycle Time、元件狀態"
  },
  quality_trend: {
    route: "/api/v1/lines/{line_id}/charts/quality-trend",
    schema: "quality_trend.schema.json",
    dbTables: ["qc_result", "ml_prediction_result"],
    uiUse: "Past / Current / Future 的 QC 或品質分數曲線"
  },
  utilization_trend: {
    route: "/api/v1/lines/{line_id}/charts/utilization-trend",
    schema: "utilization_trend.schema.json",
    dbTables: ["runtime_metric"],
    uiUse: "Past / Current / Future 的稼動率曲線"
  },
  cycle_time_trend: {
    route: "/api/v1/lines/{line_id}/charts/cycle-time-trend",
    schema: "cycle_time_trend.schema.json",
    dbTables: ["part_history"],
    uiUse: "Past / Current / Future 的 Cycle Time 曲線"
  },
  diagnosis_latest: {
    route: "/api/v1/lines/{line_id}/diagnosis/latest",
    schema: "diagnosis_latest.schema.json",
    dbTables: ["diagnosis_result", "filter_threshold", "nozzle_threshold", "process_threshold"],
    uiUse: "噴嘴、濾網、噴幅、壓力流量、品質異常原因判斷"
  },
  kpi_summary: {
    route: "/api/v1/lines/{line_id}/kpi",
    schema: "kpi_summary.schema.json",
    dbTables: ["ml_prediction_result", "runtime_metric", "part_history", "qc_result"],
    uiUse: "預測良率、預測 NG、整線稼動率、平均 Cycle Time"
  },
  pending_alerts: {
    route: "/api/v1/lines/{line_id}/alerts/pending",
    schema: "pending_alerts.schema.json",
    dbTables: ["alert_log", "diagnosis_result", "ml_prediction_result", "qc_result"],
    uiUse: "只顯示待處理 / warning / alarm 的站別問題"
  },
  prediction_accuracy: {
    route: "/api/v1/lines/{line_id}/prediction-accuracy",
    schema: "prediction_accuracy.schema.json",
    dbTables: ["qc_result", "ml_prediction_result"],
    uiUse: "預測驗證：昨日預測 OK 與實際 QC OK 的誤差"
  }
};


let SIMULATED_API_UPLOAD_INDEX = 0;
let SIMULATED_API_DAY_INDEX = 0;
let SIMULATED_DECISION_HISTORY = [];
let latestDecisionSnapshot = null;
let previousDecisionSnapshot = null;

const SIMULATED_BASE_METRICS = {
  line_1: {
    state: "running",
    pressure_bar: 2.18,
    flow_rate_ml_min: 124,
    spray_width_mm: 182,
    target_min_mm: 176,
    target_max_mm: 190,
    temperature_c: 27.8,
    availability_pct: 87.2,
    maintainability_pct: 92.4,
    clog_rate_pct: 6.8,
    quality_score_pct: 93.6,
    utilization_pct: 82.5,
    cycle_time_sec: 46.8,
    componentHealth: { nozzle: "normal", filter_mesh: "normal", spray_width: "normal" }
  },
  line_2: {
    state: "running",
    pressure_bar: 2.26,
    flow_rate_ml_min: 126,
    spray_width_mm: 185,
    target_min_mm: 178,
    target_max_mm: 190,
    temperature_c: 28.2,
    availability_pct: 86.5,
    maintainability_pct: 90.5,
    clog_rate_pct: 6.4,
    quality_score_pct: 93.2,
    utilization_pct: 82.4,
    cycle_time_sec: 47.3,
    componentHealth: { nozzle: "normal", filter_mesh: "normal", spray_width: "normal" }
  },
  line_3: {
    state: "running",
    pressure_bar: 2.07,
    flow_rate_ml_min: 119,
    spray_width_mm: 187,
    target_min_mm: 178,
    target_max_mm: 190,
    temperature_c: 27.2,
    availability_pct: 85.9,
    maintainability_pct: 88.8,
    clog_rate_pct: 8.7,
    quality_score_pct: 92.8,
    utilization_pct: 80.4,
    cycle_time_sec: 48.1,
    componentHealth: { nozzle: "normal", filter_mesh: "normal", spray_width: "normal" }
  }
};


function getDateKeyFromTimestamp(timestamp) {
  const match = String(timestamp || "").match(/^(\d{4}-\d{2}-\d{2})/);
  return match ? match[1] : getActiveApiDateKey();
}

function addDaysToDateKey(dateKey, days) {
  const date = parseDateKey(dateKey);
  date.setDate(date.getDate() + Number(days || 0));
  return getDateKey(date);
}

function getActiveApiDateKey() {
  const startDate = CONFIG.SIMULATED_API_START_DATE || CONFIG.API_DATE || getTodayKey();
  if (!CONFIG.SIMULATED_API_ENABLED) return CONFIG.API_DATE || startDate;
  return addDaysToDateKey(startDate, SIMULATED_API_DAY_INDEX);
}

function getInitialReportDateKey() {
  return CONFIG.SIMULATED_API_ENABLED ? getActiveApiDateKey() : (CONFIG.API_DATE || getTodayKey());
}

function safeReadLocalStorageJson(key, fallback) {
  if (typeof localStorage === "undefined" || !key) return fallback;
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (error) {
    console.warn(`[LocalStorage] failed to read ${key}`, error);
    return fallback;
  }
}

function mergeObjectStores(primary, legacyStores = []) {
  const merged = { ...(primary || {}) };
  legacyStores.forEach(store => {
    Object.entries(store || {}).forEach(([key, value]) => {
      if (!merged[key]) merged[key] = value;
    });
  });
  return merged;
}

function getSimulatedArchiveStore() {
  if (typeof localStorage === "undefined") return {};

  const primary = safeReadLocalStorageJson(CONFIG.SIMULATED_HISTORY_STORAGE_KEY, {});
  const legacyStores = (CONFIG.SIMULATED_HISTORY_STORAGE_LEGACY_KEYS || [])
    .map(key => safeReadLocalStorageJson(key, {}));
  const merged = mergeObjectStores(primary, legacyStores);

  // Migrate legacy archived dates into the current key so the dropdown keeps
  // showing 已封存日期 after the next page reload.
  if (Object.keys(merged).length !== Object.keys(primary || {}).length) {
    saveSimulatedArchiveStore(merged);
  }

  return merged;
}

function saveSimulatedArchiveStore(store) {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(CONFIG.SIMULATED_HISTORY_STORAGE_KEY, JSON.stringify(store || {}));
  } catch (error) {
    console.warn("[Archive] failed to save daily archive", error);
  }
}

function getSimulatedStateStore() {
  if (typeof localStorage === "undefined") return null;

  const primary = safeReadLocalStorageJson(CONFIG.SIMULATED_STATE_STORAGE_KEY, null);
  if (primary) return primary;

  for (const legacyKey of CONFIG.SIMULATED_STATE_STORAGE_LEGACY_KEYS || []) {
    const legacyState = safeReadLocalStorageJson(legacyKey, null);
    if (legacyState) return legacyState;
  }

  return null;
}

function saveSimulatedApiState(reason = "state_update") {
  if (!CONFIG.SIMULATED_API_ENABLED || typeof localStorage === "undefined") return;
  const maxUploadIndex = Math.max(
    0,
    Number(CONFIG.SIMULATED_API_MAX_HOUR || 23) - Number(CONFIG.SIMULATED_API_START_HOUR || 0)
  );
  try {
    localStorage.setItem(CONFIG.SIMULATED_STATE_STORAGE_KEY, JSON.stringify({
      reason,
      savedAt: new Date().toISOString(),
      startDate: CONFIG.SIMULATED_API_START_DATE || CONFIG.API_DATE || getTodayKey(),
      activeDate: getActiveApiDateKey(),
      dayIndex: Math.max(0, Number(SIMULATED_API_DAY_INDEX || 0)),
      uploadIndex: Math.max(0, Math.min(maxUploadIndex, Number(SIMULATED_API_UPLOAD_INDEX || 0))),
      currentHour: getSimulatedApiCurrentHour()
    }));
  } catch (error) {
    console.warn("[Simulation state] failed to save state", error);
  }
}

function getDateDiffDays(startDateKey, targetDateKey) {
  const start = parseDateKey(startDateKey);
  const target = parseDateKey(targetDateKey);
  return Math.round((target.getTime() - start.getTime()) / (24 * 60 * 60 * 1000));
}

function hydrateSimulatedApiStateFromLocalStorage() {
  if (!CONFIG.SIMULATED_API_ENABLED) return;

  const startDate = CONFIG.SIMULATED_API_START_DATE || CONFIG.API_DATE || getTodayKey();
  const storedState = getSimulatedStateStore() || {};
  const maxUploadIndex = Math.max(
    0,
    Number(CONFIG.SIMULATED_API_MAX_HOUR || 23) - Number(CONFIG.SIMULATED_API_START_HOUR || 0)
  );

  let dayIndex = Number.isFinite(Number(storedState.dayIndex)) ? Number(storedState.dayIndex) : 0;
  let uploadIndex = Number.isFinite(Number(storedState.uploadIndex)) ? Number(storedState.uploadIndex) : 0;

  const latestArchivedDate = getArchivedDateKeys()[0];
  const storedActiveDate = addDaysToDateKey(startDate, dayIndex);

  // Important: the archive survives page refresh, but normal JS variables do not.
  // If the archive already contains dates newer than the in-memory simulated day,
  // continue from the day after the latest archive instead of jumping back to the old start date.
  if (latestArchivedDate && latestArchivedDate >= storedActiveDate) {
    const nextActiveDate = addDaysToDateKey(latestArchivedDate, 1);
    dayIndex = getDateDiffDays(startDate, nextActiveDate);
    uploadIndex = 0;
  }

  SIMULATED_API_DAY_INDEX = Math.max(0, dayIndex);
  SIMULATED_API_UPLOAD_INDEX = Math.max(0, Math.min(maxUploadIndex, uploadIndex));
  saveSimulatedApiState("hydrate_from_local_storage");
}

function getArchivedDateKeys() {
  return Object.keys(getSimulatedArchiveStore()).sort().reverse();
}

function getArchivedDatabaseResponse(dateKey) {
  const archived = getSimulatedArchiveStore()[dateKey]?.dbResponse || null;
  return archived ? ensureHistoricalActualQualityData(archived, dateKey) : null;
}

function archiveDatabaseResponseForDate(dateKey, dbResponse, reason = "day_completed") {
  if (!dateKey || !dbResponse) return;
  const store = getSimulatedArchiveStore();
  const actualDbResponse = actualizeDatabaseResponseFromDb(dbResponse, dateKey);
  store[dateKey] = {
    date: dateKey,
    reason,
    archivedAt: new Date().toISOString(),
    qualitySource: "DB qc_result actual, not stored prediction",
    dbResponse: JSON.parse(JSON.stringify(actualDbResponse))
  };
  saveSimulatedArchiveStore(store);
}


function getSimulatedHourlyStore() {
  if (typeof localStorage === "undefined") return {};

  const primary = safeReadLocalStorageJson(CONFIG.SIMULATED_HOURLY_STORAGE_KEY, {});
  const legacyStores = (CONFIG.SIMULATED_HOURLY_STORAGE_LEGACY_KEYS || [])
    .map(key => safeReadLocalStorageJson(key, {}));
  const merged = mergeObjectStores(primary, legacyStores);

  // Migrate old hourly problem markers into the current key so review mode can
  // still show problem hours after a version upgrade.
  if (Object.keys(merged).length !== Object.keys(primary || {}).length) {
    saveSimulatedHourlyStore(merged);
  }

  return merged;
}

function saveSimulatedHourlyStore(store) {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(CONFIG.SIMULATED_HOURLY_STORAGE_KEY, JSON.stringify(store || {}));
  } catch (error) {
    console.warn("[Hourly history] failed to save hourly snapshots", error);
  }
}

function getResponseHourFromDb(dbResponse) {
  const rawTime =
    dbResponse?.responseMeta?.dataWindow?.currentEnd ||
    dbResponse?.responseMeta?.generatedAt ||
    dbResponse?.generated_at ||
    "";
  const match = String(rawTime).match(/T(\d{2}):/);
  const hour = match ? Number(match[1]) : 0;
  return Math.max(0, Math.min(23, Number.isFinite(hour) ? hour : 0));
}

function getResponseDateKeyFromDb(dbResponse) {
  return getDateKeyFromTimestamp(
    dbResponse?.responseMeta?.dataWindow?.currentEnd ||
    dbResponse?.responseMeta?.generatedAt ||
    dbResponse?.generated_at ||
    selectedReportDate ||
    getActiveApiDateKey()
  );
}

function createDecisionSnapshotForDb(dbResponse) {
  if (!dbResponse) return null;

  const previousDb = currentDatabaseResponse;
  try {
    currentDatabaseResponse = dbResponse;
    const summary = buildManagerReportFromDatabase(dbResponse);
    return getDecisionSnapshotFromSummary(summary);
  } catch (error) {
    console.warn("[Hourly history] failed to create decision snapshot", error);
    return null;
  } finally {
    currentDatabaseResponse = previousDb;
  }
}

function storeHourlySnapshotForDbResponse(dbResponse) {
  if (!CONFIG.SIMULATED_API_ENABLED || !dbResponse) return;

  const dateKey = getResponseDateKeyFromDb(dbResponse);
  const hour = getResponseHourFromDb(dbResponse);
  const decision = createDecisionSnapshotForDb(dbResponse);
  const store = getSimulatedHourlyStore();

  if (!store[dateKey]) {
    store[dateKey] = {
      date: dateKey,
      hours: {}
    };
  }

  store[dateKey].hours[String(hour)] = {
    date: dateKey,
    hour,
    savedAt: new Date().toISOString(),
    hasProblem: Boolean(decision && decision.level !== "正常"),
    problemLevel: decision?.level || "正常",
    problemStation: decision?.station || "無",
    problemDirection: decision?.direction || "無需處理",
    decisionLabel: decision?.label || "目前無異常",
    dbResponse: JSON.parse(JSON.stringify(dbResponse))
  };

  saveSimulatedHourlyStore(store);
}

function getHourlySnapshot(dateKey, hour) {
  if (hour === null || hour === undefined || hour === "") return null;
  const key = String(Number(hour));
  return getSimulatedHourlyStore()[dateKey]?.hours?.[key] || null;
}

function getHourlySnapshotsForDate(dateKey) {
  const hours = getSimulatedHourlyStore()[dateKey]?.hours || {};
  return Object.values(hours).sort((a, b) => Number(a.hour) - Number(b.hour));
}

function getProblemHourMapForDate(dateKey) {
  const map = new Map();
  getHourlySnapshotsForDate(dateKey).forEach(snapshot => {
    if (!snapshot.hasProblem) return;
    map.set(Number(snapshot.hour), snapshot);
  });
  return map;
}

function getLatestAvailableHourForDate(dateKey) {
  const hours = getHourlySnapshotsForDate(dateKey).map(snapshot => Number(snapshot.hour));
  if (hours.length) return Math.max(...hours);
  if (dateKey === getActiveApiDateKey()) return getSimulatedApiCurrentHour();
  return 23;
}

function getSimulationDayIndexForDate(dateKey) {
  const startDate = parseDateKey(CONFIG.SIMULATED_API_START_DATE || CONFIG.API_DATE || getTodayKey());
  const targetDate = parseDateKey(dateKey);
  return Math.max(0, Math.round((targetDate.getTime() - startDate.getTime()) / (24 * 60 * 60 * 1000)));
}

function makeSimulatedDbResponseForDateHour(dateKey, hour) {
  const previousUploadIndex = SIMULATED_API_UPLOAD_INDEX;
  const previousDayIndex = SIMULATED_API_DAY_INDEX;

  try {
    const startHour = Number(CONFIG.SIMULATED_API_START_HOUR || 0);
    const stepHours = Number(CONFIG.SIMULATED_API_STEP_HOURS || 1) || 1;
    SIMULATED_API_DAY_INDEX = getSimulationDayIndexForDate(dateKey);
    SIMULATED_API_UPLOAD_INDEX = Math.max(0, Math.round((Number(hour) - startHour) / stepHours));
    return normalizeProjectApiBundleToManagerDb(getProjectSchemaMockBundle());
  } finally {
    SIMULATED_API_UPLOAD_INDEX = previousUploadIndex;
    SIMULATED_API_DAY_INDEX = previousDayIndex;
  }
}

function getOrCreateHourlySnapshot(dateKey, hour) {
  let snapshot = getHourlySnapshot(dateKey, hour);
  if (snapshot) return snapshot;

  if (!CONFIG.SIMULATED_API_ENABLED) return null;

  const activeDate = getActiveApiDateKey();
  const selectedHour = Number(hour);
  const maxSelectableHour = dateKey === activeDate ? getSimulatedApiCurrentHour() : 23;

  if (selectedHour < 0 || selectedHour > maxSelectableHour) return null;

  const generatedDb = makeSimulatedDbResponseForDateHour(dateKey, selectedHour);
  const dbForSnapshot = dateKey < activeDate
    ? actualizeDatabaseResponseFromDb(generatedDb, dateKey)
    : generatedDb;
  storeHourlySnapshotForDbResponse(dbForSnapshot);
  return getHourlySnapshot(dateKey, selectedHour);
}

function generateHourOptionsForSelectedDate() {
  const activeDate = getActiveApiDateKey();
  const selectedDate = selectedReportDate || activeDate;
  const problemMap = getProblemHourMapForDate(selectedDate);
  const latestHour = getLatestAvailableHourForDate(selectedDate);
  const maxHour = selectedDate === activeDate ? getSimulatedApiCurrentHour() : Math.max(23, latestHour);
  const options = [];

  if (selectedDate === activeDate) {
    options.push({
      value: "live",
      label: `最新 ${String(getSimulatedApiCurrentHour()).padStart(2, "0")}:00`,
      problem: false
    });
  }

  // Manager review UX: newest hour first, oldest hour last.
  // Example: if current is 12:00, show 12:00, 11:00, 10:00 ... 00:00.
  for (let hour = maxHour; hour >= 0; hour -= 1) {
    const problem = problemMap.get(hour);
    const problemText = problem ? ` ${problem.problemStation}：${problem.problemDirection}` : "";
    options.push({
      value: String(hour),
      label: `${String(hour).padStart(2, "0")}:00${problemText}`,
      hourLabel: `${String(hour).padStart(2, "0")}:00`,
      problemText: problem ? `${problem.problemStation}：${problem.problemDirection}` : "",
      problem: Boolean(problem),
      problemLevel: problem?.problemLevel || "正常"
    });
  }

  return options;
}

function getSelectedHourSelectValue() {
  return selectedReportHourMode === "live" ? "live" : String(selectedReportHour ?? getLatestAvailableHourForDate(selectedReportDate));
}

function setDefaultTimeSelectionForDate(dateKey) {
  const activeDate = getActiveApiDateKey();
  if (dateKey === activeDate) {
    selectedReportHourMode = "live";
    selectedReportHour = null;
    return;
  }

  selectedReportHourMode = "hour";
  selectedReportHour = getLatestAvailableHourForDate(dateKey);
}

function getTimeReviewModeLabel() {
  if (selectedReportHourMode === "live") return "當前資料";
  return `回顧 ${String(selectedReportHour ?? 0).padStart(2, "0")}:00`;
}

function getSelectedDateMode() {
  const activeDate = getActiveApiDateKey();
  if (selectedReportDate === activeDate) return "active";
  if (getArchivedDatabaseResponse(selectedReportDate)) return "archive";
  return "missing";
}

function getSimulatedApiCurrentHour() {
  const start = Number(CONFIG.SIMULATED_API_START_HOUR || 10);
  const step = Number(CONFIG.SIMULATED_API_STEP_HOURS || 1);
  const maxHour = Number(CONFIG.SIMULATED_API_MAX_HOUR || 23);
  const hour = start + SIMULATED_API_UPLOAD_INDEX * step;
  return Math.max(0, Math.min(maxHour, hour));
}

function getSimulatedGeneratedAt() {
  const hour = getSimulatedApiCurrentHour();
  return `${getActiveApiDateKey()}T${String(hour).padStart(2, "0")}:20:00+08:00`;
}

function getSimulatedScenario(hour, dateKey = getActiveApiDateKey()) {
  const h = Number(hour || 0);
  const dayIndex = getSimulationDayIndexForDate(dateKey);
  const dayProfile = ((dayIndex % 6) + 6) % 6;
  const dateLabel = formatDateLabel(dateKey);

  const stableScenario = {
    name: `${dateLabel} 三站回穩`,
    activeLineId: null,
    note: `${dateLabel} API upload：目前三站回到可接受範圍，診斷區應自動隱藏。`,
    overrides: {}
  };

  // 每一天故意給不同的模擬情境，避免封存後 6/8、6/9、6/10 看起來都一樣。
  // 真正接 DB 後，這裡會由 API 回傳的 station_latest / trend / diagnosis 取代。
  if (dayProfile === 0) {
    if (h <= 10) {
      return {
        name: `${dateLabel} 第二站顏色層噴嘴堵塞風險`,
        activeLineId: "line_2",
        note: `${dateLabel}：第二站品質、稼動率與 Cycle Time 同時變差。`,
        overrides: {
          line_2: {
            state: "warning",
            pressure_bar: 2.52,
            flow_rate_ml_min: 111,
            spray_width_mm: 196,
            temperature_c: 29.1,
            availability_pct: 78.1,
            maintainability_pct: 84.5,
            clog_rate_pct: 14.6,
            quality_score_pct: 89.1,
            utilization_pct: 74.6,
            cycle_time_sec: 52.4,
            componentHealth: { nozzle: "warning", filter_mesh: "warning", spray_width: "out_of_range" }
          }
        }
      };
    }

    if (h === 11) {
      return {
        name: `${dateLabel} 第二站處理後仍需觀察`,
        activeLineId: "line_2",
        note: `${dateLabel}：第二站有改善，但品質仍低於 92%。`,
        overrides: {
          line_2: {
            state: "warning",
            pressure_bar: 2.43,
            flow_rate_ml_min: 116,
            spray_width_mm: 192,
            temperature_c: 28.9,
            availability_pct: 80.4,
            maintainability_pct: 86.8,
            clog_rate_pct: 11.8,
            quality_score_pct: 90.8,
            utilization_pct: 77.8,
            cycle_time_sec: 50.2,
            componentHealth: { nozzle: "warning", filter_mesh: "monitor", spray_width: "out_of_range" }
          }
        }
      };
    }

    if (h === 12 || h === 13) {
      return {
        name: h === 12 ? `${dateLabel} 第三站保護層濾網供漆阻力上升` : `${dateLabel} 第三站保護層惡化`,
        activeLineId: "line_3",
        note: h === 12 ? `${dateLabel}：問題轉移到第三站，決策應改通知第三站負責工程師。` : `${dateLabel}：第三站由警告升級為緊急，決策應升級。`,
        overrides: {
          line_3: {
            state: "warning",
            pressure_bar: h === 12 ? 2.02 : 1.96,
            flow_rate_ml_min: h === 12 ? 110 : 106,
            spray_width_mm: h === 12 ? 186 : 191,
            temperature_c: h === 12 ? 28.5 : 29.2,
            availability_pct: h === 12 ? 78.7 : 75.1,
            maintainability_pct: h === 12 ? 83.2 : 81.2,
            clog_rate_pct: h === 12 ? 12.2 : 15.5,
            quality_score_pct: h === 12 ? 91.1 : 89.5,
            utilization_pct: h === 12 ? 76.5 : 73.9,
            cycle_time_sec: h === 12 ? 51.2 : 53.0,
            componentHealth: { nozzle: h === 12 ? "normal" : "monitor", filter_mesh: "warning", spray_width: h === 12 ? "normal" : "out_of_range" }
          }
        }
      };
    }

    if (h === 14) {
      return {
        name: `${dateLabel} 第一站底色層噴幅偏低`,
        activeLineId: "line_1",
        note: `${dateLabel}：第一站噴幅低於目標，決策應改通知第一站負責工程師。`,
        overrides: {
          line_1: {
            state: "warning",
            pressure_bar: 2.01,
            flow_rate_ml_min: 115,
            spray_width_mm: 171,
            temperature_c: 28.1,
            availability_pct: 79.5,
            maintainability_pct: 86.4,
            clog_rate_pct: 10.5,
            quality_score_pct: 90.6,
            utilization_pct: 77.1,
            cycle_time_sec: 51.0,
            componentHealth: { nozzle: "normal", filter_mesh: "monitor", spray_width: "out_of_range" }
          }
        }
      };
    }

    return stableScenario;
  }

  if (dayProfile === 1) {
    if (h >= 8 && h <= 9) {
      return {
        name: `${dateLabel} 第一站底色層供漆偏低`,
        activeLineId: "line_1",
        note: `${dateLabel}：第一站早班供漆流量偏低，可能影響底色覆蓋。`,
        overrides: {
          line_1: {
            state: "warning",
            pressure_bar: 2.05,
            flow_rate_ml_min: 113,
            spray_width_mm: 174,
            temperature_c: 27.9,
            availability_pct: 81.4,
            maintainability_pct: 87.2,
            clog_rate_pct: 9.8,
            quality_score_pct: 91.2,
            utilization_pct: 78.4,
            cycle_time_sec: 49.9,
            componentHealth: { nozzle: "monitor", filter_mesh: "monitor", spray_width: "out_of_range" }
          }
        }
      };
    }

    if (h >= 17 && h <= 18) {
      return {
        name: `${dateLabel} 第三站保護層 Cycle Time 偏高`,
        activeLineId: "line_3",
        note: `${dateLabel}：第三站傍晚節拍偏慢，但品質尚未明顯掉落。`,
        overrides: {
          line_3: {
            state: "warning",
            pressure_bar: 2.09,
            flow_rate_ml_min: 118,
            spray_width_mm: 188,
            temperature_c: 28.0,
            availability_pct: 80.2,
            maintainability_pct: 86.5,
            clog_rate_pct: 9.1,
            quality_score_pct: 92.1,
            utilization_pct: 76.8,
            cycle_time_sec: 52.7,
            componentHealth: { nozzle: "normal", filter_mesh: "monitor", spray_width: "normal" }
          }
        }
      };
    }

    return stableScenario;
  }

  if (dayProfile === 2) {
    if (h >= 6 && h <= 7) {
      return {
        name: `${dateLabel} 第二站顏色層壓力波動`,
        activeLineId: "line_2",
        note: `${dateLabel}：第二站早班壓力與流量不同步，需檢查供漆與霧化條件。`,
        overrides: {
          line_2: {
            state: "warning",
            pressure_bar: 2.62,
            flow_rate_ml_min: 118,
            spray_width_mm: 191,
            temperature_c: 28.7,
            availability_pct: 81.0,
            maintainability_pct: 87.1,
            clog_rate_pct: 10.4,
            quality_score_pct: 91.0,
            utilization_pct: 78.6,
            cycle_time_sec: 50.6,
            componentHealth: { nozzle: "monitor", filter_mesh: "normal", spray_width: "out_of_range" }
          }
        }
      };
    }

    if (h >= 15 && h <= 16) {
      return {
        name: `${dateLabel} 第一站底色層稼動率下降`,
        activeLineId: "line_1",
        note: `${dateLabel}：第一站下午稼動率下降，可能有等待、短暫停機或清潔。`,
        overrides: {
          line_1: {
            state: "warning",
            pressure_bar: 2.16,
            flow_rate_ml_min: 122,
            spray_width_mm: 181,
            temperature_c: 28.0,
            availability_pct: 77.8,
            maintainability_pct: 86.2,
            clog_rate_pct: 8.9,
            quality_score_pct: 92.7,
            utilization_pct: 73.8,
            cycle_time_sec: 51.6,
            componentHealth: { nozzle: "normal", filter_mesh: "normal", spray_width: "normal" }
          }
        }
      };
    }

    return stableScenario;
  }

  if (dayProfile === 3) {
    if (h >= 13 && h <= 15) {
      return {
        name: `${dateLabel} 第三站保護層噴嘴霧化不穩`,
        activeLineId: "line_3",
        note: `${dateLabel}：第三站午後噴嘴與濾網同時進入監控狀態。`,
        overrides: {
          line_3: {
            state: "warning",
            pressure_bar: 1.99,
            flow_rate_ml_min: 107,
            spray_width_mm: 193,
            temperature_c: 29.4,
            availability_pct: 76.9,
            maintainability_pct: 82.8,
            clog_rate_pct: 13.8,
            quality_score_pct: 90.4,
            utilization_pct: 75.6,
            cycle_time_sec: 52.9,
            componentHealth: { nozzle: "warning", filter_mesh: "warning", spray_width: "out_of_range" }
          }
        }
      };
    }

    return stableScenario;
  }

  if (dayProfile === 4) {
    if (h >= 10 && h <= 11) {
      return {
        name: `${dateLabel} 第二站顏色層色差風險`,
        activeLineId: "line_2",
        note: `${dateLabel}：第二站噴幅與流量偏離，可能造成色差或膜厚不均。`,
        overrides: {
          line_2: {
            state: "warning",
            pressure_bar: 2.38,
            flow_rate_ml_min: 114,
            spray_width_mm: 193,
            temperature_c: 28.6,
            availability_pct: 79.8,
            maintainability_pct: 86.0,
            clog_rate_pct: 12.0,
            quality_score_pct: 90.1,
            utilization_pct: 77.2,
            cycle_time_sec: 50.8,
            componentHealth: { nozzle: "warning", filter_mesh: "monitor", spray_width: "out_of_range" }
          }
        }
      };
    }

    if (h >= 20 && h <= 21) {
      return {
        name: `${dateLabel} 第三站夜間供漆阻力上升`,
        activeLineId: "line_3",
        note: `${dateLabel}：第三站夜間流量下降，需檢查濾網與管路。`,
        overrides: {
          line_3: {
            state: "warning",
            pressure_bar: 2.00,
            flow_rate_ml_min: 109,
            spray_width_mm: 188,
            temperature_c: 28.8,
            availability_pct: 79.2,
            maintainability_pct: 84.4,
            clog_rate_pct: 11.9,
            quality_score_pct: 91.5,
            utilization_pct: 77.9,
            cycle_time_sec: 50.9,
            componentHealth: { nozzle: "normal", filter_mesh: "warning", spray_width: "normal" }
          }
        }
      };
    }

    return stableScenario;
  }

  if (h >= 4 && h <= 5) {
    return {
      name: `${dateLabel} 第一站清晨短暫堵塞`,
      activeLineId: "line_1",
      note: `${dateLabel}：第一站清晨堵塞率短暫上升，後續已回穩。`,
      overrides: {
        line_1: {
          state: "warning",
          pressure_bar: 2.08,
          flow_rate_ml_min: 116,
          spray_width_mm: 173,
          temperature_c: 27.6,
          availability_pct: 80.6,
          maintainability_pct: 87.6,
          clog_rate_pct: 10.8,
          quality_score_pct: 91.6,
          utilization_pct: 78.8,
          cycle_time_sec: 50.1,
          componentHealth: { nozzle: "warning", filter_mesh: "normal", spray_width: "out_of_range" }
        }
      }
    };
  }

  return stableScenario;
}

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
  if (CONFIG.USE_MOCK_DATA || !CONFIG.API_BASE_URL) return getProjectSchemaMockBundle();

  const apiDate = (typeof selectedReportDate !== "undefined" && selectedReportDate)
    ? selectedReportDate
    : getActiveApiDateKey();
  const url = `${String(CONFIG.API_BASE_URL).replace(/\/$/, "")}/api/v1/bundle?date=${encodeURIComponent(apiDate)}`;

  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${response.status}: ${url}`);
    return await response.json();
  } catch (err) {
    console.warn("[fetchProjectSchemaApiBundle] API 呼叫失敗，退回模擬資料：", err);
    return getProjectSchemaMockBundle();
  }
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
let MANAGER_MOCK_SUMMARY = buildManagerReportFromDatabase(currentDatabaseResponse);
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
      else if (archivedKeys.includes(key)) suffix = " 已封存";
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

function buildTopProblemCards(summary) {
  const mainMetrics = summary.mainStationMetrics;
  const mainBaseline = summary.mainStationBaseline;
  const reasons = summary.mainRiskReasons;

  return [
    {
      rank: "1",
      title: `最大風險 1：${summary.mainIssueStation} / ${summary.mainIssueProcess} 風險最高`,
      metric: `風險分數 ${summary.mainStationRiskScore}｜品質分數 ${formatPercent(mainMetrics.quality_score_pct)}｜預測良率 ${formatPercent(summary.predictedOkRate)}`,
      judgement: reasons[0] || `${summary.mainIssueStation} 數據異常，需要工程師確認。`,
      action: `通知 ${summary.responsibleEngineer} 優先處理，檢查壓力、流量、噴幅、噴嘴、濾網與噴塗節拍。`
    },
    {
      rank: "2",
      title: "最大風險 2：堵塞與流量造成噴塗不穩",
      metric: `堵塞率 ${formatPercent(mainMetrics.clog_rate_pct)}｜流量 ${formatNumber(mainMetrics.flow_rate_ml_min)} ml/min｜基準 ${formatNumber(mainBaseline.flow_rate_ml_min)} ml/min`,
      judgement: "堵塞率偏高且流量低於基準，可能造成膜厚不均、色差或局部覆蓋不足。",
      action: `由 ${summary.responsibleEngineer} 確認噴嘴、濾網、供漆流量與塗料壓力。`
    },
    {
      rank: "3",
      title: "最大風險 3：噴幅與節拍偏離基準",
      metric: `噴幅 ${mainMetrics.spray_width_mm} mm｜目標 ${mainMetrics.target_min_mm}-${mainMetrics.target_max_mm} mm｜Cycle Time ${mainMetrics.cycle_time_sec.toFixed(1)} sec`,
      judgement: "噴幅超出目標範圍且 Cycle Time 變慢，會讓品質風險與產能風險同時上升。",
      action: `下一次資料更新前確認 ${summary.mainIssueStation} 噴幅、扇形氣壓、Robot path 與等待時間。`
    }
  ];
}

function buildCategoryContent(summary) {
  const level = getOperationLevel(summary);
  const mainMetrics = summary.mainStationMetrics;
  const mainBaseline = summary.mainStationBaseline;
  const qualityMode = getCurrentQualityScoreMode();

  return {
    monitor: {
      title: "狀態實時監控表",
      status: level,
      conclusion: {
        meta: `${level}：目前即時資料顯示 ${summary.mainIssueStation} / ${summary.mainIssueProcess} 風險最高，風險分數 ${summary.mainStationRiskScore}。`,
        reason: `狀態表由 stationTelemetry / component_metrics 欄位產生，包含壓力、流量、噴幅、堵塞率、品質分數、稼動率與 Cycle Time。`,
        action: `先通知 ${summary.responsibleEngineer} 處理 ${summary.mainIssueStation}，並用下一次 DB 更新確認指標是否回穩。`
      },
      situation: "這一頁是主管主畫面：把三站即時資料整理成一張監控表。主管不需要先看六個分類，而是先看哪一站異常、異常欄位是什麼、工程師是誰。",
      actionText: `目前 P1 是 ${summary.responsibleEngineer}。驗收重點是 ${summary.mainIssueStation} 的風險分數下降、堵塞率降低、噴幅回到目標範圍，以及預測 NG 不再增加。`,
      evidence: [
        {
          label: "最高風險站別",
          answer: `${summary.mainIssueStation} / ${summary.mainIssueProcess}`,
          text: `風險分數 ${summary.mainStationRiskScore}，對應設備 ${summary.mainIssueRobot}，站別 ${summary.responsibleEngineer}。`,
          status: "stationTelemetry + responsibility"
        },
        {
          label: "目前品質",
          answer: formatPercent(summary.predictedOkRate),
          text: `${qualityMode.isPredicted ? "當天品質尚未完成 QC，目前為預測品質分數；隔天 QC 後才會轉為實際品質。" : "選定日期已完成 QC，目前顯示實際品質分數。"}上週實際良率 ${formatPercent(summary.lastWeekActualOkRate)}。`,
          status: qualityMode.sourceStatus
        },
        {
          label: "產出差異",
          answer: `-${formatNumber(summary.lostProductionPcs)} pcs`,
          text: `目前產出 ${formatNumber(summary.producedPcs)} pcs，上週同期間 ${formatNumber(summary.lastWeekProducedPcs)} pcs。`,
          status: "productionKpi"
        },
        {
          label: "資料模式",
          answer: "Mock DB",
          text: `目前使用 mock web service 格式，未來可把 CONFIG.DB_API_URL 換成實際 API。`,
          status: "尚未真連線"
        }
      ]
    },

    decision: {
      title: "現在要不要處理",
      status: level,
      conclusion: {
        meta: `答案：要處理。${summary.mainIssueStation} / ${summary.mainIssueProcess} 是目前風險最高站別，風險分數 ${summary.mainStationRiskScore}。`,
        reason: `資料來源指出 ${summary.mainIssueStation} 品質分數 ${formatPercent(mainMetrics.quality_score_pct)}、堵塞率 ${formatPercent(mainMetrics.clog_rate_pct)}、稼動率 ${formatPercent(mainMetrics.utilization_pct)}，且噴幅 ${mainMetrics.spray_width_mm} mm 已超出目標範圍。`,
        action: `通知 ${summary.responsibleEngineer} 優先處理，不建議等明天 QC 完成才處理。`
      },
      situation: `這一頁是把 mock database / web service 回傳的三站即時資料轉成主管決策。系統比較第一站、第二站、第三站後，判斷 ${summary.mainIssueStation} / ${summary.mainIssueProcess} 的風險最高。`,
      actionText: `今天先通知 ${summary.responsibleEngineer} 處理 ${summary.mainIssueStation}，其他站別負責工程師同步確認前後段是否受到影響。`,
      evidence: [
        {
          label: "決策",
          answer: level === "正常" ? "觀察" : "要處理",
          text: `${summary.mainIssueStation} 風險分數 ${summary.mainStationRiskScore}，高於其他站別。`,
          status: "由 stationTelemetry 計算"
        },
        {
          label: "問題站別",
          answer: `${summary.mainIssueStation} / ${summary.mainIssueProcess}`,
          text: `對應設備：${summary.mainIssueRobot}；對應工程師：${summary.responsibleEngineer}。`,
          status: "由 stationResponsibility 對應"
        },
        {
          label: "主要異常",
          answer: `堵塞率 ${formatPercent(mainMetrics.clog_rate_pct)}`,
          text: summary.mainRiskReasons.slice(0, 2).join(" "),
          status: "壓力 / 流量 / 噴幅 / 堵塞率"
        },
        {
          label: "品質狀態",
          answer: "待 QC / 預測",
          text: `當天品質分數為模型預測 ${formatPercent(summary.predictedOkRate)}，明天 QC 後再驗證。`,
          status: "prediction + QC delay"
        }
      ]
    },

    gap: {
      title: "差多少",
      status: level,
      conclusion: {
        meta: `本週預估效益 ${formatPercent(summary.estimatedThisWeekEfficiency)}，比上週實際 ${formatDeltaPercent(summary.efficiencyChange)}。`,
        reason: `${summary.mainIssueStation} 稼動率比基準低 ${Math.abs(mainMetrics.utilization_pct - mainBaseline.utilization_pct).toFixed(1)} points，Cycle Time 比基準慢 ${(mainMetrics.cycle_time_sec - mainBaseline.cycle_time_sec).toFixed(1)} 秒。`,
        action: "先看差距最大的站別，不要平均看三站，否則會把第二站問題稀釋掉。"
      },
      situation: "這裡顯示的是 database / web service 資料轉換後的差異，不是人工填寫的結論。",
      actionText: `差距主要集中在 ${summary.mainIssueStation}，下一次更新要看稼動率、Cycle Time、堵塞率、噴幅是否回到基準。`,
      cards: [
        { label: "本週效益差異", value: formatDeltaPercent(summary.efficiencyChange), tone: "danger", note: `本週預估 ${formatPercent(summary.estimatedThisWeekEfficiency)} vs 上週實際 ${formatPercent(summary.lastWeekActualEfficiency)}` },
        { label: "今日 vs 昨日", value: formatDeltaPercent(summary.todayVsYesterdayChange), tone: "danger", note: `今日預估 ${formatPercent(summary.todayEstimatedEfficiency)} vs 昨日實際 ${formatPercent(summary.yesterdayActualEfficiency)}` },
        { label: "主站稼動差異", value: `${formatDeltaPercent(mainMetrics.utilization_pct - mainBaseline.utilization_pct)}`, tone: "warning", note: `${summary.mainIssueStation} 現在 ${formatPercent(mainMetrics.utilization_pct)}，基準 ${formatPercent(mainBaseline.utilization_pct)}` },
        { label: "Cycle Time 差異", value: `+${(mainMetrics.cycle_time_sec - mainBaseline.cycle_time_sec).toFixed(1)} sec`, tone: "warning", note: `${summary.mainIssueStation} 現在 ${mainMetrics.cycle_time_sec.toFixed(1)} sec，基準 ${mainBaseline.cycle_time_sec.toFixed(1)} sec` }
      ]
    },

    cause: {
      title: "為什麼變差",
      status: level,
      conclusion: {
        meta: `主要原因集中在 ${summary.mainIssueStation} / ${summary.mainIssueProcess}。`,
        reason: summary.mainRiskReasons.join(" "),
        action: `先由 ${summary.responsibleEngineer} 查 ${summary.mainIssueStation}，不要先分散處理所有站。`
      },
      situation: "原因分析不是寫死文字，而是由每站 pressure、flow rate、spray width、clog rate、quality score、utilization、cycle time 和 baseline 比較後產生。",
      actionText: `優先處理 ${summary.mainIssueStation} 的噴嘴、濾網、供漆流量、噴幅、壓力與節拍。`,
      causes: summary.mainRiskReasons
    },

    impact: {
      title: "損失多少",
      status: level,
      conclusion: {
        meta: `目前預估少產 ${formatNumber(summary.lostProductionPcs)} pcs，預測不良數增加 ${formatNumber(summary.extraPredictedNgPcs)} pcs，停機增加 ${formatNumber(summary.extraDowntimeMinutes)} min。`,
        reason: "這些是由 productionKpi 與 forecastNoAction 推估出的管理風險，不是最終財務損失。",
        action: `${summary.mainIssueStation} 若不改善，未來 7 天可能再少產 ${formatNumber(summary.futureLostPcs)} pcs。`
      },
      situation: "損失區塊要標示為預估 / 預測 / 待驗證，不能說成已發生的實際損失。",
      actionText: "主管應把它當成優先順序判斷依據：先降低預測 NG 與少產風險，再等待 QC 實績驗證。",
      cards: [
        { label: "預估少產風險", value: `-${formatNumber(summary.lostProductionPcs)} pcs`, tone: "danger", note: "currentPeriod.producedPcs vs previousPeriod.producedPcs" },
        { label: "預測 NG 增加風險", value: `+${formatNumber(summary.extraPredictedNgPcs)} pcs`, tone: "danger", note: "currentPeriod.predictedNgPcs vs previousPeriod.actualNgPcs" },
        { label: "停機 / 等待風險", value: `+${formatNumber(summary.extraDowntimeMinutes)} min`, tone: "warning", note: "productionKpi.currentPeriod.estimatedDowntimeMin" },
        { label: "未來 7 天少產風險", value: `-${formatNumber(summary.futureLostPcs)} pcs`, tone: "warning", note: "forecastNoAction.extraLostProductionPcs" },
        { label: "未來 7 天 NG 風險", value: `+${formatNumber(summary.futureExtraNgPcs)} pcs`, tone: "warning", note: "forecastNoAction.extraPredictedNgPcs" },
        { label: "額外成本", value: "待成本資料", tone: "neutral", note: "之後可接成本表自動換算" }
      ]
    },

    action: {
      title: "叫誰處理",
      status: level,
      conclusion: {
        meta: `P1：${summary.responsibleEngineer}。因為 ${summary.mainIssueStation} / ${summary.mainIssueProcess} 是風險最高站別。`,
        reason: "每一站有對應工程師，系統依照 stationResponsibility 與風險分數產生任務分派。",
        action: `先發送通知給 ${summary.responsibleEngineer}，其他站別負責工程師同步確認前後段影響。`
      },
      situation: "這裡不是叫主管自己猜要查哪一站，而是由資料判斷異常站別，再對應該站負責工程師。",
      actionText: "下一次資料更新要用驗收條件確認是否有效：風險分數下降、預測 NG 不再增加、壓力/流量/噴幅回穩。",
      assignments: summary.assignments
    },

    validation: {
      title: "預測可不可信",
      status: Math.abs(summary.predictionValidation.predictionErrorPts) <= 2 ? "正常" : "警告",
      conclusion: {
        meta: `昨日預測良率與今日完成 QC 後實際良率誤差 ${formatDeltaPoints(summary.predictionValidation.predictionErrorPts)}。`,
        reason: `模型輸入來源：${summary.predictionValidation.modelInputSource}；目前預測可信度為 ${summary.predictionValidation.modelTrustLevel}。`,
        action: "若誤差連續超過 2 points，降低預測信任度並檢查資料欄位或模型。"
      },
      situation: "因為品質 QC 延遲 1 天，今天看到的品質是預測值；昨天以前可以用實際 QC 回來驗證模型。",
      actionText: "當天的 NG、品質分數與品質等級都要標示為待 QC / 預測品質，不能當成實際結果；隔天 QC 完成後才可切換為實際品質。",
      validations: [
        { label: "預測良率", predicted: formatPercent(summary.predictionValidation.yesterdayPredictedOkRate), actual: formatPercent(summary.predictionValidation.yesterdayActualOkRate), error: formatDeltaPoints(summary.predictionValidation.predictionErrorPts), result: "良好" },
        { label: "預測不良數", predicted: String(summary.predictionValidation.yesterdayPredictedNgPcs), actual: String(summary.predictionValidation.yesterdayActualNgPcs), error: formatDeltaNumber(summary.predictionValidation.yesterdayActualNgPcs - summary.predictionValidation.yesterdayPredictedNgPcs, " pcs"), result: "可接受" },
        { label: "模型輸入來源", predicted: summary.predictionValidation.modelInputSource, actual: "QC 實績驗證", error: "有對照", result: "可信" },
        { label: "預測可信度", predicted: "-", actual: "-", error: "-", result: summary.predictionValidation.modelTrustLevel }
      ]
    }
  };
}

// ==============================
// Render
// ==============================

function renderManagerHeader() {
  const summary = MANAGER_MOCK_SUMMARY;
  const level = getOperationLevel(summary);
  const selectedQuality = getSelectedQualityInfo(summary);
  const dateOptions = generateDateOptions(14);
  const hourOptions = generateHourOptionsForSelectedDate();
  const selectedHourValue = getSelectedHourSelectValue();
  const header = document.getElementById("managerHeader");

  header.innerHTML = `
    <div class="decision-alert">
      <div class="header-title-row">
        <h1>${escapeHtml(summary.lineName)} 噴塗線主管駕駛艙</h1>
        <span class="header-status-pill ${statusClass(level)}">${escapeHtml(level)}</span>
      </div>
      <p class="decision-line primary">
        ${escapeHtml(level)}：${escapeHtml(summary.mainIssueStation)} / ${escapeHtml(summary.mainIssueProcess)} 風險最高
      </p>
      <p class="decision-line secondary">
        主要依據：風險分數 ${escapeHtml(summary.mainStationRiskScore)}｜堵塞率 ${escapeHtml(formatPercent(summary.mainStationMetrics.clog_rate_pct))}｜噴幅 ${escapeHtml(summary.mainStationMetrics.spray_width_mm)} mm
      </p>
      <p class="decision-line action">
        建議：通知 ${escapeHtml(summary.responsibleEngineer)} 優先處理。資料來源：${escapeHtml(summary.dataSource)}。
      </p>
    </div>

    <div class="overview-card-grid" aria-label="主管總覽摘要">
      <article class="overview-mini-card date-card">
        <label class="overview-label" for="reportDateSelect">資料日期</label>
        <select id="reportDateSelect" class="date-select">
          ${dateOptions.map(option => `
            <option value="${escapeHtml(option.key)}" ${option.key === selectedReportDate ? "selected" : ""}>
              ${escapeHtml(option.label)}
            </option>
          `).join("")}
        </select>
        <div class="overview-note">${escapeHtml(selectedQuality.sourceStatus)}｜${escapeHtml(getSelectedDateMode() === "archive" ? "歷史回顧" : "即時模擬")}</div>
      </article>

      <article class="overview-mini-card time-card">
        <label class="overview-label" for="reportHourDropdownTrigger">資料時間</label>
        <div class="time-review-picker">
          <button
            type="button"
            id="reportHourDropdownTrigger"
            class="time-dropdown-trigger ${hourOptions.find(option => option.value === selectedHourValue)?.problem ? "selected-problem-hour" : ""}"
            aria-haspopup="listbox"
            aria-expanded="false"
          >
            <span>${escapeHtml(hourOptions.find(option => option.value === selectedHourValue)?.label || "選擇時間")}</span>
            <span class="time-dropdown-arrow">⌄</span>
          </button>
          <div class="time-dropdown-menu" id="reportHourDropdownMenu" role="listbox" aria-label="選擇資料時間">
            ${hourOptions.map(option => `
              <button
                type="button"
                class="time-dropdown-option ${option.problem ? `problem-hour-option problem-${option.problemLevel}` : ""} ${option.value === selectedHourValue ? "is-selected" : ""}"
                data-report-hour-option="${escapeHtml(option.value)}"
                role="option"
                aria-selected="${option.value === selectedHourValue ? "true" : "false"}"
              >
                <span class="time-option-hour">${escapeHtml(option.hourLabel || option.label)}</span>
                ${option.problemText ? `<span class="time-option-problem">${escapeHtml(option.problemText)}</span>` : ""}
              </button>
            `).join("")}
          </div>
        </div>
        <select id="reportHourSelect" class="date-select time-select sr-only" aria-hidden="true" tabindex="-1">
          ${hourOptions.map(option => `
            <option value="${escapeHtml(option.value)}" ${option.value === selectedHourValue ? "selected" : ""}>
              ${escapeHtml(option.label)}
            </option>
          `).join("")}
        </select>
        <div class="overview-note">${escapeHtml(getTimeReviewModeLabel())}</div>
      </article>

      <article class="overview-mini-card warning-card">
        <div class="overview-label">本週預估效益</div>
        <div class="overview-value">${escapeHtml(formatPercent(summary.estimatedThisWeekEfficiency))}</div>
        <div class="overview-note">本週模型預估</div>
      </article>

      <article class="overview-mini-card actual-card">
        <div class="overview-label">上週實際效益</div>
        <div class="overview-value">${escapeHtml(formatPercent(summary.lastWeekActualEfficiency))}</div>
        <div class="overview-note">上週 QC 實績</div>
      </article>

      <article class="overview-mini-card danger-card">
        <div class="overview-label">效益差異</div>
        <div class="overview-value">${escapeHtml(formatDeltaPercent(summary.efficiencyChange))}</div>
        <div class="overview-note">預估 vs 實績</div>
      </article>


      <article class="overview-mini-card ${escapeHtml(selectedQuality.gradeClass)}">
        <div class="overview-label">${escapeHtml(selectedQuality.label)}</div>
        <div class="overview-value">${escapeHtml(selectedQuality.value)}</div>
        <div class="overview-note">
          品質等級：${escapeHtml(selectedQuality.grade)}｜${escapeHtml(selectedQuality.sourceStatus)}
        </div>
      </article>
    </div>
  `;
}

function renderSelectedQualityNote() {
  const note = document.getElementById("selectedQualityNote");
  if (!note) return;

  const quality = getSelectedQualityInfo(MANAGER_MOCK_SUMMARY);
  const dateLabel = formatDateLabel(selectedReportDate);

  note.classList.remove("pending-qc", "actual-qc", "quality-good", "quality-warning", "quality-danger");
  note.classList.add(quality.gradeClass);

  note.innerHTML = `
    ${escapeHtml(dateLabel)} 品質等級：
    <strong>${escapeHtml(quality.grade)}</strong>
    <span class="quality-note-sub">
      ｜${escapeHtml(quality.value)}｜${escapeHtml(quality.sourceStatus)}
    </span>
  `;
}

function renderCategoryButtons() {
  const container = document.getElementById("categoryButtons");
  const contentMap = buildCategoryContent(MANAGER_MOCK_SUMMARY);

  container.innerHTML = CATEGORY_LIST.map(category => {
    const categoryState = contentMap[category.key]?.status || "正常";
    const showAlert = shouldShowCategoryAlert(categoryState);
    const alertClass = getCategoryAlertClass(categoryState);

    return `
      <button
        type="button"
        class="category-btn ${activeCategory === category.key ? "active" : ""}"
        data-category="${escapeHtml(category.key)}"
        aria-pressed="${activeCategory === category.key}"
      >
        <span class="category-btn-text">${escapeHtml(category.label)}</span>
        ${showAlert ? `
          <span
            class="category-alert-icon ${alertClass}"
            aria-label="${escapeHtml(categoryState)}"
            title="狀態：${escapeHtml(categoryState)}"
          >!</span>
        ` : ""}
      </button>
    `;
  }).join("");
}

function setActiveCategory(category) {
  if (!CATEGORY_LIST.some(item => item.key === category)) return;
  activeCategory = category;
  renderCategoryButtons();
  renderCategoryContent(category);
}

function renderCategoryContent(category) {
  const contentMap = buildCategoryContent(MANAGER_MOCK_SUMMARY);
  const content = contentMap[category] || contentMap.monitor;
  document.getElementById("activeCategoryTitle").textContent = content.title;

  const container = document.getElementById("categoryContent");

  // Manager UI simplified view:
  // 1) 狀態實時監控表：只保留三站即時監控表
  // 2) 預測驗證：只保留預測 vs QC 實績驗證
  // 不再顯示主管決策來源、情況說明、建議行動等文字卡片。
  if (category === "monitor") {
    container.innerHTML = renderStationMonitorTable(MANAGER_MOCK_SUMMARY);
    return;
  }

  if (category === "validation") {
    container.innerHTML = renderValidationCards(content);
    return;
  }

  container.innerHTML = renderCategoryEvidence(category, content);
}

function renderConclusionCard(content) {
  const level = content.status;

  return `
    <section class="conclusion-card ${statusClass(level)}">
      <div class="conclusion-status">
        <div class="conclusion-decision">${escapeHtml(level)}</div>
        <div class="conclusion-meta">${escapeHtml(content.conclusion.meta)}</div>
      </div>

      <div class="conclusion-copy">
        <div class="conclusion-item">
          <h3>主要原因</h3>
          <p>${escapeHtml(content.conclusion.reason)}</p>
        </div>
        <div class="conclusion-item">
          <h3>建議動作</h3>
          <p>${escapeHtml(content.conclusion.action)}</p>
        </div>
      </div>
    </section>
  `;
}

function renderCategoryEvidence(category, content) {
  if (category === "monitor") {
    return `${renderStationMonitorTable(MANAGER_MOCK_SUMMARY)}${renderTopProblemCards(MANAGER_MOCK_SUMMARY)}${renderDecisionEvidenceCards(content)}`;
  }

  if (category === "decision") {
    return `${renderTopProblemCards(MANAGER_MOCK_SUMMARY)}${renderDecisionEvidenceCards(content)}`;
  }

  if (category === "gap") return renderImpactCards(content, "判斷依據：目前差距");
  if (category === "cause") return renderCauseCards(content);
  if (category === "impact") return renderImpactCards(content, "判斷依據：預估損失風險");
  if (category === "action") return renderProgressCards(content);
  if (category === "validation") return renderValidationCards(content);

  return "";
}


function renderStationMonitorTable(summary) {
  const qualityMode = getCurrentQualityScoreMode();
  const stationItems = [...(summary.stationEvaluations || [])].sort((a, b) => {
    const aNo = Number(String(a.station.lineId || "").replace(/[^0-9]/g, "")) || 0;
    const bNo = Number(String(b.station.lineId || "").replace(/[^0-9]/g, "")) || 0;
    return aNo - bNo;
  });

  return `
    ${renderApiSimulationStatusPanel(summary)}
    <section class="evidence-panel quality-chart-panel">
      <p class="content-section-kicker">Today hourly ${escapeHtml(qualityMode.shortLabel)}</p>
      <h3>今日 24 小時${escapeHtml(qualityMode.scoreLabel)}：三站 XY 圖表</h3>
      <p class="quality-data-note">${escapeHtml(qualityMode.explanation)}品質分數採用「該小時所有 batch 分數平均值」。</p>
      <div class="quality-chart-grid">
        ${stationItems.map(item => renderQualityScoreChartCard(item)).join("")}
      </div>
    </section>
    ${renderRealtimeDiagnosisPanel(summary)}
  `;
}

function getHourlyQualityScoreSeries(lineId) {
  const values = getHourlyValuesFromDb(lineId, "quality_score_pct") || MOCK_QUALITY_SCORE_HOURLY_TODAY[lineId] || [];
  return Array.from({ length: 24 }, (_, hour) => ({
    hour,
    hourLabel: `${String(hour).padStart(2, "0")}:00`,
    qualityScore: Number(values[hour] ?? 0)
  }));
}

function average(values) {
  if (!values.length) return 0;
  return values.reduce((sum, value) => sum + Number(value || 0), 0) / values.length;
}


function getMetricDeltaPct(current, baseline) {
  const base = Number(baseline || 0);
  if (!base) return 0;
  return ((Number(current || 0) - base) / base) * 100;
}

function getHourlyTrendStats(lineId) {
  const series = getStationHourlyDetailSeries(lineId);
  const qualityStats = getMetricStats(series, "quality_score_pct");
  const utilizationStats = getMetricStats(series, "utilization_pct");
  const cycleStats = getMetricStats(series, "cycle_time_sec");
  const firstQuality = Number(series[0]?.quality_score_pct || 0);
  const latestQuality = Number(series[series.length - 1]?.quality_score_pct || 0);
  const qualityDrop = latestQuality - firstQuality;

  return {
    series,
    qualityStats,
    utilizationStats,
    cycleStats,
    qualityDrop
  };
}

function severityRank(level) {
  if (level === "緊急") return 3;
  if (level === "警告") return 2;
  return 1;
}

function buildStationDiagnosis(evaluation) {
  const qualityMode = getCurrentQualityScoreMode();
  const station = evaluation.station;
  const responsibility = evaluation.responsibility;
  const metrics = station.metrics;
  const baseline = station.baseline;
  const component = station.componentHealth || {};
  const trend = getHourlyTrendStats(station.lineId);

  const flowDelta = getMetricDeltaPct(metrics.flow_rate_ml_min, baseline.flow_rate_ml_min);
  const pressureDelta = getMetricDeltaPct(metrics.pressure_bar, baseline.pressure_bar);
  const utilizationGap = metrics.utilization_pct - baseline.utilization_pct;
  const cycleGap = metrics.cycle_time_sec - baseline.cycle_time_sec;
  const sprayOut = metrics.spray_width_mm < metrics.target_min_mm || metrics.spray_width_mm > metrics.target_max_mm;
  const qualityWarning = metrics.quality_score_pct < 92 || trend.qualityStats.latest < 92 || trend.qualityDrop <= -2;
  const highClog = metrics.clog_rate_pct >= 10;
  const flowLow = metrics.flow_rate_ml_min < baseline.flow_rate_ml_min * 0.92;
  const pressureAbnormal = Math.abs(pressureDelta) >= 8;
  const utilizationLow = utilizationGap <= -5;
  const cycleSlow = metrics.cycle_time_sec > baseline.cycle_time_sec * 1.08;

  const issues = [];

  (station.projectDiagnosis || [])
    .filter(item => item.severity && item.severity !== "normal")
    .forEach(item => {
      const level = item.severity === "alarm" ? "緊急" : "警告";
      issues.push({
        level,
        direction: item.stateLabel || "DB 診斷異常",
        evidence: item.evidence || `來源：diagnosis_latest.schema.json，confidence=${item.confidence || 0}`,
        impact: "此問題由 diagnosis_result 與 threshold tables 推論，代表目前站別資料已超出正常判斷規則。",
        action: item.action || `請 ${responsibility.engineerRole} 依診斷類別先確認 ${responsibility.stationName} 的噴嘴、濾網、噴幅、壓力流量與製程條件。`
      });
    });

  if (highClog || component.nozzle !== "normal") {
    issues.push({
      level: highClog && flowLow ? "緊急" : "警告",
      direction: "噴嘴可能堵塞 / 霧化不穩",
      evidence: `堵塞率 ${formatPercent(metrics.clog_rate_pct)}；噴嘴狀態 ${component.nozzle || "unknown"}；流量 ${formatNumber(metrics.flow_rate_ml_min)} ml/min，基準 ${formatNumber(baseline.flow_rate_ml_min)} ml/min。`,
      impact: `可能造成霧化不均、膜厚不穩、色差或局部覆蓋不足，進一步拉低${qualityMode.scoreLabel}。`,
      action: `請 ${responsibility.engineerRole} 先檢查 ${responsibility.stationName} 噴嘴是否堵塞、磨耗或噴形異常，必要時清潔或更換。`
    });
  }

  if ((component.filter_mesh && component.filter_mesh !== "normal") || (highClog && flowLow)) {
    issues.push({
      level: highClog && flowLow ? "緊急" : "警告",
      direction: "濾網可能堵塞 / 供漆阻力變大",
      evidence: `濾網狀態 ${component.filter_mesh || "unknown"}；流量偏差 ${flowDelta.toFixed(1)}%；堵塞率 ${formatPercent(metrics.clog_rate_pct)}。`,
      impact: "濾網阻塞會讓供漆流量下降，造成顏色層覆蓋不穩，品質分數與稼動率可能一起下降。",
      action: `檢查 ${responsibility.stationName} 濾網、管路與供漆壓力穩定性，先排除供漆端堵塞。`
    });
  }

  if (sprayOut || component.spray_width === "out_of_range") {
    const side = metrics.spray_width_mm > metrics.target_max_mm ? "偏寬" : "偏窄";
    issues.push({
      level: "緊急",
      direction: `噴幅偏離目標範圍（${side}）`,
      evidence: `目前噴幅 ${metrics.spray_width_mm.toFixed(0)} mm，目標 ${metrics.target_min_mm}-${metrics.target_max_mm} mm；噴幅狀態 ${component.spray_width || "unknown"}。`,
      impact: "噴幅偏離會直接影響顏色均勻性、過噴、邊緣覆蓋與外觀缺陷，是 QC 下降的高關聯原因。",
      action: `立即確認扇形氣壓、噴槍角度、噴槍距離與 Robot path，先把噴幅拉回目標範圍。`
    });
  }

  if (pressureAbnormal || flowLow) {
    const pressureText = pressureDelta >= 0 ? `高於基準 ${Math.abs(pressureDelta).toFixed(1)}%` : `低於基準 ${Math.abs(pressureDelta).toFixed(1)}%`;
    const flowText = flowDelta >= 0 ? `高於基準 ${Math.abs(flowDelta).toFixed(1)}%` : `低於基準 ${Math.abs(flowDelta).toFixed(1)}%`;
    issues.push({
      level: pressureAbnormal && flowLow ? "緊急" : "警告",
      direction: "壓力與流量不匹配",
      evidence: `壓力 ${metrics.pressure_bar.toFixed(2)} bar（${pressureText}）；流量 ${formatNumber(metrics.flow_rate_ml_min)} ml/min（${flowText}）。`,
      impact: "壓力上升但流量下降時，通常代表供漆阻力、堵塞或調壓不穩；會造成噴塗量不穩並影響品質分數。",
      action: "同時查塗料壓力、霧化空氣壓力、扇形氣壓與供漆流量，不要只調單一壓力值。"
    });
  }

  if (qualityWarning) {
    issues.push({
      level: trend.qualityStats.latest < 90 ? "緊急" : "警告",
      direction: `${qualityMode.scoreLabel}正在下降`,
      evidence: `最新${qualityMode.hourlyAverageLabel} ${formatPercent(trend.qualityStats.latest)}；最低 ${formatPercent(trend.qualityStats.min)}；00:00 到 23:00 變化 ${formatDeltaPoints(trend.qualityDrop)}。`,
      impact: qualityMode.isPredicted
        ? "當天品質尚未完成 QC，低於 92% 管理線代表明天 QC 可能出現 NG 增加或缺陷集中在該站相關製程。"
        : "此日期已完成 QC，實際品質分數低於 92% 管理線，代表該小時 batch 的實際品質已經有異常紀錄。",
      action: qualityMode.isPredicted
        ? "先把預測品質下降視為待驗證風險，下一次資料更新看預測品質分數是否停止下滑；隔天 QC 回來後確認缺陷類型。"
        : "回查該小時實際 QC 異常 batch，確認缺陷類型、站別原因與當時處理紀錄。"
    });
  }

  if (utilizationLow || cycleSlow) {
    issues.push({
      level: utilizationLow && cycleSlow ? "警告" : "正常",
      direction: "稼動率下降 / Cycle Time 變慢",
      evidence: `稼動率 ${formatPercent(metrics.utilization_pct)}，基準 ${formatPercent(baseline.utilization_pct)}；Cycle Time ${metrics.cycle_time_sec.toFixed(1)} s，基準 ${baseline.cycle_time_sec.toFixed(1)} s。`,
      impact: "若品質異常同時伴隨節拍變慢，可能代表等待、清槍、重噴、調機或設備狀態不穩。",
      action: "查看該時段是否有停等、清槍、換漆、換濾網、Robot path 等事件，判斷是品質造成產能下降，還是設備造成品質下降。"
    });
  }

  const activeIssues = issues.filter(issue => issue.level !== "正常");
  activeIssues.sort((a, b) => severityRank(b.level) - severityRank(a.level));

  const topIssue = activeIssues[0] || null;
  const decisionLevel = topIssue
    ? topIssue.level === "緊急"
      ? "立即處理"
      : "優先確認"
    : "不顯示";

  return {
    evaluation,
    station,
    responsibility,
    issues: activeIssues,
    topIssue,
    hasProblem: Boolean(topIssue),
    decisionLevel,
    trend,
    evidenceSummary: `${qualityMode.shortLabel} ${formatPercent(metrics.quality_score_pct)}｜堵塞 ${formatPercent(metrics.clog_rate_pct)}｜噴幅 ${metrics.spray_width_mm} mm｜壓力 ${metrics.pressure_bar.toFixed(2)} bar｜流量 ${formatNumber(metrics.flow_rate_ml_min)} ml/min｜稼動 ${formatPercent(metrics.utilization_pct)}｜Cycle ${metrics.cycle_time_sec.toFixed(1)} s`
  };
}

function buildRealtimeDiagnosis(summary) {
  const stationDiagnoses = (summary.stationEvaluations || [])
    .map(buildStationDiagnosis)
    .filter(item => item.hasProblem);

  stationDiagnoses.sort((a, b) => severityRank(b.topIssue.level) - severityRank(a.topIssue.level) || b.evaluation.riskScore - a.evaluation.riskScore);
  const main = stationDiagnoses[0] || null;

  if (!main) {
    return {
      main: null,
      stationDiagnoses: [],
      decision: "無異常",
      decisionText: "目前沒有需要顯示的異常資料。"
    };
  }

  return {
    main,
    stationDiagnoses,
    decision: main.decisionLevel,
    decisionText: main.topIssue.level === "緊急"
      ? `現在先處理 ${main.responsibility.stationName} / ${main.responsibility.layerName}，不要等 QC 完成才處理。`
      : `先請 ${main.responsibility.engineerRole} 確認 ${main.topIssue.direction}，下一次資料更新再決定是否升級。`
  };
}

function renderRealtimeDiagnosisPanel(summary) {
  const diagnosis = buildRealtimeDiagnosis(summary);
  const main = diagnosis.main;

  if (!main) return "";

  return `
    <section class="evidence-panel diagnosis-panel">
      <div class="diagnosis-head">
        <div>
          <p class="content-section-kicker">Realtime diagnosis</p>
          <h3>目前可能發生什麼：由 DB 指標自動判斷</h3>
        </div>
        <span class="diagnosis-decision-pill ${statusClass(main.topIssue.level)}">${escapeHtml(diagnosis.decision)}</span>
      </div>

      <div class="diagnosis-main-card ${statusClass(main.topIssue.level)}">
        <div>
          <div class="diagnosis-label">最可能問題方向</div>
          <h4>${escapeHtml(main.responsibility.stationName)} / ${escapeHtml(main.responsibility.layerName)}：${escapeHtml(main.topIssue.direction)}</h4>
          <p>${escapeHtml(main.topIssue.impact)}</p>
        </div>
        <div class="diagnosis-main-evidence">
          <strong>資料證據</strong>
          <span>${escapeHtml(main.topIssue.evidence)}</span>
        </div>
      </div>

      <div class="diagnosis-grid">
        ${diagnosis.stationDiagnoses.map(diagnosisItem => renderStationDiagnosisCard(diagnosisItem)).join("")}
      </div>

    </section>
  `;
}

function renderStationDiagnosisCard(diagnosisItem) {
  if (!diagnosisItem || !diagnosisItem.topIssue) return "";

  const issue = diagnosisItem.topIssue;
  const visibleIssues = diagnosisItem.issues.slice(0, 3);

  return `
    <article class="diagnosis-card ${statusClass(issue.level)}">
      <div class="diagnosis-card-head">
        <div>
          <span>${escapeHtml(diagnosisItem.responsibility.stationName)}｜${escapeHtml(diagnosisItem.responsibility.layerName)}</span>
          <h4>${escapeHtml(issue.direction)}</h4>
        </div>
        <span class="table-status ${statusClass(issue.level)}">${escapeHtml(issue.level)}</span>
      </div>
      <p class="diagnosis-evidence-line">${escapeHtml(diagnosisItem.evidenceSummary)}</p>
      <ul>
        ${visibleIssues.map(item => `
          <li>
            <strong>${escapeHtml(item.direction)}</strong>
            <span>${escapeHtml(item.evidence)}</span>
          </li>
        `).join("")}
      </ul>
      <div class="diagnosis-action-box">
        <strong>建議決策</strong>
        <span>${escapeHtml(issue.action)}</span>
      </div>
    </article>
  `;
}


function renderTimeSegmentLegend() {
  const segment = getTimeSegmentSummaryText();

  return `
    <span class="time-segment-chip past">${escapeHtml(segment.pastText)}</span>
    <span class="time-segment-chip current">${escapeHtml(segment.currentText)}</span>
    <span class="time-segment-chip future">${escapeHtml(segment.futureText)}</span>
  `;
}

function renderQualityScoreChartCard(item) {
  const qualityMode = getCurrentQualityScoreMode();
  const station = item.station;
  const responsibility = item.responsibility;
  const series = getHourlyQualityScoreSeries(station.lineId);
  const currentHour = getCurrentDataHour();
  const currentAndPastValues = series
    .filter(row => Number(row.hour) <= currentHour)
    .map(row => row.qualityScore)
    .filter(value => value > 0);
  const currentRow = series.find(row => Number(row.hour) === currentHour) || series[Math.min(currentHour, series.length - 1)];
  const latest = Number(currentRow?.qualityScore || currentAndPastValues[currentAndPastValues.length - 1] || 0);
  const minValue = currentAndPastValues.length ? Math.min(...currentAndPastValues) : latest;
  const avgValue = average(currentAndPastValues.length ? currentAndPastValues : [latest]);
  const level = latest < 90 ? "緊急" : latest < 92 ? "警告" : "正常";

  return `
    <button
      type="button"
      class="quality-chart-card ${statusClass(level)}"
      data-detail-line-id="${escapeHtml(station.lineId)}"
      aria-label="開啟 ${escapeHtml(responsibility.stationName)} ${escapeHtml(responsibility.layerName)} 詳細資料"
    >
      <div class="quality-chart-head">
        <div>
          <p class="quality-chart-kicker">${escapeHtml(responsibility.stationName)}｜${escapeHtml(responsibility.layerName)}</p>
          <h4>${escapeHtml(responsibility.machineName)}</h4>
        </div>
        <span class="table-status ${statusClass(level)}">${escapeHtml(level)}</span>
      </div>

      <div class="quality-chart-kpi-row">
        <div><span>${escapeHtml(qualityMode.isPredicted ? "最新預測平均" : "最新實際平均")}</span><strong>${escapeHtml(formatPercent(latest))}</strong></div>
        <div><span>最低小時平均</span><strong>${escapeHtml(formatPercent(minValue))}</strong></div>
        <div><span>已發生小時平均</span><strong>${escapeHtml(formatPercent(avgValue))}</strong></div>
      </div>

      ${renderQualityScoreSvg(series)}

      <div class="quality-chart-foot">
        ${renderTimeSegmentLegend()}
        <span>Y 軸：${escapeHtml(qualityMode.axisLabel)}</span>
        <span>${escapeHtml(qualityMode.batchAverageNote)}</span>
        <span>管理線：92%</span>
      </div>

      <div class="quality-card-open-hint">點開查看 QC、稼動率與 Cycle Time 詳細圖表</div>
    </button>
  `;
}

function renderQualityScoreSvg(series) {
  const width = 720;
  const height = 240;
  const left = 54;
  const right = 20;
  const top = 22;
  const bottom = 38;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const yMin = 84;
  const yMax = 96;
  const currentHour = getCurrentDataHour();
  const halfStep = plotWidth / 23 / 2;

  const xForHour = hour => left + (Number(hour || 0) / 23) * plotWidth;
  const yForValue = value => top + ((yMax - Number(value || 0)) / (yMax - yMin)) * plotHeight;

  const metricKey = "qualityScore";
  const { pastRows, futureRows, currentRow } = splitSeriesByCurrentHour(series);
  const allPoints = makeSvgPoints(series, xForHour, yForValue, metricKey);
  const pastPoints = makeSvgPoints(pastRows, xForHour, yForValue, metricKey);
  const futurePoints = makeSvgPoints(futureRows, xForHour, yForValue, metricKey);
  const areaPoints = `${left},${top + plotHeight} ${allPoints} ${left + plotWidth},${top + plotHeight}`;
  const thresholdY = yForValue(92);
  const lastPoint = currentRow || series[series.length - 1];
  const lastX = xForHour(lastPoint.hour);
  const lastY = yForValue(lastPoint.qualityScore);
  const currentX = xForHour(currentHour);
  const currentBandX = Math.max(left, currentX - halfStep);
  const currentBandWidth = Math.min(left + plotWidth, currentX + halfStep) - currentBandX;
  const yTicks = [96, 94, 92, 90, 88, 86, 84];
  const xTicks = Array.from(new Set([0, 4, 8, currentHour, 12, 16, 20, 23]))
    .filter(hour => hour >= 0 && hour <= 23)
    .sort((a, b) => a - b);

  return `
    <div class="quality-svg-wrap" aria-label="每小時品質分數折線圖">
      <svg viewBox="0 0 ${width} ${height}" role="img">
        <rect x="0" y="0" width="${width}" height="${height}" rx="16" class="chart-bg"></rect>
        <rect x="${left}" y="${top}" width="${Math.max(0, currentBandX - left).toFixed(1)}" height="${plotHeight}" class="chart-zone-past"></rect>
        <rect x="${currentBandX.toFixed(1)}" y="${top}" width="${currentBandWidth.toFixed(1)}" height="${plotHeight}" class="chart-zone-current"></rect>
        <rect x="${(currentX + halfStep).toFixed(1)}" y="${top}" width="${Math.max(0, left + plotWidth - (currentX + halfStep)).toFixed(1)}" height="${plotHeight}" class="chart-zone-future"></rect>

        ${yTicks.map(value => `
          <line x1="${left}" y1="${yForValue(value).toFixed(1)}" x2="${left + plotWidth}" y2="${yForValue(value).toFixed(1)}" class="chart-grid-line"></line>
          <text x="${left - 12}" y="${(yForValue(value) + 4).toFixed(1)}" text-anchor="end" class="chart-axis-label">${value}%</text>
        `).join("")}

        ${xTicks.map(hour => `
          <text x="${xForHour(hour).toFixed(1)}" y="${height - 12}" text-anchor="middle" class="chart-axis-label ${hour === currentHour ? "chart-current-axis-label" : ""}">${String(hour).padStart(2, "0")}</text>
        `).join("")}

        <line x1="${left}" y1="${thresholdY.toFixed(1)}" x2="${left + plotWidth}" y2="${thresholdY.toFixed(1)}" class="chart-threshold-line"></line>
        <text x="${left + plotWidth - 4}" y="${(thresholdY - 6).toFixed(1)}" text-anchor="end" class="chart-threshold-label">標準線 92%</text>

        <polygon points="${areaPoints}" class="chart-area"></polygon>
        ${pastPoints ? `<polyline points="${pastPoints}" class="chart-line-past"></polyline>` : ""}
        ${futurePoints ? `<polyline points="${futurePoints}" class="chart-line-future"></polyline>` : ""}
        <line x1="${currentX.toFixed(1)}" y1="${top}" x2="${currentX.toFixed(1)}" y2="${top + plotHeight}" class="chart-current-line"></line>
        <text x="${(currentX + 5).toFixed(1)}" y="${top + 14}" class="chart-current-label">Current ${String(currentHour).padStart(2, "0")}:00</text>

        <circle cx="${lastX.toFixed(1)}" cy="${lastY.toFixed(1)}" r="6" class="chart-current-point"></circle>
        <text x="${(lastX - 8).toFixed(1)}" y="${(lastY - 10).toFixed(1)}" text-anchor="end" class="chart-last-label">${lastPoint.qualityScore.toFixed(1)}%</text>
        ${renderSvgHoverPoints({
          series,
          xForHour,
          yForValue,
          metricKey,
          valueFormatter: value => `${value.toFixed(1)}%`,
          plotTop: top,
          plotBottom: top + plotHeight,
          plotLeft: left,
          plotRight: left + plotWidth
        })}
      </svg>
    </div>
  `;
}

function getStationEvaluationByLineId(lineId) {
  return (MANAGER_MOCK_SUMMARY.stationEvaluations || []).find(item => item.station.lineId === lineId) || null;
}

function getStationHourlyDetailSeries(lineId) {
  const detail = MOCK_STATION_DETAIL_HOURLY_TODAY[lineId] || {};
  const fallbackQuality = MOCK_QUALITY_SCORE_HOURLY_TODAY[lineId] || [];
  const apiQuality = getHourlyValuesFromDb(lineId, "quality_score_pct");
  const apiUtilization = getHourlyValuesFromDb(lineId, "utilization_pct");
  const apiCycle = getHourlyValuesFromDb(lineId, "cycle_time_sec");

  return Array.from({ length: 24 }, (_, hour) => ({
    hour,
    hourLabel: `${String(hour).padStart(2, "0")}:00`,
    quality_score_pct: Number((apiQuality || detail.quality_score_pct || fallbackQuality)[hour] ?? 0),
    utilization_pct: Number((apiUtilization || detail.utilization_pct || [])[hour] ?? 0),
    cycle_time_sec: Number((apiCycle || detail.cycle_time_sec || [])[hour] ?? 0)
  }));
}

function getMetricStats(series, key) {
  const currentHour = getCurrentDataHour();
  const values = series
    .filter(row => Number(row.hour) <= currentHour)
    .map(row => Number(row[key] || 0))
    .filter(value => value > 0);
  const currentRow = series.find(row => Number(row.hour) === currentHour) || series[Math.min(currentHour, series.length - 1)];
  const latest = Number(currentRow?.[key] || values[values.length - 1] || 0);
  const safeValues = values.length ? values : [latest].filter(value => value > 0);
  return {
    latest,
    min: safeValues.length ? Math.min(...safeValues) : 0,
    max: safeValues.length ? Math.max(...safeValues) : 0,
    avg: average(safeValues)
  };
}


function renderSvgHoverPoints(options) {
  const {
    series,
    xForHour,
    yForValue,
    metricKey,
    valueFormatter,
    plotTop,
    plotBottom,
    plotLeft,
    plotRight
  } = options;

  const tooltipWidth = 136;
  const tooltipHeight = 46;

  return series.map(row => {
    const x = xForHour(row.hour);
    const y = yForValue(row[metricKey]);
    const valueText = valueFormatter(Number(row[metricKey] || 0));
    const timeText = row.hourLabel || `${String(row.hour).padStart(2, "0")}:00`;
    const segment = getTimeSegment(row.hour);
    const preferLeft = x > plotLeft + (plotRight - plotLeft) * 0.72;
    const tooltipX = preferLeft ? x - tooltipWidth - 12 : x + 12;
    const tooltipY = Math.max(6, Math.min(plotBottom - tooltipHeight - 6, y - tooltipHeight - 10));
    const textX = tooltipX + 10;

    return `
      <g class="chart-hover-point" tabindex="0" aria-label="${escapeHtml(timeText)}，${escapeHtml(valueText)}，${escapeHtml(segment.label)}">
        <line x1="${x.toFixed(1)}" y1="${plotTop}" x2="${x.toFixed(1)}" y2="${plotBottom}" class="chart-hover-guide"></line>
        <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="15" class="chart-hover-hit"></circle>
        <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="5" class="chart-hover-dot ${escapeHtml(segment.key)}"></circle>
        <rect x="${tooltipX.toFixed(1)}" y="${tooltipY.toFixed(1)}" width="${tooltipWidth}" height="${tooltipHeight}" rx="9" class="chart-hover-tooltip-bg"></rect>
        <text x="${textX.toFixed(1)}" y="${(tooltipY + 13).toFixed(1)}" class="chart-hover-tooltip-text">${escapeHtml(timeText)}｜${escapeHtml(segment.key.toUpperCase())}</text>
        <text x="${textX.toFixed(1)}" y="${(tooltipY + 28).toFixed(1)}" class="chart-hover-tooltip-value">${escapeHtml(valueText)}</text>
        <text x="${textX.toFixed(1)}" y="${(tooltipY + 40).toFixed(1)}" class="chart-hover-tooltip-segment">${escapeHtml(segment.label)}</text>
      </g>
    `;
  }).join("");
}

function formatMetricValue(value, unit, digits = 1) {
  const number = Number(value || 0).toFixed(digits);
  return unit === "%" ? `${number}%` : `${number} ${unit}`;
}

function setStationDetailOpen(open, lineId = selectedDetailLineId) {
  isStationDetailOpen = Boolean(open);
  selectedDetailLineId = isStationDetailOpen ? lineId : "";

  const panel = document.getElementById("stationDetailPanel");
  const overlay = document.getElementById("stationDetailOverlay");

  if (panel) {
    if (isStationDetailOpen) {
      panel.innerHTML = renderStationDetailPanel(selectedDetailLineId);
    }

    panel.classList.toggle("open", isStationDetailOpen);
    panel.setAttribute("aria-hidden", String(!isStationDetailOpen));
  }

  if (overlay) {
    overlay.classList.toggle("open", isStationDetailOpen);
  }

  document.body.classList.toggle("detail-open", isStationDetailOpen);
}

function renderStationDetailPanel(lineId) {
  const qualityMode = getCurrentQualityScoreMode();
  const evaluation = getStationEvaluationByLineId(lineId);

  if (!evaluation) {
    return `
      <div class="station-detail-header">
        <div>
          <p class="content-section-kicker">Station detail</p>
          <h3>找不到站別資料</h3>
        </div>
        <button type="button" class="station-detail-close-btn" id="stationDetailCloseBtn">關閉</button>
      </div>
    `;
  }

  const station = evaluation.station;
  const responsibility = evaluation.responsibility;
  const series = getStationHourlyDetailSeries(lineId);
  const qualityStats = getMetricStats(series, "quality_score_pct");
  const utilizationStats = getMetricStats(series, "utilization_pct");
  const cycleStats = getMetricStats(series, "cycle_time_sec");

  return `
    <div class="station-detail-header">
      <div>
        <p class="content-section-kicker">Station detail / today 24 hours</p>
        <h3>${escapeHtml(responsibility.stationName)}｜${escapeHtml(responsibility.layerName)} 詳細資料</h3>
        <p>
          ${escapeHtml(responsibility.machineName)}｜負責：${escapeHtml(responsibility.engineerRole)}｜
          目前風險分數 ${escapeHtml(evaluation.riskScore)}
        </p>
      </div>
      <button type="button" class="station-detail-close-btn" id="stationDetailCloseBtn">關閉</button>
    </div>

    <div class="station-detail-summary-grid">
      <div><span>${escapeHtml(qualityMode.hourlyAverageLabel)}</span><strong>${escapeHtml(formatMetricValue(qualityStats.latest, "%"))}</strong></div>
      <div><span>稼動率最新值</span><strong>${escapeHtml(formatMetricValue(utilizationStats.latest, "%"))}</strong></div>
      <div><span>Cycle Time 最新值</span><strong>${escapeHtml(formatMetricValue(cycleStats.latest, "s"))}</strong></div>
      <div><span>資料時間</span><strong>${escapeHtml(getTimeSegmentSummaryText().currentText)}</strong></div>
    </div>

    <div class="station-detail-chart-stack">
      ${renderMetricDetailChart({
        title: qualityMode.scoreLabel,
        leftLabel: qualityMode.scoreLabel,
        series,
        metricKey: "quality_score_pct",
        unit: "%",
        yMin: 84,
        yMax: 96,
        standardValue: 92,
        standardLabel: "標準線 92%",
        stats: qualityStats,
        lowerIsWorse: true
      })}

      ${renderMetricDetailChart({
        title: "稼動率",
        leftLabel: "稼動率",
        series,
        metricKey: "utilization_pct",
        unit: "%",
        yMin: 68,
        yMax: 90,
        standardValue: station.baseline.utilization_pct,
        standardLabel: `基準 ${station.baseline.utilization_pct.toFixed(1)}%`,
        stats: utilizationStats,
        lowerIsWorse: true
      })}

      ${renderMetricDetailChart({
        title: "Cycle Time",
        leftLabel: "Cycle-Time",
        series,
        metricKey: "cycle_time_sec",
        unit: "s",
        yMin: 44,
        yMax: 56,
        standardValue: station.baseline.cycle_time_sec,
        standardLabel: `基準 ${station.baseline.cycle_time_sec.toFixed(1)}s`,
        stats: cycleStats,
        lowerIsWorse: false
      })}
    </div>
  `;
}

function renderMetricDetailChart(config) {
  return `
    <article class="station-detail-chart-row">
      <div class="station-detail-chart-label">
        <strong>${escapeHtml(config.leftLabel)}</strong>
        <span>${escapeHtml(config.title)}</span>
      </div>
      <div class="station-detail-chart-card">
        <div class="station-detail-chart-head">
          <h4>${escapeHtml(config.title)}</h4>
          <div>
            <span>最新 ${escapeHtml(formatMetricValue(config.stats.latest, config.unit))}</span>
            <span>平均 ${escapeHtml(formatMetricValue(config.stats.avg, config.unit))}</span>
            <span>${escapeHtml(config.lowerIsWorse ? "低於標準為異常" : "高於基準為異常")}</span>
            ${renderTimeSegmentLegend()}
          </div>
        </div>
        ${renderMetricDetailSvg(config)}
      </div>
    </article>
  `;
}

function renderMetricDetailSvg(config) {
  const width = 980;
  const height = 220;
  const left = 62;
  const right = 26;
  const top = 22;
  const bottom = 38;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const yMin = Number(config.yMin);
  const yMax = Number(config.yMax);
  const currentHour = getCurrentDataHour();
  const halfStep = plotWidth / 23 / 2;

  const xForHour = hour => left + (Number(hour || 0) / 23) * plotWidth;
  const yForValueRaw = value => top + ((yMax - Number(value || 0)) / (yMax - yMin)) * plotHeight;
  const clampY = value => Math.max(top, Math.min(top + plotHeight, yForValueRaw(value)));
  const yForValue = value => clampY(value);
  const { pastRows, futureRows, currentRow } = splitSeriesByCurrentHour(config.series);
  const allPoints = makeSvgPoints(config.series, xForHour, yForValue, config.metricKey);
  const pastPoints = makeSvgPoints(pastRows, xForHour, yForValue, config.metricKey);
  const futurePoints = makeSvgPoints(futureRows, xForHour, yForValue, config.metricKey);
  const areaPoints = `${left},${top + plotHeight} ${allPoints} ${left + plotWidth},${top + plotHeight}`;
  const standardY = clampY(config.standardValue);
  const lastPoint = currentRow || config.series[config.series.length - 1];
  const lastX = xForHour(lastPoint.hour);
  const lastY = clampY(lastPoint[config.metricKey]);
  const currentX = xForHour(currentHour);
  const currentBandX = Math.max(left, currentX - halfStep);
  const currentBandWidth = Math.min(left + plotWidth, currentX + halfStep) - currentBandX;
  const tickStep = (yMax - yMin) / 4;
  const yTicks = Array.from({ length: 5 }, (_, index) => yMax - tickStep * index);
  const xTicks = Array.from(new Set([0, 2, 4, 8, currentHour, 12, 16, 20, 23]))
    .filter(hour => hour >= 0 && hour <= 23)
    .sort((a, b) => a - b);

  return `
    <div class="station-detail-svg-wrap">
      <svg viewBox="0 0 ${width} ${height}" role="img">
        <rect x="0" y="0" width="${width}" height="${height}" rx="16" class="chart-bg"></rect>
        <rect x="${left}" y="${top}" width="${Math.max(0, currentBandX - left).toFixed(1)}" height="${plotHeight}" class="chart-zone-past"></rect>
        <rect x="${currentBandX.toFixed(1)}" y="${top}" width="${currentBandWidth.toFixed(1)}" height="${plotHeight}" class="chart-zone-current"></rect>
        <rect x="${(currentX + halfStep).toFixed(1)}" y="${top}" width="${Math.max(0, left + plotWidth - (currentX + halfStep)).toFixed(1)}" height="${plotHeight}" class="chart-zone-future"></rect>

        ${yTicks.map(value => `
          <line x1="${left}" y1="${clampY(value).toFixed(1)}" x2="${left + plotWidth}" y2="${clampY(value).toFixed(1)}" class="chart-grid-line"></line>
          <text x="${left - 12}" y="${(clampY(value) + 4).toFixed(1)}" text-anchor="end" class="chart-axis-label">${value.toFixed(config.unit === "s" ? 1 : 0)}${config.unit}</text>
        `).join("")}

        ${xTicks.map(hour => `
          <text x="${xForHour(hour).toFixed(1)}" y="${height - 12}" text-anchor="middle" class="chart-axis-label ${hour === currentHour ? "chart-current-axis-label" : ""}">${String(hour).padStart(2, "0")}</text>
        `).join("")}

        <line x1="${left}" y1="${standardY.toFixed(1)}" x2="${left + plotWidth}" y2="${standardY.toFixed(1)}" class="detail-standard-line"></line>
        <text x="${left + 6}" y="${(standardY - 8).toFixed(1)}" class="detail-standard-label">${escapeHtml(config.standardLabel)}</text>

        <polygon points="${areaPoints}" class="detail-chart-area"></polygon>
        ${pastPoints ? `<polyline points="${pastPoints}" class="detail-chart-line-past"></polyline>` : ""}
        ${futurePoints ? `<polyline points="${futurePoints}" class="detail-chart-line-future"></polyline>` : ""}
        <line x1="${currentX.toFixed(1)}" y1="${top}" x2="${currentX.toFixed(1)}" y2="${top + plotHeight}" class="chart-current-line"></line>
        <text x="${(currentX + 5).toFixed(1)}" y="${top + 14}" class="chart-current-label">Current ${String(currentHour).padStart(2, "0")}:00</text>

        <circle cx="${lastX.toFixed(1)}" cy="${lastY.toFixed(1)}" r="6" class="chart-current-point"></circle>
        <text x="${(lastX - 8).toFixed(1)}" y="${(lastY - 10).toFixed(1)}" text-anchor="end" class="chart-last-label">${formatMetricValue(lastPoint[config.metricKey], config.unit)}</text>
        ${renderSvgHoverPoints({
          series: config.series,
          xForHour,
          yForValue,
          metricKey: config.metricKey,
          valueFormatter: value => formatMetricValue(value, config.unit),
          plotTop: top,
          plotBottom: top + plotHeight,
          plotLeft: left,
          plotRight: left + plotWidth
        })}
        <text x="${left + plotWidth}" y="${height - 12}" text-anchor="end" class="chart-axis-label">time</text>
      </svg>
    </div>
  `;
}

function renderTopProblemCards(summary) {
  const cards = buildTopProblemCards(summary);

  return `
    <section class="problem-card-grid" aria-label="Top 3 問題卡">
      ${cards.map(card => `
        <article class="problem-card">
          <div class="problem-rank">Top ${escapeHtml(card.rank)}</div>
          <h3 class="problem-title">${escapeHtml(card.title)}</h3>
          <div class="problem-metric">${escapeHtml(card.metric)}</div>
          <p class="problem-judgement"><strong>判斷：</strong>${escapeHtml(card.judgement)}</p>
          <p class="problem-action"><strong>建議：</strong>${escapeHtml(card.action)}</p>
        </article>
      `).join("")}
    </section>

    <div class="efficiency-note">
      註：目前資料由 MOCK_DATABASE_RESPONSE 模擬 web service 回傳；站別風險由 stationTelemetry 與 baseline 比較產生。
    </div>
  `;
}

function renderDecisionEvidenceCards(content) {
  return `
    <section class="evidence-panel">
      <p class="content-section-kicker">判斷依據</p>
      <h3>判斷依據：主管決策來源</h3>
      <div class="decision-evidence-grid">
        ${content.evidence.map(item => `
          <article class="decision-evidence-card">
            <div class="decision-evidence-label">${escapeHtml(item.label)}</div>
            <div class="decision-evidence-answer ${changeClass(item.answer)}">${escapeHtml(item.answer)}</div>
            <p class="decision-evidence-text">${escapeHtml(item.text)}</p>
            <div class="decision-evidence-status">${escapeHtml(item.status)}</div>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderCauseCards(content) {
  return `
    <section class="evidence-panel">
      <p class="content-section-kicker">判斷依據</p>
      <h3>判斷依據：異常原因 Top ${content.causes.length}</h3>
      <div class="decision-evidence-grid">
        ${content.causes.map((cause, index) => `
          <article class="decision-evidence-card">
            <div class="decision-evidence-label">原因 ${index + 1}</div>
            <div class="decision-evidence-answer negative-text">${escapeHtml(MANAGER_MOCK_SUMMARY.mainIssueStation)}</div>
            <p class="decision-evidence-text">${escapeHtml(cause)}</p>
            <div class="decision-evidence-status">stationTelemetry vs baseline</div>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderImpactCards(content, title = "判斷依據：本週預估損失") {
  return `
    <section class="evidence-panel">
      <p class="content-section-kicker">判斷依據</p>
      <h3>${escapeHtml(title)}</h3>
      <div class="impact-card-grid">
        ${content.cards.map(item => `
          <article class="impact-card ${escapeHtml(item.tone)}">
            <div class="impact-label">${escapeHtml(item.label)}</div>
            <div class="impact-value ${changeClass(item.value)}">${escapeHtml(item.value)}</div>
            <p>${escapeHtml(item.note)}</p>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderProgressCards(content) {
  return `
    <section class="evidence-panel">
      <p class="content-section-kicker">判斷依據</p>
      <h3>判斷依據：站別工程師與驗收條件</h3>
      <div class="progress-card-grid">
        ${content.assignments.map(item => `
          <article class="progress-card">
            <div class="progress-head">
              <span class="assignment-priority">${escapeHtml(item.priority)}</span>
              <span class="assignment-status ${assignmentStatusClass(item.status)}">${escapeHtml(item.status)}</span>
            </div>
            <h4>${escapeHtml(item.owner)}</h4>
            <p><strong>站別：</strong>${escapeHtml(item.station)} / ${escapeHtml(item.processLayer)}</p>
            <p><strong>問題：</strong>${escapeHtml(item.issue)}</p>
            <p><strong>任務：</strong>${escapeHtml(item.task)}</p>
            <p><strong>期限：</strong>${escapeHtml(item.due)}</p>
            <p><strong>驗收：</strong>${escapeHtml(item.acceptance)}</p>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderValidationCards(content) {
  return `
    <section class="evidence-panel">
      <p class="content-section-kicker">判斷依據</p>
      <h3>判斷依據：昨日預測 vs 今日 QC 實績</h3>
      <div class="validation-card-grid">
        ${content.validations.map(item => `
          <article class="validation-card">
            <div class="validation-label">${escapeHtml(item.label)}</div>
            <div class="validation-row"><span>昨日預測 / 輸入</span><strong>${escapeHtml(item.predicted)}</strong></div>
            <div class="validation-row"><span>今日 QC 後實際</span><strong>${escapeHtml(item.actual)}</strong></div>
            <div class="validation-row"><span>誤差 / 狀態</span><strong class="${changeClass(item.error)}">${escapeHtml(item.error)}</strong></div>
            <div class="validation-result">${escapeHtml(item.result)}</div>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderTextSection(title, text) {
  return `
    <section class="content-section text-only-section">
      <p class="content-section-kicker">${escapeHtml(title)}</p>
      <p class="section-text">${escapeHtml(text)}</p>
    </section>
  `;
}


function buildRecommendationAssignmentsFromCurrentData(summary) {
  const qualityMode = getCurrentQualityScoreMode();
  const diagnosis = buildRealtimeDiagnosis(summary);
  const dateLabel = formatDateLabel(getResponseDateKeyFromDb(currentDatabaseResponse || summary.rawDatabaseResponse));
  const hourLabel = `${String(getCurrentDataHour()).padStart(2, "0")}:00`;
  const reviewPrefix = selectedReportHourMode === "live" ? "目前資料" : "回顧資料";

  if (!diagnosis.main || !diagnosis.stationDiagnoses.length) return [];

  return diagnosis.stationDiagnoses.map((diagnosisItem, index) => {
    const issue = diagnosisItem.topIssue;
    const responsibility = diagnosisItem.responsibility;
    const station = diagnosisItem.station;
    const metrics = station.metrics || {};
    const baseline = station.baseline || {};
    const isMain = index === 0;
    const issueList = diagnosisItem.issues.map(item => item.direction).join("、");

    return {
      priority: `P${index + 1}`,
      owner: responsibility.engineerRole,
      station: responsibility.stationName,
      processLayer: responsibility.layerName,
      email: responsibility.engineerEmail,
      lineId: station.lineId,
      level: issue.level,
      issueDirection: issue.direction,
      issue: `${dateLabel} ${hourLabel} ${responsibility.stationName} / ${responsibility.layerName}：${issue.direction}`,
      evidence: issue.evidence,
      impact: issue.impact,
      task: isMain
        ? `${reviewPrefix}顯示 ${issue.direction}。${issue.action}`
        : `${reviewPrefix}顯示同時有異常。同步確認 ${responsibility.stationName}${responsibility.layerName} 的 ${issueList || issue.direction}。`,
      due: selectedReportHourMode === "live" ? "下一次資料更新前" : "回查該小時維修 / 清槍 / 換濾網紀錄後回報",
      status: isMain ? (issue.level === "緊急" ? "立即處理" : "優先確認") : "同步確認",
      acceptance: `${responsibility.stationName}${responsibility.layerName} 在該小時後的${qualityMode.scoreLabel}、堵塞率、噴幅、稼動率與 Cycle Time 沒有再惡化。`,
      riskScore: diagnosisItem.evaluation.riskScore,
      stationMetrics: {
        quality_score_pct: metrics.quality_score_pct,
        clog_rate_pct: metrics.clog_rate_pct,
        spray_width_mm: metrics.spray_width_mm,
        pressure_bar: metrics.pressure_bar,
        flow_rate_ml_min: metrics.flow_rate_ml_min,
        utilization_pct: metrics.utilization_pct,
        cycle_time_sec: metrics.cycle_time_sec,
        baseline_quality_score_pct: baseline.quality_score_pct,
        baseline_flow_rate_ml_min: baseline.flow_rate_ml_min,
        baseline_utilization_pct: baseline.utilization_pct,
        baseline_cycle_time_sec: baseline.cycle_time_sec
      },
      allIssueDirections: issueList
    };
  });
}



function getCurrentBatchInfo(summary, assignment) {
  const db = summary?.rawDatabaseResponse || currentDatabaseResponse || {};
  const production = db.productionKpi || {};
  const currentPeriod = production.currentPeriod || {};
  const candidates = [
    db.currentBatch,
    production.currentBatch,
    currentPeriod.currentBatch,
    currentPeriod.batch,
    currentPeriod
  ].filter(Boolean);

  const found = candidates.find(item =>
    item.batchId || item.batch_id || item.batchNo || item.batch_no || item.lotId || item.lot_no
  ) || {};

  const dateKey = getResponseDateKeyFromDb(db);
  const hour = getCurrentDataHour();
  const lineId = assignment?.lineId || summary?.mainIssueLineId || "line_all";
  const fallbackSeq = Math.floor(Number(hour || 0) / 2) + 1;
  const fallbackBatchId = `B${String(dateKey || getActiveApiDateKey()).replace(/-/g, "")}-${String(fallbackSeq).padStart(3, "0")}-${String(lineId).replace("line_", "S").toUpperCase()}`;
  const history = db.qualityHistory || [];
  const historyBatchSizes = history
    .map(row => Number(row.okPcs || 0) + Number(row.ngPcs || 0))
    .filter(value => value > 0);
  const fallbackBatchSize = currentPeriod.plannedPcs
    ? Math.max(300, Math.round(Number(currentPeriod.plannedPcs) / 18))
    : Math.round(historyBatchSizes.length ? average(historyBatchSizes) : 720);

  const plannedPcs = Number(
    found.plannedPcs ??
    found.planned_pcs ??
    found.batchPcs ??
    found.batch_pcs ??
    found.totalPcs ??
    found.total_pcs ??
    found.qty ??
    found.quantity ??
    fallbackBatchSize
  );

  return {
    batchId: String(found.batchId || found.batch_id || found.batchNo || found.batch_no || found.lotId || found.lot_no || fallbackBatchId),
    workOrderId: String(found.workOrderId || found.work_order_id || found.workOrder || found.wo || `WO-${String(dateKey || getActiveApiDateKey()).replace(/-/g, "")}-${String(fallbackSeq).padStart(3, "0")}`),
    partNo: String(found.partNo || found.part_no || found.partType || found.part_type || "Cover-A"),
    colorCode: String(found.colorCode || found.color_code || found.colorId || found.color_id || "White"),
    recipeId: String(found.recipeId || found.recipe_id || assignment?.stationMetrics?.recipeId || "依當前 API 配方"),
    batchWindow: String(found.batchWindow || found.batch_window || found.timeWindow || found.time_window || `${String(Math.floor(hour / 2) * 2).padStart(2, "0")}:00-${String(Math.min(23, Math.floor(hour / 2) * 2 + 1)).padStart(2, "0")}:59`),
    plannedPcs: Number.isFinite(plannedPcs) && plannedPcs > 0 ? Math.round(plannedPcs) : fallbackBatchSize,
    producedPcsToCurrent: Number(found.producedPcsToCurrent || found.produced_pcs_to_current || found.producedPcs || found.produced_pcs || 0),
    hourlyBatchCount: Number(found.hourlyBatchCount || found.hourly_batch_count || found.batchCountInHour || found.batch_count_in_hour || 1),
    qualityScoreSource: String(found.qualityScoreSource || found.quality_score_source || "hourly_all_batches_average"),
    isPendingQc: found.isPendingQc ?? found.is_pending_qc ?? true,
    source: found.source || "current API / DB batch snapshot"
  };
}

function buildNoActionImpactForecast(assignment, summary) {
  const qualityMode = getCurrentQualityScoreMode();
  const metrics = assignment?.stationMetrics || summary.mainStationMetrics || {};
  const batchInfo = getCurrentBatchInfo(summary, assignment);
  const batchPcs = Math.max(1, Math.round(Number(batchInfo.plannedPcs || 0)));

  const qualityScore = Number(metrics.quality_score_pct ?? summary.predictedOkRate ?? 92);
  const managementOkRate = 92;
  const predictedNgPcs = Math.max(0, Math.round(batchPcs * (100 - qualityScore) / 100));
  const acceptableNgPcs = Math.max(0, Math.round(batchPcs * (100 - managementOkRate) / 100));
  const extraNgPcs = Math.max(0, predictedNgPcs - acceptableNgPcs);

  const util = Number(metrics.utilization_pct ?? summary.utilization ?? 0);
  const baseUtil = Number(metrics.baseline_utilization_pct ?? summary.lastWeekUtilization ?? util);
  const cycle = Number(metrics.cycle_time_sec ?? 0);
  const baseCycle = Number(metrics.baseline_cycle_time_sec ?? cycle);
  const utilizationLossRate = Math.max(0, baseUtil - util) / 100;
  const cycleLossRate = baseCycle > 0 ? Math.max(0, cycle - baseCycle) / baseCycle : 0;
  const productionLossPcs = Math.max(0, Math.round(batchPcs * Math.max(utilizationLossRate, cycleLossRate) * 0.75));
  const totalLossPcs = predictedNgPcs + productionLossPcs;

  const severityScore = extraNgPcs * 1.8 + productionLossPcs + Math.max(0, 92 - qualityScore) * 8;
  const severity = severityScore >= 120 ? "高" : severityScore >= 55 ? "中" : "低";
  const severityText = severity === "高"
    ? `若放著不處理，${batchInfo.batchId} 很可能變成主管需要立即追蹤的品質與產能損失。`
    : severity === "中"
      ? `若下一小時沒有改善，建議主管要求工程師回查 ${batchInfo.batchId} 並留下處理紀錄。`
      : `目前屬於早期風險，但仍要回查 ${batchInfo.batchId} 是否為短暫異常或前兆。`;

  return {
    batchInfo,
    batchId: batchInfo.batchId,
    workOrderId: batchInfo.workOrderId,
    batchPcs,
    predictedNgPcs,
    acceptableNgPcs,
    extraNgPcs,
    productionLossPcs,
    totalLossPcs,
    severity,
    severityText,
    qualityScore,
    qualityMode
  };
}

function renderNoActionImpactAlert(assignment, summary, dateLabel, hourLabel) {
  const impact = buildNoActionImpactForecast(assignment, summary);
  const batch = impact.batchInfo;
  const qualityMode = impact.qualityMode;
  return `
    <div class="future-risk-alert no-action-impact-alert">
      <div class="no-action-impact-head">
        <span>不處理可能後果</span>
        <strong>嚴重性：${escapeHtml(impact.severity)}</strong>
      </div>
      <p>
        ${escapeHtml(dateLabel)} ${escapeHtml(hourLabel)} 目前收到的 batch 是
        <strong>${escapeHtml(batch.batchId)}</strong>（工單 ${escapeHtml(batch.workOrderId)}，${escapeHtml(batch.partNo)} / ${escapeHtml(batch.colorCode)}）。
        若不處理「${escapeHtml(assignment.issueDirection)}」，此 batch 後續可能出現 NG 增加與產出損失。
        ${escapeHtml(qualityMode.isPredicted ? "當天品質分數仍是預測值；隔天 QC 完成後會重新從 DB qc_result 取得實際品質分數，不會沿用這筆預測結果。" : "此日期已完成 QC，品質分數由 DB qc_result 實際資料取得，可作為回顧依據。")}
      </p>
      <div class="no-action-impact-grid">
        <div>
          <span>受影響 batch ID</span>
          <strong>${escapeHtml(batch.batchId)}</strong>
        </div>
        <div>
          <span>該 batch 總數</span>
          <strong>${escapeHtml(formatNumber(impact.batchPcs))} pcs</strong>
        </div>
        <div>
          <span>${escapeHtml(qualityMode.isPredicted ? "預測可能 NG" : "DB 實際品質推估 NG")}</span>
          <strong>${escapeHtml(formatNumber(impact.predictedNgPcs))} pcs</strong>
        </div>
        <div>
          <span>額外 NG</span>
          <strong>+${escapeHtml(formatNumber(impact.extraNgPcs))} pcs</strong>
        </div>
        <div>
          <span>產出損失</span>
          <strong>-${escapeHtml(formatNumber(impact.productionLossPcs))} pcs</strong>
        </div>
        <div>
          <span>${escapeHtml(qualityMode.hourlyAverageLabel)}</span>
          <strong>${escapeHtml(formatPercent(impact.qualityScore))}</strong>
        </div>
      </div>
      <div class="no-action-impact-total">
        <span>主管判斷用總風險</span>
        <strong>${escapeHtml(formatNumber(impact.totalLossPcs))} pcs 可能受影響</strong>
      </div>
      <p class="no-action-impact-note">
        ${escapeHtml(impact.severityText)} 計算基準：目前 API / DB 回傳的 batch ID、batch 數量、品質管理線 92%，以及選定小時「所有 batch 的${qualityMode.scoreLabel}平均值」、稼動率與 Cycle Time。該小時共 ${escapeHtml(formatNumber(batch.hourlyBatchCount || 1))} 個 batch 參與平均。${escapeHtml(qualityMode.isPredicted ? "隔天實際品質會另外查 DB qc_result，不使用當天預測存檔。" : "目前顯示的是 DB qc_result 實際品質，不是當天預測存檔。")}
      </p>
    </div>
  `;
}

function buildRecommendationNoActionBlock(summary) {
  const dateLabel = formatDateLabel(getResponseDateKeyFromDb(currentDatabaseResponse || summary.rawDatabaseResponse));
  const hourLabel = `${String(getCurrentDataHour()).padStart(2, "0")}:00`;
  return `
    <div class="recommendation-summary-row normal-recommendation-row">
      <div>
        <strong>${escapeHtml(dateLabel)} ${escapeHtml(hourLabel)} 目前沒有異常任務分派</strong>
        <p>該小時資料未觸發 warning / emergency。工程師面板不顯示固定分派，避免主管誤判。</p>
      </div>
      <div class="recommendation-summary-count">0 項</div>
    </div>
    <div class="data-reminder">
      若要回查曾經出現問題的小時，請使用上方「資料時間」下拉選單選擇淺紅閃爍的小時。
    </div>
  `;
}

function renderRecommendationPanel() {
  const qualityMode = getCurrentQualityScoreMode();
  const summary = MANAGER_MOCK_SUMMARY;
  const level = getOperationLevel(summary);
  const panel = document.getElementById("recommendationPanel");
  const assignments = buildRecommendationAssignmentsFromCurrentData(summary);
  CURRENT_RECOMMENDATION_ASSIGNMENTS = assignments;
  const mainAssignment = assignments[0] || null;
  const dateLabel = formatDateLabel(getResponseDateKeyFromDb(currentDatabaseResponse || summary.rawDatabaseResponse));
  const hourLabel = `${String(getCurrentDataHour()).padStart(2, "0")}:00`;
  const modeLabel = selectedReportHourMode === "live" ? "目前 Current" : "回顧時段";

  panel.innerHTML = `
    <div class="recommendation-title">
      <div>
        <p class="rec-eyebrow">任務分派</p>
        <h2>站別工程師</h2>
      </div>
      <div class="recommendation-title-actions">
        <span class="status-pill ${statusClass(mainAssignment?.level || level)}">${escapeHtml(mainAssignment?.level || level)}</span>
        <button
          type="button"
          class="drawer-close-btn"
          id="recommendationDrawerCloseBtn"
          aria-label="關閉工程師面板"
        >
          關閉
        </button>
      </div>
    </div>

    ${assignments.length ? `
      <div class="recommendation-summary-row">
        <div>
          <strong>${escapeHtml(modeLabel)} ${escapeHtml(dateLabel)} ${escapeHtml(hourLabel)}：${escapeHtml(mainAssignment.station)} / ${escapeHtml(mainAssignment.processLayer)}</strong>
          <p>
            P1 通知 ${escapeHtml(mainAssignment.owner)}；判斷原因是 ${escapeHtml(mainAssignment.issueDirection)}。
            這裡會跟著所選日期 / 小時的 DB 或 API snapshot 重新計算。
          </p>
        </div>
        <div class="recommendation-summary-count">
          ${assignments.length} 項
        </div>
      </div>

      <div class="recommendation-collapsible-body">
        ${renderNoActionImpactAlert(mainAssignment, summary, dateLabel, hourLabel)}

        <div class="assignment-list">
          ${assignments.map((item, index) => `
            <article class="assignment-card priority-${index + 1}">
              <div class="assignment-head">
                <span class="assignment-priority">${escapeHtml(item.priority)}</span>
                <span class="assignment-status ${assignmentStatusClass(item.status)}">${escapeHtml(item.status)}</span>
              </div>
              <div class="assignment-owner">${escapeHtml(item.owner)}</div>
              <div class="assignment-grid">
                <div><strong>站別：</strong>${escapeHtml(item.station)} / ${escapeHtml(item.processLayer)}</div>
                <div><strong>問題：</strong>${escapeHtml(item.issueDirection)}</div>
                <div><strong>證據：</strong>${escapeHtml(item.evidence)}</div>
                <div><strong>任務：</strong>${escapeHtml(item.task)}</div>
                <div><strong>期限：</strong>${escapeHtml(item.due)}</div>
                <div><strong>驗收：</strong>${escapeHtml(item.acceptance)}</div>
              </div>
              <button type="button" class="send-warning-btn" data-assignment-index="${index}">
                發送通知 Email
              </button>
            </article>
          `).join("")}
        </div>

        <section class="acceptance-checklist">
          <h3>改善是否有效，看該小時後的資料</h3>
          <ul>
            ${assignments.slice(0, 1).map(item => `
              <li>${escapeHtml(item.station)} / ${escapeHtml(item.processLayer)}：${escapeHtml(item.issueDirection)} 是否消失</li>
              <li>${escapeHtml(qualityMode.scoreLabel)}是否回到 92% 以上或停止下降</li>
              <li>堵塞率、流量、噴幅、稼動率、Cycle Time 是否回到可接受範圍</li>
            `).join("")}
          </ul>
        </section>

        <div class="data-reminder">
          任務分派現在依照選定日期與選定小時的 API-shaped snapshot 產生。若下一小時恢復正常，仍可回到問題小時查看當時該叫誰檢查、檢查什麼。
        </div>
      </div>
    ` : buildRecommendationNoActionBlock(summary)}
  `;
}

function buildEngineerWarningPayload(assignment) {
  const summary = MANAGER_MOCK_SUMMARY;
  const level = assignment.level || getOperationLevel(summary);
  const dateLabel = formatDateLabel(getResponseDateKeyFromDb(currentDatabaseResponse || summary.rawDatabaseResponse));
  const hourLabel = `${String(getCurrentDataHour()).padStart(2, "0")}:00`;

  return {
    warningId: `ENGINEER-${assignment.priority}-${Date.now()}`,
    timestamp: new Date().toLocaleString("zh-TW", { timeZone: "Asia/Taipei" }),
    source: summary.dataSource,
    apiVersion: summary.apiVersion,
    dataDate: dateLabel,
    dataHour: hourLabel,
    reviewMode: getTimeReviewModeLabel(),
    recipientRole: assignment.owner,
    recipientEmail: assignment.email,
    to: assignment.email,
    level,
    riskLevel: level === "緊急" ? "High" : "Warning",
    line: summary.lineName,
    station: assignment.station,
    processLayer: assignment.processLayer,
    machine: assignment.station,
    title: `${assignment.priority} ${assignment.owner} ${dateLabel} ${hourLabel} 站別任務通知`,
    issue: assignment.issue,
    issueDirection: assignment.issueDirection,
    batch: getCurrentBatchInfo(summary, assignment),
    evidence: assignment.evidence,
    impact: assignment.impact,
    task: assignment.task,
    due: assignment.due,
    acceptance: assignment.acceptance,
    message:
      `請依照 ${dateLabel} ${hourLabel} 的資料處理 ${assignment.station} / ${assignment.processLayer}：${assignment.issueDirection}。` +
      `證據：${assignment.evidence}。任務：${assignment.task}`,
    mainCause: assignment.evidence,
    suggestedAction: assignment.task,
    stationMetrics: assignment.stationMetrics || summary.mainStationMetrics,
    predictedOkRate: summary.predictedOkRate,
    predictedNgPcs: summary.predictedNgPcs,
    lostProductionPcs: summary.lostProductionPcs,
    dataStatus: selectedReportHourMode === "live"
      ? "目前 Current 小時資料，當天品質分數仍屬待 QC / 預測品質。"
      : `${getCurrentQualityScoreMode().sourceStatus}；歷史回顧小時資料，用於追查當時異常與任務分派。`
  };
}

function postEngineerWarningPayload(payload) {
  if (!CONFIG.WARNING_APP_SCRIPT_URL) {
    console.log("[MAIL DEBUG] No Apps Script URL. Payload:", payload);
    return Promise.resolve({ ok: true, mock: true });
  }

  return new Promise((resolve, reject) => {
    try {
      const iframeName = "engineerMailFrame_" + Date.now();
      const iframe = document.createElement("iframe");
      iframe.name = iframeName;
      iframe.style.display = "none";

      const form = document.createElement("form");
      form.method = "POST";
      form.action = CONFIG.WARNING_APP_SCRIPT_URL + "?source=engineer_assignment&ts=" + Date.now();
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
        setTimeout(() => {
          form.remove();
          iframe.remove();
        }, 1000);
        resolve({ ok: true, method: "hidden-form-post" });
      };

      form.submit();

      setTimeout(() => {
        if (resolved) return;
        resolved = true;
        form.remove();
        iframe.remove();
        resolve({ ok: true, method: "hidden-form-post-timeout" });
      }, 5000);
    } catch (error) {
      reject(error);
    }
  });
}

async function sendEngineerWarningEmail(index) {
  const assignment = CURRENT_RECOMMENDATION_ASSIGNMENTS[index] || ASSIGNMENT_CARDS[index];
  if (!assignment) return;

  const payload = buildEngineerWarningPayload(assignment);
  const button = document.querySelector(`[data-assignment-index="${index}"]`);

  try {
    if (button) {
      button.disabled = true;
      button.textContent = "發送中...";
      button.classList.remove("failed");
    }

    await postEngineerWarningPayload(payload);

    if (button) {
      button.textContent = "已送出";
      button.classList.add("sent");
    }

    console.log("[MAIL SENT] Engineer warning payload:", payload);
  } catch (error) {
    console.error("[MAIL ERROR] Engineer warning failed:", error);
    if (button) {
      button.disabled = false;
      button.textContent = "發送失敗，重試";
      button.classList.add("failed");
    }
  }
}

function renderDataStatusBar() {
  const dataStatus = MANAGER_MOCK_SUMMARY.dataStatus;
  const bar = document.getElementById("dataStatusBar");
  const quality = getSelectedQualityInfo(MANAGER_MOCK_SUMMARY);
  const dateLabel = formatDateLabel(selectedReportDate);

  bar.innerHTML = `
    <div class="data-status-compact">
      <div class="data-status-main">
        <span class="live-dot ${latestDataError ? "error" : "ok"}"></span>
        <strong>資料狀態：</strong>
        ${escapeHtml(dateLabel)}｜${escapeHtml(getTimeReviewModeLabel())}｜品質等級 ${escapeHtml(quality.grade)}｜${escapeHtml(quality.value)}｜${escapeHtml(quality.sourceStatus)}
      </div>
      <div class="data-status-detail">
        來源 ${escapeHtml(dataStatus.source)}｜契約 ${escapeHtml(dataStatus.apiVersion)}｜今日資料完整度 ${escapeHtml(dataStatus.todayCompleteness)}%｜
        本週 ${escapeHtml(dataStatus.weekProgress)}｜未來 7 天為 forecastNoAction 推估｜最後更新 ${escapeHtml(formatLastUpdateTime(lastDataUpdateAt))}
      </div>
    </div>
  `;
}


function getDecisionSnapshotFromSummary(summary) {
  const diagnosis = buildRealtimeDiagnosis(summary);
  const main = diagnosis.main;

  if (!main) {
    return {
      key: "normal",
      label: "目前無異常",
      station: "無",
      direction: "無需處理",
      level: "正常",
      hour: getCurrentDataHour()
    };
  }

  return {
    key: `${main.station.lineId}_${main.topIssue.direction}_${main.topIssue.level}`,
    label: `${main.responsibility.stationName} / ${main.responsibility.layerName}：${main.topIssue.direction}`,
    station: `${main.responsibility.stationName} / ${main.responsibility.layerName}`,
    direction: main.topIssue.direction,
    level: main.topIssue.level,
    hour: getCurrentDataHour()
  };
}

function recordSimulatedDecisionAudit(summary) {
  if (!CONFIG.SIMULATED_API_ENABLED) return;

  const snapshot = getDecisionSnapshotFromSummary(summary);
  const currentTime = currentDatabaseResponse?.responseMeta?.dataWindow?.currentEnd || getSimulatedGeneratedAt();

  if (!latestDecisionSnapshot || latestDecisionSnapshot.key !== snapshot.key || latestDecisionSnapshot.hour !== snapshot.hour) {
    previousDecisionSnapshot = latestDecisionSnapshot;
    latestDecisionSnapshot = snapshot;
    SIMULATED_DECISION_HISTORY.unshift({
      ...snapshot,
      time: currentTime,
      uploadNo: SIMULATED_API_UPLOAD_INDEX + 1
    });
    SIMULATED_DECISION_HISTORY = SIMULATED_DECISION_HISTORY.slice(0, 6);
  }
}

function renderApiSimulationStatusPanel(summary) {
  if (!CONFIG.SIMULATED_API_ENABLED) return "";

  const status = getSimulatedApiStatusText();
  const segment = getTimeSegmentSummaryText();
  const currentDecision = latestDecisionSnapshot || getDecisionSnapshotFromSummary(summary);
  const previousDecision = previousDecisionSnapshot;
  const changedText = previousDecision && previousDecision.key !== currentDecision.key
    ? `已變更：${previousDecision.label} → ${currentDecision.label}`
    : "目前決策未變更";

  return `
    <section class="api-simulation-panel">
      <div>
        <p class="content-section-kicker">Simulated API upload</p>
        <h3>API 模擬資料流：每 ${Math.round(status.intervalMs / 1000)} 秒更新一筆</h3>
        <p>目前模擬日期 ${escapeHtml(formatDateLabel(status.dateKey))}，第 ${escapeHtml(status.uploadNo)} 筆 API 回傳，資料時間 ${escapeHtml(status.generatedAt)}。畫面模式：${escapeHtml(getTimeReviewModeLabel())}。</p>
      </div>
      <div class="api-simulation-grid">
        <div>
          <span>日期 / Current 時間</span>
          <strong>${escapeHtml(formatDateLabel(status.dateKey))} ${escapeHtml(String(status.currentHour).padStart(2, "0"))}:00</strong>
          <p>${escapeHtml(segment.pastText)}｜${escapeHtml(segment.currentText)}｜${escapeHtml(segment.futureText)}</p>
        </div>
        <div>
          <span>目前情境</span>
          <strong>${escapeHtml(status.scenarioName)}</strong>
          <p>${escapeHtml(status.scenarioNote)}</p>
        </div>
        <div>
          <span>建議決策驗證</span>
          <strong>${escapeHtml(currentDecision.label)}</strong>
          <p>${escapeHtml(changedText)}</p>
        </div>
      </div>
      <div class="api-simulation-actions">
        <button type="button" class="api-sim-next-btn" data-sim-next-upload="1">立即模擬下一筆 API upload</button>
        <span>用途：驗證不同 DB/API 資料進來後，診斷、建議決策、Past / Current / Future 是否會同步改變。當 23:00 完成後會自動封存當天，下一筆切到隔天 00:00。</span>
      </div>
    </section>
  `;
}

function renderCockpit() {
  renderManagerHeader();
  renderSelectedQualityNote();
  renderCategoryButtons();
  renderCategoryContent(activeCategory);
  renderRecommendationPanel();
  renderDataStatusBar();
}

// ==============================
// Future API placeholders
// ==============================

async function fetchHistoricalActualData() {
  if (CONFIG.USE_MOCK_DATA || !CONFIG.HISTORICAL_ACTUAL_API_URL) return null;
  const response = await fetch(CONFIG.HISTORICAL_ACTUAL_API_URL);
  return response.json();
}

async function fetchRealtimeDataFromDB() {
  // Preferred path for this project: Project-SprayLine Dashboard v15 / DB Schema v2 endpoints.
  if (CONFIG.API_USE_PROJECT_SCHEMA) {
    const apiBundle = await fetchProjectSchemaApiBundle();
    return normalizeProjectApiBundleToManagerDb(apiBundle);
  }

  // Legacy path: one aggregate Manager UI endpoint.
  if (CONFIG.USE_MOCK_DATA || !CONFIG.DB_API_URL) return MOCK_DATABASE_RESPONSE;
  const response = await fetch(CONFIG.DB_API_URL);
  return response.json();
}

async function fetchFutureForecastData() {
  if (CONFIG.USE_MOCK_DATA || !CONFIG.FORECAST_API_URL) return null;
  const response = await fetch(CONFIG.FORECAST_API_URL);
  return response.json();
}

async function loadManagerData() {
  try {
    const activeDate = getActiveApiDateKey();
    let dbResponse = null;

    if (selectedReportHourMode === "hour") {
      const snapshot = getOrCreateHourlySnapshot(selectedReportDate, selectedReportHour);
      dbResponse = snapshot?.dbResponse || null;
    }

    if (!dbResponse) {
      const archived = selectedReportDate !== activeDate ? getArchivedDatabaseResponse(selectedReportDate) : null;
      dbResponse = archived || await fetchRealtimeDataFromDB();
    }

    currentDatabaseResponse = dbResponse || MOCK_DATABASE_RESPONSE;
    MANAGER_MOCK_SUMMARY = buildManagerReportFromDatabase(currentDatabaseResponse);
    ASSIGNMENT_CARDS = MANAGER_MOCK_SUMMARY.assignments;
    ACCEPTANCE_CHECKLIST = MANAGER_MOCK_SUMMARY.acceptanceChecklist;
    storeHourlySnapshotForDbResponse(currentDatabaseResponse);
    recordSimulatedDecisionAudit(MANAGER_MOCK_SUMMARY);
    lastDataUpdateAt = new Date();
    latestDataError = "";
  } catch (error) {
    console.error("[DATA ERROR] Failed to load manager data:", error);
    latestDataError = error.message || "資料載入失敗";
    currentDatabaseResponse = MOCK_DATABASE_RESPONSE;
    MANAGER_MOCK_SUMMARY = buildManagerReportFromDatabase(currentDatabaseResponse);
    ASSIGNMENT_CARDS = MANAGER_MOCK_SUMMARY.assignments;
    ACCEPTANCE_CHECKLIST = MANAGER_MOCK_SUMMARY.acceptanceChecklist;
  }
}


async function refreshManagerDataAndRender({ advanceSimulation = false } = {}) {
  let shouldStoreLiveSnapshotBeforeReview = false;

  if (advanceSimulation && CONFIG.SIMULATED_API_ENABLED) {
    const oldActiveDate = getActiveApiDateKey();
    const maxIndex = Math.max(0, Number(CONFIG.SIMULATED_API_MAX_HOUR || 23) - Number(CONFIG.SIMULATED_API_START_HOUR || 0));

    if (SIMULATED_API_UPLOAD_INDEX >= maxIndex) {
      archiveDatabaseResponseForDate(oldActiveDate, currentDatabaseResponse, "simulated_day_completed");
      SIMULATED_API_DAY_INDEX += 1;
      SIMULATED_API_UPLOAD_INDEX = 0;

      if (selectedReportDate === oldActiveDate && selectedReportHourMode === "live") {
        selectedReportDate = getActiveApiDateKey();
      }
    } else {
      SIMULATED_API_UPLOAD_INDEX += 1;
    }

    saveSimulatedApiState("advance_simulated_upload");
    shouldStoreLiveSnapshotBeforeReview = selectedReportHourMode === "hour";
  }

  if (shouldStoreLiveSnapshotBeforeReview) {
    try {
      const liveDb = await fetchRealtimeDataFromDB();
      storeHourlySnapshotForDbResponse(liveDb);
    } catch (error) {
      console.warn("[Hourly history] failed to store live snapshot while reviewing past hour", error);
    }
  }

  await loadManagerData();
  renderCockpit();
}

function startAutoDataRefresh() {
  const intervalMs = CONFIG.SIMULATED_API_ENABLED
    ? CONFIG.SIMULATED_API_UPLOAD_INTERVAL_MS
    : (CONFIG.USE_MOCK_DATA ? CONFIG.MOCK_POLL_INTERVAL_MS : CONFIG.DB_POLL_INTERVAL_MS);

  if (!intervalMs || intervalMs <= 0) return;

  window.setInterval(() => {
    refreshManagerDataAndRender({ advanceSimulation: CONFIG.SIMULATED_API_ENABLED });
  }, intervalMs);
}

function initCockpit() {
  renderCockpit();

  document.getElementById("categoryButtons").addEventListener("click", event => {
    const button = event.target.closest("[data-category]");
    if (!button) return;
    setActiveCategory(button.dataset.category);
  });

  document.getElementById("categoryContent").addEventListener("click", event => {
    const simButton = event.target.closest("[data-sim-next-upload]");
    if (simButton) {
      refreshManagerDataAndRender({ advanceSimulation: true });
      return;
    }

    const chartButton = event.target.closest("[data-detail-line-id]");
    if (!chartButton) return;
    setStationDetailOpen(true, chartButton.dataset.detailLineId);
  });

  document.getElementById("managerHeader").addEventListener("click", event => {
    const trigger = event.target.closest("#reportHourDropdownTrigger");
    if (trigger) {
      const picker = trigger.closest(".time-review-picker");
      const isOpen = picker.classList.toggle("is-open");
      trigger.setAttribute("aria-expanded", isOpen ? "true" : "false");
      return;
    }

    const hourOption = event.target.closest("[data-report-hour-option]");
    if (!hourOption) return;

    const selectedValue = hourOption.dataset.reportHourOption;
    if (selectedValue === "live") {
      selectedReportHourMode = "live";
      selectedReportHour = null;
      selectedReportDate = getActiveApiDateKey();
    } else {
      selectedReportHourMode = "hour";
      selectedReportHour = Number(selectedValue);
    }

    loadManagerData().then(renderCockpit);
  });

  document.addEventListener("click", event => {
    if (event.target.closest("#managerHeader .time-review-picker")) return;
    const picker = document.querySelector("#managerHeader .time-review-picker");
    if (!picker) return;
    picker.classList.remove("is-open");
    const trigger = document.getElementById("reportHourDropdownTrigger");
    if (trigger) trigger.setAttribute("aria-expanded", "false");
  });

  document.getElementById("managerHeader").addEventListener("change", event => {
    const dateSelect = event.target.closest("#reportDateSelect");
    if (!dateSelect) return;

    selectedReportDate = dateSelect.value;
    setDefaultTimeSelectionForDate(selectedReportDate);
    loadManagerData().then(renderCockpit);
  });

  document.getElementById("recommendationDrawerTrigger").addEventListener("click", () => {
    setRecommendationDrawerOpen(true);
  });

  document.getElementById("drawerOverlay").addEventListener("click", () => {
    setRecommendationDrawerOpen(false);
  });

  document.getElementById("stationDetailOverlay").addEventListener("click", () => {
    setStationDetailOpen(false);
  });

  document.getElementById("stationDetailPanel").addEventListener("click", event => {
    const closeButton = event.target.closest("#stationDetailCloseBtn");
    if (!closeButton) return;
    setStationDetailOpen(false);
  });

  document.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;

    if (isStationDetailOpen) {
      setStationDetailOpen(false);
      return;
    }

    if (isRecommendationDrawerOpen) {
      setRecommendationDrawerOpen(false);
    }
  });

  document.getElementById("recommendationPanel").addEventListener("click", event => {
    const closeButton = event.target.closest("#recommendationDrawerCloseBtn");
    if (closeButton) {
      setRecommendationDrawerOpen(false);
      return;
    }

    const button = event.target.closest("[data-assignment-index]");
    if (!button) return;

    sendEngineerWarningEmail(Number(button.dataset.assignmentIndex));
  });
}
loadManagerData().finally(() => {
  initCockpit();
  startAutoDataRefresh();
});
