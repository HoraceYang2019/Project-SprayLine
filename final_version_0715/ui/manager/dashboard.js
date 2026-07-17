// =======================================
// Data loading, refresh orchestration, and application bootstrap
// Split from the original dashboard.js to keep files focused and maintainable.
// =======================================
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
    MANAGER_MOCK_SUMMARY = getManagerSummaryFromDatabase(currentDatabaseResponse);
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
    MANAGER_MOCK_SUMMARY = getManagerSummaryFromDatabase(currentDatabaseResponse);
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
