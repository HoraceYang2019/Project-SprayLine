function renderCockpit() {
  renderManagerHeader();
  renderSelectedQualityNote();
  renderCategoryButtons();
  renderCategoryContent(activeCategory);
  renderRecommendationPanel();
  renderDataStatusBar();
}

let latestManagerDataErrorDetails = null;

function applyManagerDatabaseResponse(dbResponse) {
  const summary = getManagerSummaryFromDatabase(dbResponse);
  if (!summary) {
    throw buildManagerUiError({
      title: "Manager API data error",
      endpoint: dbResponse?.responseMeta?.requestedEndpoint,
      reason: "invalid payload",
      suggestion: "Please check /api/manager/dashboard response payload."
    });
  }

  currentDatabaseResponse = dbResponse;
  MANAGER_SUMMARY = summary;
  ASSIGNMENT_CARDS = Array.isArray(summary.assignments) ? summary.assignments : [];
  ACCEPTANCE_CHECKLIST = Array.isArray(summary.acceptanceChecklist) ? summary.acceptanceChecklist : [];
  syncSelectedDateHourFromDb(dbResponse);
}

function setManagerUiInteractiveState(enabled) {
  const trigger = document.getElementById("recommendationDrawerTrigger");
  if (!trigger) return;

  trigger.disabled = !enabled;
  trigger.hidden = !enabled;
  if (!enabled) {
    setRecommendationDrawerOpen(false);
    if (typeof setStationDetailOpen === "function") {
      setStationDetailOpen(false);
    }
  }
}

function captureManagerErrorDetails(error) {
  const normalized = normalizeManagerUiError(error, {
    title: "Manager API data error",
    endpoint: getManagerDashboardApiUrl(),
    suggestion: "Please check /api/manager/dashboard response payload."
  });

  return {
    title: normalized.uiTitle || "Manager API data error",
    endpoint: normalized.uiEndpoint || getManagerDashboardApiUrl() || "(not configured)",
    status: normalized.uiStatus || "",
    reason: normalized.uiReason || normalized.message || "Unknown error",
    missingField: normalized.uiMissingField || "",
    source: normalized.uiSource || "",
    suggestion: normalized.uiSuggestion || "Please check /api/manager/dashboard response payload."
  };
}

function renderManagerErrorState() {
  const details = latestManagerDataErrorDetails || {
    title: "Manager API data error",
    endpoint: getManagerDashboardApiUrl() || "(not configured)",
    status: "",
    reason: latestDataError || "Unknown error",
    missingField: "",
    source: "",
    suggestion: "Please check /api/manager/dashboard response payload."
  };

  const header = document.getElementById("managerHeader");
  if (header) {
    header.innerHTML = `
      <div class="decision-alert">
        <div class="header-title-row">
          <h1>${escapeHtml(details.title)}</h1>
        </div>
        <div class="overview-note">Endpoint: ${escapeHtml(details.endpoint)}</div>
      </div>
    `;
  }

  const note = document.getElementById("selectedQualityNote");
  if (note) {
    note.classList.remove("pending-qc", "actual-qc", "quality-good", "quality-warning");
    note.classList.add("quality-danger");
    note.innerHTML = `
      <strong>Reason</strong>
      <span class="quality-note-sub">${escapeHtml(details.reason)}</span>
    `;
  }

  const categoryButtons = document.getElementById("categoryButtons");
  if (categoryButtons) categoryButtons.innerHTML = "";

  const activeCategoryTitle = document.getElementById("activeCategoryTitle");
  if (activeCategoryTitle) activeCategoryTitle.textContent = details.title;

  const extraRows = [
    details.status ? `<div class="conclusion-item"><h3>Status</h3><p>${escapeHtml(details.status)}</p></div>` : "",
    details.missingField ? `<div class="conclusion-item"><h3>Missing field</h3><p>${escapeHtml(details.missingField)}</p></div>` : "",
    details.source ? `<div class="conclusion-item"><h3>Source</h3><p>${escapeHtml(details.source)}</p></div>` : ""
  ].join("");

  const categoryContent = document.getElementById("categoryContent");
  if (categoryContent) {
    categoryContent.innerHTML = `
      <section class="conclusion-card emergency" role="alert" aria-live="assertive">
        <div class="conclusion-status">
          <div class="conclusion-decision">${escapeHtml(details.title)}</div>
          <div class="conclusion-meta">Endpoint: ${escapeHtml(details.endpoint)}</div>
        </div>
        <div class="conclusion-copy">
          <div class="conclusion-item">
            <h3>Reason</h3>
            <p>${escapeHtml(details.reason)}</p>
          </div>
          ${extraRows}
          <div class="conclusion-item">
            <h3>Suggestion</h3>
            <p>${escapeHtml(details.suggestion)}</p>
          </div>
        </div>
      </section>
    `;
  }

  const recommendationPanel = document.getElementById("recommendationPanel");
  if (recommendationPanel) {
    recommendationPanel.innerHTML = "";
  }

  const statusBar = document.getElementById("dataStatusBar");
  if (statusBar) {
    statusBar.innerHTML = `
      <div class="data-status-compact" role="alert" aria-live="assertive">
        <div class="data-status-main">
          <span class="live-dot error"></span>
          <strong>${escapeHtml(details.title)}</strong>
        </div>
        <div class="data-status-detail">
          Endpoint: ${escapeHtml(details.endpoint)} | Reason: ${escapeHtml(details.reason)} | ${escapeHtml(details.suggestion)}
        </div>
      </div>
    `;
  }
}

function renderManagerView() {
  const hasLiveData = Boolean(MANAGER_SUMMARY && !latestManagerDataErrorDetails);
  setManagerUiInteractiveState(hasLiveData);

  if (!hasLiveData) {
    renderManagerErrorState();
    return;
  }

  try {
    renderCockpit();
  } catch (error) {
    latestManagerDataErrorDetails = captureManagerErrorDetails(error);
    latestDataError = latestManagerDataErrorDetails.reason;
    MANAGER_SUMMARY = null;
    renderManagerErrorState();
  }
}

async function parseManagerPayloadResponse(response, endpoint) {
  const bodyText = await response.text();

  if (!response.ok) {
    let errorReason = bodyText.trim() || `${response.status} ${response.statusText}`.trim();
    try {
      const errorPayload = JSON.parse(bodyText);
      errorReason = String(
        errorPayload?.detail ||
        errorPayload?.reason ||
        errorPayload?.message ||
        errorReason
      );
    } catch (_error) {
    }

    throw buildManagerUiError({
      title: "Manager API HTTP error",
      endpoint,
      status: `${response.status} ${response.statusText}`.trim(),
      reason: errorReason,
      suggestion: response.status >= 500
        ? "Please confirm API Server is running."
        : "Please check the selected date/hour or API Server logs."
    });
  }

  try {
    return JSON.parse(bodyText);
  } catch (error) {
    throw buildManagerUiError({
      title: "Manager API response parse error",
      endpoint,
      reason: "invalid JSON response",
      suggestion: "Please check /api/manager/dashboard response format.",
      cause: error
    });
  }
}

async function fetchHistoricalActualData() {
  return null;
}

async function fetchFutureForecastData() {
  return null;
}

function buildManagerDashboardRequestEndpoint({
  date = undefined,
  hour = undefined
} = {}) {
  const baseEndpoint = getManagerDashboardApiUrl();
  if (!baseEndpoint) return "";

  const url = new URL(baseEndpoint, window.location.href);
  if (date) {
    url.searchParams.set("date", String(date));
  }
  if (Number.isFinite(Number(hour))) {
    url.searchParams.set("hour", String(Number(hour)));
  }
  return url.toString();
}

async function fetchRealtimeDataFromDB({
  date = undefined,
  hour = undefined
} = {}) {
  const endpoint = buildManagerDashboardRequestEndpoint({ date, hour });
  if (!endpoint || !getManagerDashboardApiUrl()) {
    throw buildManagerUiError({
      title: "Manager API connection failed",
      endpoint: getManagerDashboardApiUrl(),
      reason: "MANAGER_DASHBOARD_API_URL is empty",
      suggestion: "Please confirm API Server is running on port 8011."
    });
  }

  try {
    const response = await fetch(endpoint);
    const payload = await parseManagerPayloadResponse(response, endpoint);
    payload.responseMeta = {
      ...(payload.responseMeta || {}),
      requestedEndpoint: endpoint
    };
    validateManagerDashboardPayload(payload, endpoint);

    console.info("[Manager UI] Loaded manager dashboard payload", {
      url: endpoint,
      source: payload?.responseMeta?.source || payload?.managerSummary?.dataSource || "unknown"
    });

    return payload;
  } catch (error) {
    if (error instanceof TypeError) {
      throw buildManagerUiError({
        title: "Manager API connection failed",
        endpoint,
        reason: "Failed to fetch",
        suggestion: "Please confirm API Server is running on port 8011.",
        cause: error
      });
    }

    throw normalizeManagerUiError(error, {
      title: "Manager API data error",
      endpoint,
      suggestion: "Please check /api/manager/dashboard response payload."
    });
  }
}

async function loadManagerData({
  date = selectedReportDate || undefined,
  hour = selectedReportHour
} = {}) {
  try {
    const dbResponse = await fetchRealtimeDataFromDB({
      date,
      hour: Number.isFinite(Number(hour)) ? Number(hour) : undefined
    });

    validateManagerDashboardPayload(dbResponse, dbResponse?.responseMeta?.requestedEndpoint || getManagerDashboardApiUrl());
    applyManagerDatabaseResponse(dbResponse);
    storeHourlySnapshotForDbResponse(currentDatabaseResponse);
    latestDataError = "";
    latestManagerDataErrorDetails = null;
    lastDataUpdateAt = new Date();
    return true;
  } catch (error) {
    latestManagerDataErrorDetails = captureManagerErrorDetails(error);
    latestDataError = latestManagerDataErrorDetails.reason;
    currentDatabaseResponse = null;
    MANAGER_SUMMARY = null;
    ASSIGNMENT_CARDS = [];
    ACCEPTANCE_CHECKLIST = [];
    lastDataUpdateAt = new Date();
    console.error("[Manager UI] load failed", error);
    return false;
  }
}

async function refreshManagerDataAndRender() {
  await loadManagerData();
  renderManagerView();
}

function startAutoDataRefresh() {
  const intervalMs = Number(CONFIG.DB_POLL_INTERVAL_MS || 0);
  if (!intervalMs || intervalMs <= 0) return;

  window.setInterval(() => {
    refreshManagerDataAndRender();
  }, intervalMs);
}

function initCockpit() {
  renderManagerView();

  document.getElementById("categoryButtons").addEventListener("click", event => {
    const button = event.target.closest("[data-category]");
    if (!button) return;
    setActiveCategory(button.dataset.category);
  });

  document.getElementById("categoryContent").addEventListener("click", event => {
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

    const selectedValue = Number(hourOption.dataset.reportHourOption);
    if (!Number.isFinite(selectedValue)) return;

    loadManagerData({
      date: selectedReportDate,
      hour: selectedValue
    }).then(() => renderManagerView());
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

    loadManagerData({ date: dateSelect.value }).then(() => renderManagerView());
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
