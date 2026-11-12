window.engineerTaskMailSent = window.engineerTaskMailSent || {};
window.engineerAcknowledgedTasks = window.engineerAcknowledgedTasks || {};

const ENGINEER_TASK_CACHE_KEY = "engineerTaskMailSent";

function readEngineerTaskCache() {
  try {
    return JSON.parse(window.localStorage?.getItem(ENGINEER_TASK_CACHE_KEY) || "{}");
  } catch (error) {
    console.warn("[Manager UI] failed to read engineer task cache", error);
    return {};
  }
}

function writeEngineerTaskCache(value) {
  try {
    window.localStorage?.setItem(ENGINEER_TASK_CACHE_KEY, JSON.stringify(value));
  } catch (error) {
    console.warn("[Manager UI] failed to write engineer task cache", error);
  }
}

function markEngineerTaskMailSent(taskId, task) {
  if (!taskId) return;
  window.engineerTaskMailSent[taskId] = { sent: true, ...task };
  writeEngineerTaskCache(window.engineerTaskMailSent);
}

function cacheEngineerTask(task) {
  if (!task?.taskId) return;
  window.engineerTaskMailSent[task.taskId] = {
    sent: ["sent", "acknowledged"].includes(task.deliveryStatus),
    ...task
  };
  if (task.deliveryStatus === "acknowledged") {
    window.engineerAcknowledgedTasks[task.taskId] = task;
  }
}

function getCachedEngineerTaskForRecommendation(recommendation) {
  const currentHour = formatHourRangeLabel(selectedReportHour ?? getResponseHourFromDb(currentDatabaseResponse));
  const tasks = Object.values(window.engineerTaskMailSent || {}).sort((left, right) =>
    String(right.createdAt || "").localeCompare(String(left.createdAt || ""))
  );
  return tasks.find(task =>
    task.stationId === recommendation.stationId &&
    task.issue === recommendation.mainIssue &&
    (!task.dataDate || task.dataDate === selectedReportDate) &&
    (!task.dataHour || task.dataHour === currentHour) &&
    (!task.batchId || task.batchId === selectedBatchId)
  ) || null;
}

async function syncEngineerAckStatusForSentTasks() {
  const result = await getEngineerTasks({ limit: 100 });
  const tasks = Array.isArray(result?.items) ? result.items : [];
  window.engineerTaskMailSent = {};
  window.engineerAcknowledgedTasks = {};

  for (const task of tasks) {
    cacheEngineerTask(task);
    if (task.deliveryStatus !== "sent") continue;
    try {
      cacheEngineerTask(await syncEngineerTaskAck(task.taskId));
    } catch (error) {
      console.warn("[Manager UI] failed to sync acknowledgement state", task.taskId, error);
    }
  }
  writeEngineerTaskCache(window.engineerTaskMailSent);
  if (typeof renderCockpit === "function") renderCockpit();
}

document.addEventListener("DOMContentLoaded", () => {
  window.engineerTaskMailSent = {
    ...window.engineerTaskMailSent,
    ...readEngineerTaskCache()
  };
  syncEngineerAckStatusForSentTasks().catch(error => {
    console.warn("[Manager UI] failed to load engineer task state", error);
  });
});
