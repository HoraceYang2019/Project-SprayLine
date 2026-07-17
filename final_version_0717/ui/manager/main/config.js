const DEFAULT_MANAGER_API_PORT = "8011";
const DEFAULT_MANAGER_DASHBOARD_PATH = "/api/manager/dashboard";
const DEFAULT_ENGINEER_TASK_PATH = "/api/manager/engineer-tasks";

function buildLocalApiBaseUrl(port) {
  const hasWindow = typeof window !== "undefined" && window.location;
  const protocol = hasWindow && /^https?:$/.test(window.location.protocol)
    ? window.location.protocol
    : "http:";
  const hostname = hasWindow && window.location.hostname
    ? window.location.hostname
    : "127.0.0.1";
  return `${protocol}//${hostname}:${port}`;
}

const CONFIG = {
  MANAGER_API_BASE_URL: (
    typeof window !== "undefined" && String(window.__SPRAYLINE_MANAGER_API_BASE_URL__ || "").trim()
  ) || buildLocalApiBaseUrl(DEFAULT_MANAGER_API_PORT),
  MANAGER_DASHBOARD_API_URL: (
    typeof window !== "undefined" && String(window.__SPRAYLINE_MANAGER_DASHBOARD_API_URL__ || "").trim()
  ) || `${buildLocalApiBaseUrl(DEFAULT_MANAGER_API_PORT)}${DEFAULT_MANAGER_DASHBOARD_PATH}`,
  ENGINEER_TASK_API_URL: (
    typeof window !== "undefined" && String(window.__SPRAYLINE_ENGINEER_TASK_API_URL__ || "").trim()
  ) || "",
  DB_POLL_INTERVAL_MS: 20 * 60 * 1000,
  API_LINE_IDS: ["line_1", "line_2", "line_3"]
};

function getManagerDashboardApiUrl() {
  return String(CONFIG.MANAGER_DASHBOARD_API_URL || "").trim();
}

function getEngineerTaskApiUrl() {
  if (CONFIG.ENGINEER_TASK_API_URL) return CONFIG.ENGINEER_TASK_API_URL;
  return `${String(CONFIG.MANAGER_API_BASE_URL || "").replace(/\/$/, "")}${DEFAULT_ENGINEER_TASK_PATH}`;
}

function buildManagerUiError({
  title,
  endpoint,
  status,
  reason,
  missingField,
  source,
  suggestion,
  cause
} = {}) {
  const error = new Error(reason || title || "Manager API data error");
  error.uiTitle = title || "Manager API data error";
  error.uiEndpoint = endpoint || getManagerDashboardApiUrl() || "(not configured)";
  error.uiStatus = status ? String(status) : "";
  error.uiReason = reason || error.message || "Unknown error";
  error.uiMissingField = missingField || "";
  error.uiSource = source || "";
  error.uiSuggestion = suggestion || "Please check /api/manager/dashboard response payload.";
  error.cause = cause;
  return error;
}

function normalizeManagerUiError(error, defaults = {}) {
  if (error instanceof Error && error.uiTitle) {
    return error;
  }

  if (error instanceof Error) {
    return buildManagerUiError({
      title: defaults.title || "Manager API data error",
      endpoint: defaults.endpoint,
      status: defaults.status,
      reason: error.message || defaults.reason,
      missingField: defaults.missingField,
      source: defaults.source,
      suggestion: defaults.suggestion,
      cause: error
    });
  }

  return buildManagerUiError({
    title: defaults.title || "Manager API data error",
    endpoint: defaults.endpoint,
    status: defaults.status,
    reason: defaults.reason || String(error || "Unknown error"),
    missingField: defaults.missingField,
    source: defaults.source,
    suggestion: defaults.suggestion
  });
}
