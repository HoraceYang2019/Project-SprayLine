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

async function sendEngineerWarningEmail(index) {
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
