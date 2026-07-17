// =======================================
// Configuration, mock payloads, and base constants
// Split from the original dashboard.js to keep files focused and maintainable.
// =======================================
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
  DB_API_URL: "http://127.0.0.1:5000/api/manager/dashboard",
  FORECAST_API_URL: "",

  API_BASE_URL: "http://127.0.0.1:5000",
  API_USE_PROJECT_SCHEMA: false,
  API_LINE_IDS: ["line_1", "line_2", "line_3"],
  API_TREND_TIMESTEP: "hour",
  API_DATE: "2026-06-08",
  SIMULATED_API_START_DATE: "2026-06-08",
  SIMULATED_API_START_HOUR: 0,
  SIMULATED_API_MAX_HOUR: 23,
  SIMULATED_API_STEP_HOURS: 1,

  WARNING_APP_SCRIPT_URL: "https://script.google.com/macros/s/AKfycbyvPzX3epFpOH9AUFLLlD_-W4EXCOULHInUZKfmnCyJHlrCOY_HYTNSCBLtm3ZVzoWnBQ/exec",
  DB_POLL_INTERVAL_MS: 20 * 60 * 1000,
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
      engineerEmail: "hotak702@gmail.com"
    },
    line_2: {
      stationName: "第二站",
      layerName: "顏色層",
      machineName: "第二站噴塗機",
      engineerRole: "第二站負責工程師",
      engineerEmail: "hotak702@gmail.com"
    },
    line_3: {
      stationName: "第三站",
      layerName: "保護層",
      machineName: "第三站噴塗機",
      engineerRole: "第三站負責工程師",
      engineerEmail: "hotak702@gmail.com"
    },
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
    engineerEmail: "hotak702@gmail.com",
    recipeId: "BASE-WHITE-01"
  },
  line_2: {
    stationName: "第二站",
    layerName: "顏色層",
    machineName: "第二站噴塗機",
    stationNameZh: "面漆站",
    stationNameEn: "Topcoat Station",
    engineerRole: "第二站負責工程師",
    engineerEmail: "hotak702@gmail.com",
    recipeId: "COLOR-WHITE-01"
  },
  line_3: {
    stationName: "第三站",
    layerName: "保護層",
    machineName: "第三站噴塗機",
    stationNameZh: "金漆站",
    stationNameEn: "Clearcoat Station",
    engineerRole: "第三站負責工程師",
    engineerEmail: "hotak702@gmail.com",
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


