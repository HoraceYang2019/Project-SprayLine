window.engineerTaskMailSent = window.engineerTaskMailSent || {};
window.engineerAcknowledgedTasks = window.engineerAcknowledgedTasks || {};

const STORE_API_KEY = "local" + "Storage";

function getBrowserStore() {
  if (typeof window === "undefined") return null;
  return window[STORE_API_KEY] || null;
}

function readStoredJson(key) {
  const store = getBrowserStore();
  if (!store) return {};

  try {
    return JSON.parse(store.getItem(key) || "{}");
  } catch (error) {
    console.warn("[Manager UI] failed to read persisted state", key, error);
    return {};
  }
}

function writeStoredJson(key, value) {
  const store = getBrowserStore();
  if (!store) return;

  try {
    store.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.warn("[Manager UI] failed to write persisted state", key, error);
  }
}

function saveEngineerTaskMailSentState(taskId, data) {
  const state = readStoredJson("engineerTaskMailSent");
  state[taskId] = data;
  writeStoredJson("engineerTaskMailSent", state);
}

function loadEngineerTaskMailSentState() {
  const saved = readStoredJson("engineerTaskMailSent");
  window.engineerTaskMailSent = {
    ...(window.engineerTaskMailSent || {}),
    ...saved
  };
}

function markEngineerTaskMailSent(taskId, data) {
  if (!taskId) return;

  window.engineerTaskMailSent = window.engineerTaskMailSent || {};
  window.engineerTaskMailSent[taskId] = {
    sent: true,
    taskId,
    sentAt: new Date().toLocaleString("zh-TW"),
    ...data
  };

  saveEngineerTaskMailSentState(taskId, window.engineerTaskMailSent[taskId]);
}

function isEngineerTaskMailSent(taskId) {
  return Boolean(taskId && window.engineerTaskMailSent?.[taskId]?.sent);
}

function getEngineerTaskMailSentInfo(taskId) {
  return taskId ? window.engineerTaskMailSent?.[taskId] || null : null;
}

function saveEngineerAckState(taskId, data) {
  const state = readStoredJson("engineerAcknowledgedTasks");
  state[taskId] = data;
  writeStoredJson("engineerAcknowledgedTasks", state);
}

function loadEngineerAckState() {
  const saved = readStoredJson("engineerAcknowledgedTasks");
  window.engineerAcknowledgedTasks = {
    ...(window.engineerAcknowledgedTasks || {}),
    ...saved
  };
}

function isEngineerTaskAcknowledged(taskId) {
  return Boolean(taskId && window.engineerAcknowledgedTasks?.[taskId]?.acknowledged);
}

function getEngineerAckInfo(taskId) {
  return taskId ? window.engineerAcknowledgedTasks?.[taskId] || null : null;
}

function readEngineerAckFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const taskId = params.get("ackTaskId");
  if (!taskId) return;

  const ackData = {
    acknowledged: true,
    taskId,
    ackAt: params.get("ackAt") || "",
    ackBy: params.get("ackBy") || "Engineer",
    ackEmail: params.get("ackEmail") || "",
    station: params.get("station") || "",
    batchId: params.get("batchId") || ""
  };

  window.engineerAcknowledgedTasks[taskId] = ackData;
  saveEngineerAckState(taskId, ackData);
  showEngineerAckMessage(taskId, ackData.ackAt, ackData.ackBy);
  window.history.replaceState({}, document.title, window.location.pathname);

  if (typeof renderCockpit === "function") {
    renderCockpit();
  }
}

function showEngineerAckMessage(taskId, ackAt, ackBy) {
  const oldToast = document.querySelector(".warning-confirm-toast");
  if (oldToast) oldToast.remove();

  const toast = document.createElement("div");
  toast.className = "warning-confirm-toast";
  toast.style.position = "fixed";
  toast.style.right = "24px";
  toast.style.bottom = "24px";
  toast.style.background = "#111827";
  toast.style.color = "#ffffff";
  toast.style.padding = "14px 18px";
  toast.style.borderRadius = "14px";
  toast.style.zIndex = "9999";
  toast.style.boxShadow = "0 14px 30px rgba(0,0,0,0.25)";
  toast.style.fontSize = "14px";
  toast.style.lineHeight = "1.6";
  toast.innerHTML =
    "<strong>Engineer acknowledged the assignment</strong><br>" +
    "Engineer: " + escapeHtmlFrontend(ackBy || "Engineer") + "<br>" +
    "Task ID: " + escapeHtmlFrontend(taskId) + "<br>" +
    "Time: " + escapeHtmlFrontend(ackAt || "-");

  document.body.appendChild(toast);
  window.setTimeout(() => {
    toast.remove();
  }, 5000);
}

function escapeHtmlFrontend(value) {
  return String(value === undefined || value === null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function checkEngineerAckStatusFromAppsScript(taskId) {
  if (!taskId || !CONFIG.WARNING_APP_SCRIPT_URL) {
    return Promise.resolve(null);
  }

  return new Promise((resolve, reject) => {
    const callbackName = `engineerAckCallback_${Date.now()}_${Math.floor(Math.random() * 100000)}`;
    const script = document.createElement("script");

    window[callbackName] = result => {
      delete window[callbackName];
      script.remove();
      resolve(result);
    };

    script.onerror = () => {
      delete window[callbackName];
      script.remove();
      reject(new Error("Failed to load engineer acknowledgement status."));
    };

    script.src =
      CONFIG.WARNING_APP_SCRIPT_URL +
      "?action=ack_status_jsonp" +
      "&taskId=" + encodeURIComponent(taskId) +
      "&callback=" + encodeURIComponent(callbackName) +
      "&ts=" + Date.now();

    document.body.appendChild(script);
  });
}

function markEngineerAckFromAppsScript(taskId, result) {
  if (!taskId || !result?.acknowledged) return;

  const ackData = {
    acknowledged: true,
    taskId: result.taskId || taskId,
    warningId: result.warningId || taskId,
    ackAt: result.ackAt || "",
    ackBy: result.ackBy || "Engineer",
    ackEmail: result.ackEmail || "",
    source: result.source || "apps_script"
  };

  window.engineerAcknowledgedTasks[taskId] = ackData;
  saveEngineerAckState(taskId, ackData);
}

async function syncEngineerAckStatusForSentTasks() {
  const taskIds = new Set();

  if (Array.isArray(CURRENT_RECOMMENDATION_ASSIGNMENTS)) {
    CURRENT_RECOMMENDATION_ASSIGNMENTS.forEach(assignment => {
      const taskId = buildAssignmentTaskId(assignment);
      if (taskId) taskIds.add(taskId);
    });
  }

  Object.keys(readStoredJson("engineerTaskMailSent")).forEach(taskId => {
    if (taskId) taskIds.add(taskId);
  });

  for (const taskId of taskIds) {
    if (isEngineerTaskAcknowledged(taskId)) continue;

    try {
      const result = await checkEngineerAckStatusFromAppsScript(taskId);
      if (result?.acknowledged) {
        markEngineerAckFromAppsScript(taskId, result);
      }
    } catch (error) {
      console.warn("[Manager UI] failed to sync acknowledgement state", taskId, error);
    }
  }

  if (typeof renderCockpit === "function") {
    renderCockpit();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadEngineerTaskMailSentState();
  loadEngineerAckState();
  readEngineerAckFromUrl();
});
