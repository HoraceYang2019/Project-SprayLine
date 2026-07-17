// =======================================
// Engineer acknowledgement persistence and Apps Script sync helpers
// Split from the original dashboard.js to keep files focused and maintainable.
// =======================================
// =======================================
// Engineer Task Acknowledgement Frontend Module
// Engineer email button -> Manager Dashboard
// =======================================
window.engineerTaskMailSent = window.engineerTaskMailSent || {};

function saveEngineerTaskMailSentToLocalStorage(taskId, data) {
  const oldData = JSON.parse(localStorage.getItem("engineerTaskMailSent") || "{}");
  oldData[taskId] = data;
  localStorage.setItem("engineerTaskMailSent", JSON.stringify(oldData));
}

function loadEngineerTaskMailSentFromLocalStorage() {
  const saved = JSON.parse(localStorage.getItem("engineerTaskMailSent") || "{}");

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

  saveEngineerTaskMailSentToLocalStorage(taskId, window.engineerTaskMailSent[taskId]);
}

function isEngineerTaskMailSent(taskId) {
  if (!taskId) return false;

  return Boolean(
    window.engineerTaskMailSent &&
    window.engineerTaskMailSent[taskId] &&
    window.engineerTaskMailSent[taskId].sent
  );
}

function getEngineerTaskMailSentInfo(taskId) {
  if (!taskId) return null;

  return window.engineerTaskMailSent && window.engineerTaskMailSent[taskId]
    ? window.engineerTaskMailSent[taskId]
    : null;
}
window.engineerAcknowledgedTasks = window.engineerAcknowledgedTasks || {};

function readEngineerAckFromUrl() {
  const params = new URLSearchParams(window.location.search);

  console.log("[ACK DEBUG] current url:", window.location.href);
  console.log("[ACK DEBUG] ackTaskId:", params.get("ackTaskId"));

  const taskId = params.get("ackTaskId");
  if (!taskId) return;

  const ackAt = params.get("ackAt") || "";
  const ackBy = params.get("ackBy") || "工作站工程師";
  const ackEmail = params.get("ackEmail") || "";
  const station = params.get("station") || "";
  const batchId = params.get("batchId") || "";

  window.engineerAcknowledgedTasks[taskId] = {
    acknowledged: true,
    taskId,
    ackAt,
    ackBy,
    ackEmail,
    station,
    batchId
  };

  saveEngineerAckToLocalStorage(taskId, window.engineerAcknowledgedTasks[taskId]);

  showEngineerAckMessage(taskId, ackAt, ackBy);

  window.history.replaceState({}, document.title, window.location.pathname);

  if (typeof renderCockpit === "function") {
    renderCockpit();
  }
}

function saveEngineerAckToLocalStorage(taskId, data) {
  const oldData = JSON.parse(localStorage.getItem("engineerAcknowledgedTasks") || "{}");
  oldData[taskId] = data;
  localStorage.setItem("engineerAcknowledgedTasks", JSON.stringify(oldData));
}

function loadEngineerAckFromLocalStorage() {
  const saved = JSON.parse(localStorage.getItem("engineerAcknowledgedTasks") || "{}");

  window.engineerAcknowledgedTasks = {
    ...(window.engineerAcknowledgedTasks || {}),
    ...saved
  };
}

function isEngineerTaskAcknowledged(taskId) {
  if (!taskId) return false;

  return Boolean(
    window.engineerAcknowledgedTasks &&
    window.engineerAcknowledgedTasks[taskId] &&
    window.engineerAcknowledgedTasks[taskId].acknowledged
  );
}

function getEngineerAckInfo(taskId) {
  if (!taskId) return null;

  return window.engineerAcknowledgedTasks && window.engineerAcknowledgedTasks[taskId]
    ? window.engineerAcknowledgedTasks[taskId]
    : null;
}

function showEngineerAckMessage(taskId, ackAt, ackBy) {
  const oldToast = document.querySelector(".warning-confirm-toast");
  if (oldToast) oldToast.remove();

  const div = document.createElement("div");

  div.className = "warning-confirm-toast";
  div.style.position = "fixed";
  div.style.right = "24px";
  div.style.bottom = "24px";
  div.style.background = "#111827";
  div.style.color = "#ffffff";
  div.style.padding = "14px 18px";
  div.style.borderRadius = "14px";
  div.style.zIndex = "9999";
  div.style.boxShadow = "0 14px 30px rgba(0,0,0,0.25)";
  div.style.fontSize = "14px";
  div.style.lineHeight = "1.6";

  div.innerHTML =
    "<strong>工程師已收到任務</strong><br>" +
    "工程師: " + escapeHtmlFrontend(ackBy || "工作站工程師") + "<br>" +
    "Task ID: " + escapeHtmlFrontend(taskId) + "<br>" +
    "時間: " + escapeHtmlFrontend(ackAt || "-");

  document.body.appendChild(div);

  setTimeout(function () {
    div.remove();
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

document.addEventListener("DOMContentLoaded", function () {
  loadEngineerTaskMailSentFromLocalStorage();
  loadEngineerAckFromLocalStorage();
  readEngineerAckFromUrl();
});
function checkEngineerAckStatusFromAppsScript(taskId) {
  if (!taskId || !CONFIG.WARNING_APP_SCRIPT_URL) {
    return Promise.resolve(null);
  }

  return new Promise((resolve, reject) => {
    const callbackName = "engineerAckCallback_" + Date.now() + "_" + Math.floor(Math.random() * 100000);

    window[callbackName] = function (result) {
      delete window[callbackName];

      if (script && script.parentNode) {
        script.parentNode.removeChild(script);
      }

      resolve(result);
    };

    const script = document.createElement("script");
    const url =
      CONFIG.WARNING_APP_SCRIPT_URL +
      "?action=ack_status_jsonp" +
      "&taskId=" + encodeURIComponent(taskId) +
      "&callback=" + encodeURIComponent(callbackName) +
      "&ts=" + Date.now();

    script.src = url;

    script.onerror = function () {
      delete window[callbackName];

      if (script && script.parentNode) {
        script.parentNode.removeChild(script);
      }

      reject(new Error("Failed to load engineer ack status JSONP."));
    };

    document.body.appendChild(script);
  });
}
async function syncEngineerAckStatusForCurrentAssignments() {
  const assignments = CURRENT_RECOMMENDATION_ASSIGNMENTS || [];

  for (const assignment of assignments) {
    const taskId = buildAssignmentTaskId(assignment);

    if (!taskId) continue;
    if (isEngineerTaskAcknowledged(taskId)) continue;

    try {
      const result = await checkEngineerAckStatusFromAppsScript(taskId);

      if (result && result.acknowledged) {
        window.engineerAcknowledgedTasks[taskId] = {
          acknowledged: true,
          taskId: result.taskId || taskId,
          warningId: result.warningId || taskId,
          ackAt: result.ackAt || "",
          ackBy: result.ackBy || assignment.owner || "工作站工程師",
          ackEmail: result.ackEmail || assignment.email || "",
          source: result.source || "apps_script"
        };

        saveEngineerAckToLocalStorage(taskId, window.engineerAcknowledgedTasks[taskId]);

        console.log("[ACK SYNC] Engineer acknowledged:", taskId, result);
      }
    } catch (error) {
      console.warn("[ACK SYNC] Failed:", taskId, error);
    }
  }

  if (typeof renderCockpit === "function") {
    renderCockpit();
  }
}
function checkEngineerAckStatusFromAppsScript(taskId) {
  if (!taskId || !CONFIG.WARNING_APP_SCRIPT_URL) {
    return Promise.resolve(null);
  }

  return new Promise((resolve, reject) => {
    const callbackName =
      "engineerAckCallback_" + Date.now() + "_" + Math.floor(Math.random() * 100000);

    let script = document.createElement("script");

    window[callbackName] = function (result) {
      delete window[callbackName];

      if (script && script.parentNode) {
        script.parentNode.removeChild(script);
      }

      resolve(result);
    };

    script.onerror = function () {
      delete window[callbackName];

      if (script && script.parentNode) {
        script.parentNode.removeChild(script);
      }

      reject(new Error("Failed to load engineer ack status JSONP."));
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
  if (!taskId || !result || !result.acknowledged) return;

  if (!window.engineerAcknowledgedTasks) {
    window.engineerAcknowledgedTasks = {};
  }

  const ackData = {
    acknowledged: true,
    taskId: result.taskId || taskId,
    warningId: result.warningId || taskId,
    ackAt: result.ackAt || "",
    ackBy: result.ackBy || "工作站工程師",
    ackEmail: result.ackEmail || "",
    source: result.source || "apps_script"
  };

  window.engineerAcknowledgedTasks[taskId] = ackData;

  if (typeof saveEngineerAckToLocalStorage === "function") {
    saveEngineerAckToLocalStorage(taskId, ackData);
  } else {
    localStorage.setItem(
      "engineerAcknowledgedTasks",
      JSON.stringify(window.engineerAcknowledgedTasks)
    );
  }

  console.log("[ACK SYNC] Engineer acknowledged:", taskId, ackData);
}
async function syncEngineerAckStatusForSentTasks() {
  const taskIds = new Set();

  // 目前畫面上的任務
  if (Array.isArray(CURRENT_RECOMMENDATION_ASSIGNMENTS)) {
    CURRENT_RECOMMENDATION_ASSIGNMENTS.forEach((assignment) => {
      const taskId = buildAssignmentTaskId(assignment);
      if (taskId) taskIds.add(taskId);
    });
  }

  // 已寄出的任務
  try {
    const sentTasks = JSON.parse(localStorage.getItem("engineerTaskMailSent") || "{}");
    Object.keys(sentTasks).forEach((taskId) => {
      if (taskId) taskIds.add(taskId);
    });
  } catch (error) {
    console.warn("[ACK SYNC] Failed to read engineerTaskMailSent:", error);
  }

  for (const taskId of taskIds) {
    if (isEngineerTaskAcknowledged(taskId)) {
      continue;
    }

    try {
      const result = await checkEngineerAckStatusFromAppsScript(taskId);

      console.log("[ACK SYNC] result:", taskId, result);

      if (result && result.acknowledged) {
        markEngineerAckFromAppsScript(taskId, result);
      }
    } catch (error) {
      console.warn("[ACK SYNC] failed:", taskId, error);
    }
  }

  if (typeof renderCockpit === "function") {
    renderCockpit();
  }
}
