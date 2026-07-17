// =======================================
// Simulated archive state, local storage, and hourly review helpers
// Split from the original dashboard.js to keep files focused and maintainable.
// =======================================
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
  const startDate = CONFIG.SIMULATED_API_START_DATE || CONFIG.API_DATE || getDateKey(new Date());
  if (!CONFIG.SIMULATED_API_ENABLED) return CONFIG.API_DATE || startDate;
  return addDaysToDateKey(startDate, SIMULATED_API_DAY_INDEX);
}

function getInitialReportDateKey() {
  return CONFIG.SIMULATED_API_ENABLED ? getActiveApiDateKey() : (CONFIG.API_DATE || getDateKey(new Date()));
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
    const summary = getManagerSummaryFromDatabase(dbResponse);
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

