function renderRecommendationSection() {
  const section = document.getElementById("managerRecommendationSection");
  if (!section || !MANAGER_SUMMARY) return;

  const recommendations = getRecommendationItems();
  CURRENT_RECOMMENDATION_ASSIGNMENTS = recommendations;

  if (!recommendations.length) {
    section.innerHTML = `
      <section class="manager-section">
        <div class="manager-section-head">
          <div>
            <p class="section-kicker">處理建議</p>
            <h2>目前無需處理事項</h2>
          </div>
        </div>
      </section>
    `;
    return;
  }

  section.innerHTML = `
    <section class="manager-section">
      <div class="manager-section-head">
        <div>
          <p class="section-kicker">處理建議</p>
          <h2>需要處理的項目</h2>
        </div>
      </div>
      <div class="recommendation-list">
        ${recommendations.map((item, index) => renderRecommendationCard(item, index)).join("")}
      </div>
    </section>
  `;
}

function renderRecommendationCard(item, index) {
  const existingTask = typeof getCachedEngineerTaskForRecommendation === "function"
    ? getCachedEngineerTaskForRecommendation(item)
    : null;
  const isAcknowledged = existingTask?.deliveryStatus === "acknowledged";
  const isSent = existingTask?.deliveryStatus === "sent";
  const buttonLabel = isAcknowledged ? "工程師已確認" : (isSent ? "通知已送出" : "發送通知");
  return `
    <article class="recommendation-card ${escapeHtml(levelClass(item.level))}">
      <div class="recommendation-card-head">
        <div>
          <h3>${escapeHtml(item.stationName || "-")} / ${escapeHtml(item.processName || "-")}</h3>
          <p class="recommendation-issue">問題：${escapeHtml(item.mainIssue || "-")}</p>
        </div>
        <span class="issue-chip ${escapeHtml(levelClass(item.level))}">${escapeHtml(formatLevelLabel(item.level))}</span>
      </div>
      <p class="recommendation-text">建議：${escapeHtml(item.recommendation || "-")}</p>
      <div class="recommendation-actions">
        <button
          type="button"
          class="notify-btn"
          data-recommendation-index="${index}"
          ${(isSent || isAcknowledged) ? "disabled" : ""}
        >
          ${buttonLabel}
        </button>
      </div>
    </article>
  `;
}

function buildEngineerWarningPayload(recommendation) {
  const dateText = selectedReportDate || getResponseDateKeyFromDb(currentDatabaseResponse) || "-";
  const hourText = formatHourRangeLabel(selectedReportHour ?? getResponseHourFromDb(currentDatabaseResponse));
  const batchText = selectedBatchId || MANAGER_SUMMARY?.batchSelector?.defaultModeLabel || "全部批號 / 該小時累計";
  const stationText = `${recommendation.stationName || "-"} / ${recommendation.processName || "-"}`;
  const messageText = [
    `Date：${dateText}`,
    `Hour：${hourText}`,
    `Batch：${batchText}`,
    `Station：${stationText}`,
    `問題：${recommendation.mainIssue || "-"}`,
    `建議：${recommendation.recommendation || "-"}`
  ].join("\n");

  return {
    sourceAlertEventId: recommendation.sourceAlertEventId || null,
    stationId: recommendation.stationId || "",
    stationName: recommendation.stationName || "",
    processName: recommendation.processName || "",
    batchId: selectedBatchId || null,
    batchLabel: batchText,
    dataDate: dateText,
    dataHour: hourText,
    level: recommendation.level || "warning",
    issue: recommendation.mainIssue || "",
    recommendation: recommendation.recommendation || "",
    engineerName: recommendation.engineerName || "",
    engineerEmail: recommendation.engineerEmail || "",
    messageText
  };
}

function showManagerToast(message) {
  const host = document.getElementById("managerToastHost");
  if (!host) return;

  const toast = document.createElement("div");
  toast.className = "manager-toast";
  toast.textContent = message;
  host.appendChild(toast);

  window.setTimeout(() => {
    toast.classList.add("fade-out");
  }, 2200);

  window.setTimeout(() => {
    toast.remove();
  }, 2800);
}

let pendingRecommendationIndex = null;

async function sendEngineerWarningEmail(index) {
  const recommendation = CURRENT_RECOMMENDATION_ASSIGNMENTS[index];
  if (!recommendation) return;

  try {
    const base = String(CONFIG.MANAGER_API_BASE_URL).replace(/\/$/, "");
    const assignments = await managerApiRequest(`${base}/api/manager/station-engineer-assignments?station_id=${encodeURIComponent(recommendation.stationId)}&active_only=true`);
    if (Array.isArray(assignments) && assignments.length) {
      pendingRecommendationIndex = index;
      document.getElementById("assignmentDialogStation").textContent = `${recommendation.stationName} / ${recommendation.processName}`;
      document.getElementById("assignmentChoices").innerHTML = assignments.map((item, itemIndex) => `
        <label class="assignment-choice">
          <span><input type="checkbox" name="selectedEngineer" value="${escapeHtml(item.assignmentId)}" ${itemIndex === 0 ? "checked" : ""}> ${escapeHtml(item.engineerName)}<small>${escapeHtml(item.engineerEmail)}</small></span>
          <span><input type="radio" name="primaryEngineer" value="${escapeHtml(item.assignmentId)}" ${itemIndex === 0 ? "checked" : ""}> Primary</span>
          <span><input type="checkbox" name="requiredEngineer" value="${escapeHtml(item.assignmentId)}" ${itemIndex === 0 ? "checked" : ""}> 必要參與</span>
        </label>`).join("");
      const dialog = document.getElementById("assignmentDialog");
      dialog.dataset.assignments = JSON.stringify(assignments);
      dialog.showModal();
      return;
    }
  } catch (error) {
    console.warn("[Manager UI] station assignment unavailable", error);
  }

  if (!recommendation.engineerEmail || !window.confirm("此站尚無正式工程師指派。是否使用舊 Email fallback？")) return;
  await sendLegacyEngineerWarning(index);
}

async function sendLegacyEngineerWarning(index) {
  const recommendation = CURRENT_RECOMMENDATION_ASSIGNMENTS[index];
  if (!recommendation) return;

  const button = document.querySelector(`[data-recommendation-index="${index}"]`);
  const resetKey = `${recommendation.stationId || "station"}:${recommendation.mainIssue || "issue"}:${index}`;
  clearNotificationResetTimer(resetKey);

  try {
    if (button) {
      button.disabled = true;
      button.textContent = "送出中...";
    }

    const task = await createEngineerTask(buildEngineerWarningPayload(recommendation));
    markEngineerTaskMailSent(task.taskId, task);

    if (button) {
      button.textContent = "已送出";
    }
    showManagerToast(`通知已送出（Task ${task.taskId}）`);

    notificationButtonResetTimers[resetKey] = window.setTimeout(() => {
      if (button) {
        button.disabled = false;
        button.textContent = "發送通知";
      }
      clearNotificationResetTimer(resetKey);
    }, 3000);
  } catch (error) {
    console.error("[Manager UI] engineer notification failed", error);
    if (button) {
      button.disabled = false;
      button.textContent = "發送通知";
    }
    showManagerToast(`通知送出失敗：${error.uiReason || error.message || "未知錯誤"}`);
  }
}

async function submitAssignmentSelection(event) {
  event.preventDefault();
  const dialog = document.getElementById("assignmentDialog");
  const assignments = JSON.parse(dialog.dataset.assignments || "[]");
  const selected = new Set([...document.querySelectorAll('[name="selectedEngineer"]:checked')].map(item => item.value));
  const primary = document.querySelector('[name="primaryEngineer"]:checked')?.value;
  const required = new Set([...document.querySelectorAll('[name="requiredEngineer"]:checked')].map(item => item.value));
  if (!selected.size || !primary || !selected.has(primary)) {
    showManagerToast("Primary 必須是已選取的工程師");
    return;
  }
  required.add(primary);
  const recommendation = CURRENT_RECOMMENDATION_ASSIGNMENTS[pendingRecommendationIndex];
  const payload = buildEngineerWarningPayload(recommendation);
  delete payload.engineerName;
  delete payload.engineerEmail;
  payload.assignees = assignments.filter(item => selected.has(item.assignmentId)).map(item => ({
    stationAssignmentId: item.assignmentId,
    engineerName: item.engineerName,
    engineerEmail: item.engineerEmail,
    isPrimary: item.assignmentId === primary,
    isRequiredParticipant: required.has(item.assignmentId)
  }));
  const button = document.querySelector(`[data-recommendation-index="${pendingRecommendationIndex}"]`);
  try {
    if (button) { button.disabled = true; button.textContent = "送出中..."; }
    const task = await createEngineerTask(payload);
    markEngineerTaskMailSent(task.taskId, task);
    dialog.close();
    if (button) button.textContent = "通知已送出";
    showManagerToast(`已建立多人任務（Task ${task.taskId}）`);
  } catch (error) {
    if (button) { button.disabled = false; button.textContent = "發送通知"; }
    showManagerToast(`通知失敗：${error.uiReason || error.message}`);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("confirmAssignment")?.addEventListener("click", submitAssignmentSelection);
});
