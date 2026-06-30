let latestManagerDataErrorDetails = null;

function renderCockpit() {
  renderManagerView();
}

function renderStaticHeader() {
  const header = document.getElementById("managerHeader");
  if (!header) return;

  header.innerHTML = `
    <div class="manager-header-title">
      <h1>Manager Dashboard</h1>
    </div>
  `;
}

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
  CURRENT_RECOMMENDATION_ASSIGNMENTS = getRecommendationItems();
  syncSelectedDateHourFromDb(dbResponse);
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
    suggestion: normalized.uiSuggestion || "Please check /api/manager/dashboard response payload."
  };
}

function clearManagerSections() {
  const errorBanner = document.getElementById("managerErrorBanner");
  const overview = document.getElementById("managerOverviewSection");
  const recommendations = document.getElementById("managerRecommendationSection");

  if (errorBanner) errorBanner.innerHTML = "";
  if (overview) overview.innerHTML = "";
  if (recommendations) recommendations.innerHTML = "";
}

function renderManagerErrorState() {
  renderStaticHeader();
  setTrendDrawerOpen(false);

  const details = latestManagerDataErrorDetails || {
    title: "Manager API connection failed",
    endpoint: getManagerDashboardApiUrl() || "(not configured)",
    status: "",
    reason: latestDataError || "Unknown error",
    missingField: "",
    suggestion: "Please confirm API Server is running."
  };

  const errorBanner = document.getElementById("managerErrorBanner");
  if (errorBanner) {
    errorBanner.innerHTML = `
      <section class="error-banner" role="alert" aria-live="assertive">
        <strong>${escapeHtml(details.title)}</strong>
        <p>資料載入失敗，請確認 API Server 或所選日期 / 小時是否有資料。</p>
        <p>Endpoint: ${escapeHtml(details.endpoint)}</p>
        <p>Reason: ${escapeHtml(details.reason)}</p>
        ${details.status ? `<p>Status: ${escapeHtml(details.status)}</p>` : ""}
        ${details.missingField ? `<p>Field: ${escapeHtml(details.missingField)}</p>` : ""}
      </section>
    `;
  }

  const overview = document.getElementById("managerOverviewSection");
  const recommendations = document.getElementById("managerRecommendationSection");
  if (overview) overview.innerHTML = "";
  if (recommendations) recommendations.innerHTML = "";
}

function renderManagerView() {
  const hasLiveData = Boolean(MANAGER_SUMMARY && !latestManagerDataErrorDetails);
  if (!hasLiveData) {
    renderManagerErrorState();
    return;
  }

  renderManagerHeader();
  clearManagerSections();
  renderOverviewSection();
  renderRecommendationSection();
  renderTrendDrawer();
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

function isValidDateKeyForManagerRequest(date) {
  return typeof date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(date);
}

function isValidHourForManagerRequest(hour) {
  if (hour === null || hour === undefined || hour === "") return false;
  const numericHour = Number(hour);
  return Number.isInteger(numericHour) && numericHour >= 0 && numericHour <= 23;
}

function isValidBatchIdForManagerRequest(batchId) {
  return typeof batchId === "string" && batchId.trim() !== "";
}

function buildManagerDashboardRequestEndpoint({
  date = undefined,
  hour = undefined,
  batchId = undefined
} = {}) {
  const baseEndpoint = getManagerDashboardApiUrl();
  if (!baseEndpoint) return "";

  const url = new URL(baseEndpoint, window.location.origin);
  const hasValidDate = isValidDateKeyForManagerRequest(date);
  const hasValidHour = hasValidDate && isValidHourForManagerRequest(hour);

  if (hasValidDate) {
    url.searchParams.set("date", String(date));
  }

  if (hasValidHour) {
    url.searchParams.set("hour", String(Number(hour)));
  }

  if (hasValidHour && isValidBatchIdForManagerRequest(batchId)) {
    url.searchParams.set("batch_id", String(batchId).trim());
  }

  return url.toString();
}

async function fetchRealtimeDataFromDB({
  date = undefined,
  hour = undefined,
  batchId = undefined
} = {}) {
  const endpoint = buildManagerDashboardRequestEndpoint({ date, hour, batchId });
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
  date = selectedReportDate,
  hour = selectedReportHour,
  batchId = selectedBatchId
} = {}) {
  try {
    const requestDate = isValidDateKeyForManagerRequest(date) ? String(date) : undefined;
    const requestHour = requestDate && isValidHourForManagerRequest(hour)
      ? Number(hour)
      : undefined;
    const requestBatchId = requestDate && requestHour !== undefined && isValidBatchIdForManagerRequest(batchId)
      ? String(batchId).trim()
      : undefined;

    const dbResponse = await fetchRealtimeDataFromDB({
      date: requestDate,
      hour: requestHour,
      batchId: requestBatchId
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
    CURRENT_RECOMMENDATION_ASSIGNMENTS = [];
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

  document.addEventListener("click", event => {
    const hourTrigger = event.target.closest("#reportHourDropdownTrigger");
    if (hourTrigger) {
      const picker = document.getElementById("reportHourPicker");
      const isOpen = picker?.classList.toggle("is-open");
      hourTrigger.setAttribute("aria-expanded", isOpen ? "true" : "false");
      return;
    }

    const hourOption = event.target.closest("[data-report-hour-option]");
    if (hourOption) {
      const selectedValue = Number(hourOption.dataset.reportHourOption);
      if (!Number.isFinite(selectedValue)) return;
      selectedBatchId = null;
      loadManagerData({
        date: selectedReportDate,
        hour: selectedValue,
        batchId: null
      }).then(() => renderManagerView());
      return;
    }

    const trendButton = event.target.closest("[data-trend-station-id][data-trend-metric]");
    if (trendButton) {
      setTrendDrawerOpen(
        true,
        trendButton.dataset.trendStationId,
        trendButton.dataset.trendMetric
      );
      return;
    }

    const notifyButton = event.target.closest("[data-recommendation-index]");
    if (notifyButton) {
      sendEngineerWarningEmail(Number(notifyButton.dataset.recommendationIndex));
      return;
    }

    const closeDrawerButton = event.target.closest("#trendDrawerCloseBtn");
    if (closeDrawerButton) {
      setTrendDrawerOpen(false);
      return;
    }

    if (event.target.closest("#reportHourPicker")) return;
    const picker = document.getElementById("reportHourPicker");
    const trigger = document.getElementById("reportHourDropdownTrigger");
    if (picker) picker.classList.remove("is-open");
    if (trigger) trigger.setAttribute("aria-expanded", "false");
  });

  document.addEventListener("change", event => {
    const dateSelect = event.target.closest("#reportDateSelect");
    if (dateSelect) {
      selectedBatchId = null;
      loadManagerData({ date: dateSelect.value, hour: null, batchId: null }).then(() => renderManagerView());
      return;
    }

    const batchSelect = event.target.closest("#batchSelect");
    if (batchSelect) {
      selectedBatchId = batchSelect.value || null;
      loadManagerData({
        date: selectedReportDate,
        hour: selectedReportHour,
        batchId: selectedBatchId
      }).then(() => renderManagerView());
    }
  });

  document.getElementById("drawerOverlay")?.addEventListener("click", () => {
    setTrendDrawerOpen(false);
  });

  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && isTrendDrawerOpen) {
      setTrendDrawerOpen(false);
    }
  });
}

loadManagerData().finally(() => {
  initCockpit();
  startAutoDataRefresh();
});
