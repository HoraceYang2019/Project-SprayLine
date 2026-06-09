from pathlib import Path
p=Path('/mnt/data/date_rollover_work/dashboard.js')
s=p.read_text()
# CONFIG changes
s=s.replace('API_DATE: "2026-06-09",\n  SIMULATED_API_START_HOUR: 10,', 'API_DATE: "2026-06-08",\n  SIMULATED_API_START_DATE: "2026-06-08",\n  SIMULATED_API_START_HOUR: 0,')
s=s.replace('SIMULATED_API_UPLOAD_INTERVAL_MS: 5000\n};', 'SIMULATED_API_UPLOAD_INTERVAL_MS: 5000,\n  SIMULATED_HISTORY_STORAGE_KEY: "spray_manager_daily_archive_v1"\n};')
# variables
s=s.replace('let SIMULATED_API_UPLOAD_INDEX = 0;\nlet SIMULATED_DECISION_HISTORY = [];', 'let SIMULATED_API_UPLOAD_INDEX = 0;\nlet SIMULATED_API_DAY_INDEX = 0;\nlet SIMULATED_DECISION_HISTORY = [];')
# Insert date/history helpers before getSimulatedApiCurrentHour
marker='function getSimulatedApiCurrentHour() {'
helpers=r'''
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

function getSimulatedArchiveStore() {
  if (typeof localStorage === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(CONFIG.SIMULATED_HISTORY_STORAGE_KEY) || "{}");
  } catch (error) {
    console.warn("[Archive] failed to read daily archive", error);
    return {};
  }
}

function saveSimulatedArchiveStore(store) {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(CONFIG.SIMULATED_HISTORY_STORAGE_KEY, JSON.stringify(store || {}));
  } catch (error) {
    console.warn("[Archive] failed to save daily archive", error);
  }
}

function getArchivedDateKeys() {
  return Object.keys(getSimulatedArchiveStore()).sort().reverse();
}

function getArchivedDatabaseResponse(dateKey) {
  return getSimulatedArchiveStore()[dateKey]?.dbResponse || null;
}

function archiveDatabaseResponseForDate(dateKey, dbResponse, reason = "day_completed") {
  if (!dateKey || !dbResponse) return;
  const store = getSimulatedArchiveStore();
  store[dateKey] = {
    date: dateKey,
    reason,
    archivedAt: new Date().toISOString(),
    dbResponse: JSON.parse(JSON.stringify(dbResponse))
  };
  saveSimulatedArchiveStore(store);
}

function getSelectedDateMode() {
  const activeDate = getActiveApiDateKey();
  if (selectedReportDate === activeDate) return "active";
  if (getArchivedDatabaseResponse(selectedReportDate)) return "archive";
  return "missing";
}

'''
if helpers not in s:
    s=s.replace(marker, helpers+marker)
# getGeneratedAt update
s=s.replace('return `${CONFIG.API_DATE}T${String(hour).padStart(2, "0")}:20:00+08:00`;', 'return `${getActiveApiDateKey()}T${String(hour).padStart(2, "0")}:20:00+08:00`;')
# buildProjectSchemaMockBundle add currentDateKey and replace uses
s=s.replace('const generatedAt = getSimulatedGeneratedAt();\n  const scenario = getSimulatedScenario(currentHour);', 'const generatedAt = getSimulatedGeneratedAt();\n  const currentDateKey = getActiveApiDateKey();\n  const previousDateKey = addDaysToDateKey(currentDateKey, -1);\n  const scenario = getSimulatedScenario(currentHour);')
s=s.replace('`rw_${lineId}_${CONFIG.API_DATE.replace(/-/g, "")}_${String(currentHour).padStart(2, "0")}20`', '`rw_${lineId}_${currentDateKey.replace(/-/g, "")}_${String(currentHour).padStart(2, "0")}20`')
s=s.replace('date: CONFIG.API_DATE,\n      predicted_ok_rate:', 'date: currentDateKey,\n      predicted_ok_rate:')
s=s.replace('date: "2026-06-08",\n      yesterday_predicted_ok:', 'date: previousDateKey,\n      yesterday_predicted_ok:')
# normalizeProjectApiBundleToManagerDb date window
s=s.replace('if (!apiBundle || !apiBundle.stationLatest) return MOCK_DATABASE_RESPONSE;\n\n  const lineIds = CONFIG.API_LINE_IDS;', 'if (!apiBundle || !apiBundle.stationLatest) return MOCK_DATABASE_RESPONSE;\n\n  const apiDateKey = getDateKeyFromTimestamp(apiBundle.generated_at) || getActiveApiDateKey();\n  const lineIds = CONFIG.API_LINE_IDS;')
s=s.replace('currentStart: `${CONFIG.API_DATE}T00:00:00+08:00`,\n        currentEnd: apiBundle.generated_at || `${CONFIG.API_DATE}T10:20:00+08:00`,', 'currentStart: `${apiDateKey}T00:00:00+08:00`,\n        currentEnd: apiBundle.generated_at || `${apiDateKey}T10:20:00+08:00`,')
# selected date init
s=s.replace('let selectedReportDate = getDateKey(new Date());', 'let selectedReportDate = getInitialReportDateKey();')
# getTodayKey function use active for simulated
s=s.replace('function getTodayKey() {\n  return getDateKey(new Date());\n}', 'function getTodayKey() {\n  return CONFIG.SIMULATED_API_ENABLED ? getActiveApiDateKey() : getDateKey(new Date());\n}')
# isSelected pending
s=s.replace('function isSelectedDatePendingQC(dateKey) {\n  return dateKey >= getTodayKey();\n}', 'function isSelectedDatePendingQC(dateKey) {\n  return dateKey >= getActiveApiDateKey();\n}')
# generateDateOptions replace whole function
start=s.index('function generateDateOptions(daysBack = 14) {')
end=s.index('\nfunction getQualityGradeByOkRate', start)
new_func=r'''function generateDateOptions(daysBack = 14) {
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
'''
s=s[:start]+new_func+s[end:]
# render header add archive note in date card maybe replace overview-note
s=s.replace('<div class="overview-note">${escapeHtml(selectedQuality.sourceStatus)}</div>', '<div class="overview-note">${escapeHtml(selectedQuality.sourceStatus)}｜${escapeHtml(getSelectedDateMode() === "archive" ? "歷史回顧" : "即時模擬")}</div>')
# getSimulated status include date
s=s.replace('return {\n    uploadNo: SIMULATED_API_UPLOAD_INDEX + 1,\n    currentHour,', 'return {\n    uploadNo: SIMULATED_API_UPLOAD_INDEX + 1,\n    dateKey: getActiveApiDateKey(),\n    currentHour,')
# render sim panel text include date/archive
s=s.replace('目前模擬第 ${escapeHtml(status.uploadNo)} 筆 API 回傳，資料時間 ${escapeHtml(status.generatedAt)}。', '目前模擬日期 ${escapeHtml(formatDateLabel(status.dateKey))}，第 ${escapeHtml(status.uploadNo)} 筆 API 回傳，資料時間 ${escapeHtml(status.generatedAt)}。')
s=s.replace('<span>Current 時間</span>\n          <strong>${escapeHtml(String(status.currentHour).padStart(2, "0"))}:00</strong>', '<span>日期 / Current 時間</span>\n          <strong>${escapeHtml(formatDateLabel(status.dateKey))} ${escapeHtml(String(status.currentHour).padStart(2, "0"))}:00</strong>')
# add archive summary to sim panel after actions span
s=s.replace('<span>用途：驗證不同 DB/API 資料進來後，診斷、建議決策、Past / Current / Future 是否會同步改變。</span>', '<span>用途：驗證不同 DB/API 資料進來後，診斷、建議決策、Past / Current / Future 是否會同步改變。當 23:00 完成後會自動封存當天，下一筆切到隔天 00:00。</span>')
# replace refresh function
old=r'''async function refreshManagerDataAndRender({ advanceSimulation = false } = {}) {
  if (advanceSimulation && CONFIG.SIMULATED_API_ENABLED) {
    const maxIndex = Math.max(0, Number(CONFIG.SIMULATED_API_MAX_HOUR || 23) - Number(CONFIG.SIMULATED_API_START_HOUR || 10));
    SIMULATED_API_UPLOAD_INDEX = Math.min(maxIndex, SIMULATED_API_UPLOAD_INDEX + 1);
  }

  await loadManagerData();
  renderCockpit();
}
'''
new=r'''async function refreshManagerDataAndRender({ advanceSimulation = false } = {}) {
  if (advanceSimulation && CONFIG.SIMULATED_API_ENABLED) {
    const oldActiveDate = getActiveApiDateKey();
    const maxIndex = Math.max(0, Number(CONFIG.SIMULATED_API_MAX_HOUR || 23) - Number(CONFIG.SIMULATED_API_START_HOUR || 0));

    if (SIMULATED_API_UPLOAD_INDEX >= maxIndex) {
      archiveDatabaseResponseForDate(oldActiveDate, currentDatabaseResponse, "simulated_day_completed");
      SIMULATED_API_DAY_INDEX += 1;
      SIMULATED_API_UPLOAD_INDEX = 0;

      if (selectedReportDate === oldActiveDate) {
        selectedReportDate = getActiveApiDateKey();
      }
    } else {
      SIMULATED_API_UPLOAD_INDEX += 1;
    }
  }

  await loadManagerData();
  renderCockpit();
}
'''
if old not in s:
    raise SystemExit('old refresh function not found')
s=s.replace(old,new)
# loadManagerData replace beginning try
old2='''async function loadManagerData() {
  try {
    const dbResponse = await fetchRealtimeDataFromDB();
    currentDatabaseResponse = dbResponse || MOCK_DATABASE_RESPONSE;
    MANAGER_MOCK_SUMMARY = buildManagerReportFromDatabase(currentDatabaseResponse);'''
new2='''async function loadManagerData() {
  try {
    const activeDate = getActiveApiDateKey();
    const archived = selectedReportDate !== activeDate ? getArchivedDatabaseResponse(selectedReportDate) : null;
    const dbResponse = archived || await fetchRealtimeDataFromDB();
    currentDatabaseResponse = dbResponse || MOCK_DATABASE_RESPONSE;
    MANAGER_MOCK_SUMMARY = buildManagerReportFromDatabase(currentDatabaseResponse);'''
if old2 not in s:
    raise SystemExit('load header not found')
s=s.replace(old2,new2)
# event change: renderCockpit to reload data
old3='''    selectedReportDate = select.value;
    renderCockpit();
  });'''
new3='''    selectedReportDate = select.value;
    loadManagerData().then(renderCockpit);
  });'''
if old3 not in s:
    print('event change old not found')
else:
    s=s.replace(old3,new3,1)
# current display in sim panel for archived selected? maybe ok
p.write_text(s)
print('[OK] patched dashboard.js')
