// =======================================
// Recommendation rendering, notification payloads, and assignment interactions
// Split from the original dashboard.js to keep files focused and maintainable.
// =======================================
function buildRecommendationAssignmentsFromCurrentData(summary) {
  const qualityMode = getCurrentQualityScoreMode();
  const diagnosis = buildRealtimeDiagnosis(summary);
  const dateLabel = formatDateLabel(getResponseDateKeyFromDb(currentDatabaseResponse || summary.rawDatabaseResponse));
  const hourLabel = `${String(getCurrentDataHour()).padStart(2, "0")}:00`;
  const reviewPrefix = selectedReportHourMode === "live" ? "目前資料" : "回顧資料";

  if (!diagnosis.main || !diagnosis.stationDiagnoses.length) return [];

  return diagnosis.stationDiagnoses.map((diagnosisItem, index) => {
    const issue = diagnosisItem.topIssue;
    const responsibility = diagnosisItem.responsibility;
    const station = diagnosisItem.station;
    const metrics = station.metrics || {};
    const baseline = station.baseline || {};
    const isMain = index === 0;
    const issueList = diagnosisItem.issues.map(item => item.direction).join("、");

    return {
      priority: `P${index + 1}`,
      owner: responsibility.engineerRole,
      station: responsibility.stationName,
      processLayer: responsibility.layerName,
      email: responsibility.engineerEmail,
      lineId: station.lineId,
      level: issue.level,
      issueDirection: issue.direction,
      issue: `${dateLabel} ${hourLabel} ${responsibility.stationName} / ${responsibility.layerName}：${issue.direction}`,
      evidence: issue.evidence,
      impact: issue.impact,
      task: isMain
        ? `${reviewPrefix}顯示 ${issue.direction}。${issue.action}`
        : `${reviewPrefix}顯示同時有異常。同步確認 ${responsibility.stationName}${responsibility.layerName} 的 ${issueList || issue.direction}。`,
      due: selectedReportHourMode === "live" ? "下一次資料更新前" : "回查該小時維修 / 清槍 / 換濾網紀錄後回報",
      status: isMain ? (issue.level === "緊急" ? "立即處理" : "優先確認") : "同步確認",
      acceptance: `${responsibility.stationName}${responsibility.layerName} 在該小時後的${qualityMode.scoreLabel}、堵塞率、噴幅、稼動率與 Cycle Time 沒有再惡化。`,
      riskScore: diagnosisItem.evaluation.riskScore,
      stationMetrics: {
        quality_score_pct: metrics.quality_score_pct,
        clog_rate_pct: metrics.clog_rate_pct,
        spray_width_mm: metrics.spray_width_mm,
        pressure_bar: metrics.pressure_bar,
        flow_rate_ml_min: metrics.flow_rate_ml_min,
        utilization_pct: metrics.utilization_pct,
        cycle_time_sec: metrics.cycle_time_sec,
        baseline_quality_score_pct: baseline.quality_score_pct,
        baseline_flow_rate_ml_min: baseline.flow_rate_ml_min,
        baseline_utilization_pct: baseline.utilization_pct,
        baseline_cycle_time_sec: baseline.cycle_time_sec
      },
      allIssueDirections: issueList
    };
  });
}



function getCurrentBatchInfo(summary, assignment) {
  const db = summary?.rawDatabaseResponse || currentDatabaseResponse || {};
  const production = db.productionKpi || {};
  const currentPeriod = production.currentPeriod || {};
  const candidates = [
    db.currentBatch,
    production.currentBatch,
    currentPeriod.currentBatch,
    currentPeriod.batch,
    currentPeriod
  ].filter(Boolean);

  const found = candidates.find(item =>
    item.batchId || item.batch_id || item.batchNo || item.batch_no || item.lotId || item.lot_no
  ) || {};

  const dateKey = getResponseDateKeyFromDb(db);
  const hour = getCurrentDataHour();
  const lineId = assignment?.lineId || summary?.mainIssueLineId || "line_all";
  const fallbackSeq = Math.floor(Number(hour || 0) / 2) + 1;
  const fallbackBatchId = `B${String(dateKey || getActiveApiDateKey()).replace(/-/g, "")}-${String(fallbackSeq).padStart(3, "0")}-${String(lineId).replace("line_", "S").toUpperCase()}`;
  const history = db.qualityHistory || [];
  const historyBatchSizes = history
    .map(row => Number(row.okPcs || 0) + Number(row.ngPcs || 0))
    .filter(value => value > 0);
  const fallbackBatchSize = currentPeriod.plannedPcs
    ? Math.max(300, Math.round(Number(currentPeriod.plannedPcs) / 18))
    : Math.round(historyBatchSizes.length ? average(historyBatchSizes) : 720);

  const plannedPcs = Number(
    found.plannedPcs ??
    found.planned_pcs ??
    found.batchPcs ??
    found.batch_pcs ??
    found.totalPcs ??
    found.total_pcs ??
    found.qty ??
    found.quantity ??
    fallbackBatchSize
  );

  return {
    batchId: String(found.batchId || found.batch_id || found.batchNo || found.batch_no || found.lotId || found.lot_no || fallbackBatchId),
    workOrderId: String(found.workOrderId || found.work_order_id || found.workOrder || found.wo || `WO-${String(dateKey || getActiveApiDateKey()).replace(/-/g, "")}-${String(fallbackSeq).padStart(3, "0")}`),
    partNo: String(found.partNo || found.part_no || found.partType || found.part_type || "Cover-A"),
    colorCode: String(found.colorCode || found.color_code || found.colorId || found.color_id || "White"),
    recipeId: String(found.recipeId || found.recipe_id || assignment?.stationMetrics?.recipeId || "依當前 API 配方"),
    batchWindow: String(found.batchWindow || found.batch_window || found.timeWindow || found.time_window || `${String(Math.floor(hour / 2) * 2).padStart(2, "0")}:00-${String(Math.min(23, Math.floor(hour / 2) * 2 + 1)).padStart(2, "0")}:59`),
    plannedPcs: Number.isFinite(plannedPcs) && plannedPcs > 0 ? Math.round(plannedPcs) : fallbackBatchSize,
    producedPcsToCurrent: Number(found.producedPcsToCurrent || found.produced_pcs_to_current || found.producedPcs || found.produced_pcs || 0),
    hourlyBatchCount: Number(found.hourlyBatchCount || found.hourly_batch_count || found.batchCountInHour || found.batch_count_in_hour || 1),
    qualityScoreSource: String(found.qualityScoreSource || found.quality_score_source || "hourly_all_batches_average"),
    isPendingQc: found.isPendingQc ?? found.is_pending_qc ?? true,
    source: found.source || "current API / DB batch snapshot"
  };
}

function buildNoActionImpactForecast(assignment, summary) {
  const qualityMode = getCurrentQualityScoreMode();
  const metrics = assignment?.stationMetrics || summary.mainStationMetrics || {};
  const batchInfo = getCurrentBatchInfo(summary, assignment);
  const batchPcs = Math.max(1, Math.round(Number(batchInfo.plannedPcs || 0)));

  const qualityScore = Number(metrics.quality_score_pct ?? summary.predictedOkRate ?? 92);
  const managementOkRate = 92;
  const predictedNgPcs = Math.max(0, Math.round(batchPcs * (100 - qualityScore) / 100));
  const acceptableNgPcs = Math.max(0, Math.round(batchPcs * (100 - managementOkRate) / 100));
  const extraNgPcs = Math.max(0, predictedNgPcs - acceptableNgPcs);

  const util = Number(metrics.utilization_pct ?? summary.utilization ?? 0);
  const baseUtil = Number(metrics.baseline_utilization_pct ?? summary.lastWeekUtilization ?? util);
  const cycle = Number(metrics.cycle_time_sec ?? 0);
  const baseCycle = Number(metrics.baseline_cycle_time_sec ?? cycle);
  const utilizationLossRate = Math.max(0, baseUtil - util) / 100;
  const cycleLossRate = baseCycle > 0 ? Math.max(0, cycle - baseCycle) / baseCycle : 0;
  const productionLossPcs = Math.max(0, Math.round(batchPcs * Math.max(utilizationLossRate, cycleLossRate) * 0.75));
  const totalLossPcs = predictedNgPcs + productionLossPcs;

  const severityScore = extraNgPcs * 1.8 + productionLossPcs + Math.max(0, 92 - qualityScore) * 8;
  const severity = severityScore >= 120 ? "高" : severityScore >= 55 ? "中" : "低";
  const severityText = severity === "高"
    ? `若放著不處理，${batchInfo.batchId} 很可能變成主管需要立即追蹤的品質與產能損失。`
    : severity === "中"
      ? `若下一小時沒有改善，建議主管要求工程師回查 ${batchInfo.batchId} 並留下處理紀錄。`
      : `目前屬於早期風險，但仍要回查 ${batchInfo.batchId} 是否為短暫異常或前兆。`;

  return {
    batchInfo,
    batchId: batchInfo.batchId,
    workOrderId: batchInfo.workOrderId,
    batchPcs,
    predictedNgPcs,
    acceptableNgPcs,
    extraNgPcs,
    productionLossPcs,
    totalLossPcs,
    severity,
    severityText,
    qualityScore,
    qualityMode
  };
}

function renderNoActionImpactAlert(assignment, summary, dateLabel, hourLabel) {
  const impact = buildNoActionImpactForecast(assignment, summary);
  const batch = impact.batchInfo;
  const qualityMode = impact.qualityMode;
  return `
    <div class="future-risk-alert no-action-impact-alert">
      <div class="no-action-impact-head">
        <span>不處理可能後果</span>
        <strong>嚴重性：${escapeHtml(impact.severity)}</strong>
      </div>
      <p>
        ${escapeHtml(dateLabel)} ${escapeHtml(hourLabel)} 目前收到的 batch 是
        <strong>${escapeHtml(batch.batchId)}</strong>（工單 ${escapeHtml(batch.workOrderId)}，${escapeHtml(batch.partNo)} / ${escapeHtml(batch.colorCode)}）。
        若不處理「${escapeHtml(assignment.issueDirection)}」，此 batch 後續可能出現 NG 增加與產出損失。
        ${escapeHtml(qualityMode.isPredicted ? "當天品質分數仍是預測值；隔天 QC 完成後會重新從 DB qc_result 取得實際品質分數，不會沿用這筆預測結果。" : "此日期已完成 QC，品質分數由 DB qc_result 實際資料取得，可作為回顧依據。")}
      </p>
      <div class="no-action-impact-grid">
        <div>
          <span>受影響 batch ID</span>
          <strong>${escapeHtml(batch.batchId)}</strong>
        </div>
        <div>
          <span>該 batch 總數</span>
          <strong>${escapeHtml(formatNumber(impact.batchPcs))} pcs</strong>
        </div>
        <div>
          <span>${escapeHtml(qualityMode.isPredicted ? "預測可能 NG" : "估測目前 NG")}</span>
          <strong>${escapeHtml(formatNumber(impact.predictedNgPcs))} pcs</strong>
        </div>
        <div>
          <span>額外 NG</span>
          <strong>+${escapeHtml(formatNumber(impact.extraNgPcs))} pcs</strong>
        </div>
        <div>
          <span>產出損失</span>
          <strong>-${escapeHtml(formatNumber(impact.productionLossPcs))} pcs</strong>
        </div>
        <div>
          <span>${escapeHtml(qualityMode.hourlyAverageLabel)}</span>
          <strong>${escapeHtml(formatPercent(impact.qualityScore))}</strong>
        </div>
      </div>
      <div class="no-action-impact-total">
        <span>主管判斷用總風險</span>
        <strong>${escapeHtml(formatNumber(impact.totalLossPcs))} pcs 可能受影響</strong>
      </div>
      <p class="no-action-impact-note">
        ${escapeHtml(impact.severityText)} 計算基準：目前 API / DB 回傳的 batch ID、batch 數量、品質管理線 92%，以及選定小時「所有 batch 的${qualityMode.scoreLabel}平均值」、稼動率與 Cycle Time。該小時共 ${escapeHtml(formatNumber(batch.hourlyBatchCount || 1))} 個 batch 參與平均。${escapeHtml(qualityMode.isPredicted ? "隔天實際品質會另外查 DB qc_result，不使用當天預測存檔。" : "目前顯示的是 DB qc_result 實際品質，不是當天預測存檔。")}
      </p>
    </div>
  `;
}

function buildRecommendationNoActionBlock(summary) {
  const dateLabel = formatDateLabel(getResponseDateKeyFromDb(currentDatabaseResponse || summary.rawDatabaseResponse));
  const hourLabel = `${String(getCurrentDataHour()).padStart(2, "0")}:00`;
  return `
    <div class="recommendation-summary-row normal-recommendation-row">
      <div>
        <strong>${escapeHtml(dateLabel)} ${escapeHtml(hourLabel)} 目前沒有異常任務分派</strong>
        <p>該小時資料未觸發 warning / emergency。工程師面板不顯示固定分派，避免主管誤判。</p>
      </div>
      <div class="recommendation-summary-count">0 項</div>
    </div>
    <div class="data-reminder">
      若要回查曾經出現問題的小時，請使用上方「資料時間」下拉選單選擇淺紅閃爍的小時。
    </div>
  `;
}

function renderRecommendationPanel() {
  const qualityMode = getCurrentQualityScoreMode();
  const summary = MANAGER_MOCK_SUMMARY;
  const level = getOperationLevel(summary);
  const panel = document.getElementById("recommendationPanel");
  const assignments = buildRecommendationAssignmentsFromCurrentData(summary);
  CURRENT_RECOMMENDATION_ASSIGNMENTS = assignments;
  const mainAssignment = assignments[0] || null;
  const dateLabel = formatDateLabel(getResponseDateKeyFromDb(currentDatabaseResponse || summary.rawDatabaseResponse));
  const hourLabel = `${String(getCurrentDataHour()).padStart(2, "0")}:00`;
  const modeLabel = selectedReportHourMode === "live" ? "目前 Current" : "回顧時段";

  panel.innerHTML = `
    <div class="recommendation-title">
      <div>
        <p class="rec-eyebrow">任務分派</p>
        <h2>站別工程師</h2>
      </div>
      <div class="recommendation-title-actions">
        <span class="status-pill ${statusClass(mainAssignment?.level || level)}">${escapeHtml(mainAssignment?.level || level)}</span>
        <button
          type="button"
          class="drawer-close-btn"
          id="recommendationDrawerCloseBtn"
          aria-label="關閉工程師面板"
        >
          關閉
        </button>
      </div>
    </div>

    ${assignments.length ? `
      <div class="recommendation-summary-row">
        <div>
          <strong>${escapeHtml(modeLabel)} ${escapeHtml(dateLabel)} ${escapeHtml(hourLabel)}：${escapeHtml(mainAssignment.station)} / ${escapeHtml(mainAssignment.processLayer)}</strong>
          <p>
            P1 通知 ${escapeHtml(mainAssignment.owner)}；判斷原因是 ${escapeHtml(mainAssignment.issueDirection)}。
          </p>
        </div>
        <div class="recommendation-summary-count">
          ${assignments.length} 項
        </div>
      </div>

      <div class="recommendation-collapsible-body">
        ${renderNoActionImpactAlert(mainAssignment, summary, dateLabel, hourLabel)}

        <div class="assignment-list">
          ${assignments.map((item, index) => `
            <article class="assignment-card priority-${index + 1}">
              <div class="assignment-head">
                <span class="assignment-priority">${escapeHtml(item.priority)}</span>
                <span class="assignment-status ${assignmentStatusClass(item.status)}">${escapeHtml(item.status)}</span>
              </div>
              <div class="assignment-owner">${escapeHtml(item.owner)}</div>
              <div class="assignment-grid">
                <div><strong>站別：</strong>${escapeHtml(item.station)} / ${escapeHtml(item.processLayer)}</div>
                <div><strong>問題：</strong>${escapeHtml(item.issueDirection)}</div>
                <div><strong>證據：</strong>${escapeHtml(item.evidence)}</div>
                <div><strong>任務：</strong>${escapeHtml(item.task)}</div>
                <div><strong>期限：</strong>${escapeHtml(item.due)}</div>
                <div><strong>驗收：</strong>${escapeHtml(item.acceptance)}</div>
              </div>
              ${(() => {
                  const taskId = buildAssignmentTaskId(item);
                  const acknowledged = isEngineerTaskAcknowledged(taskId);
                  const ackInfo = getEngineerAckInfo(taskId);
                  const mailSent = isEngineerTaskMailSent(taskId);
                  const mailInfo = getEngineerTaskMailSentInfo(taskId);

                  let statusClassName = "waiting";
                  let statusText = `等待發送任務｜Task ID：${escapeHtml(taskId)}`;
                  let buttonText = "發送任務 Email";
                  let buttonDisabled = false;
                  let buttonExtraClass = "";

                  if (acknowledged) {
                    statusClassName = "acknowledged";
                    statusText = `工程師已收到任務｜${escapeHtml(ackInfo.ackBy || item.owner)}｜${escapeHtml(ackInfo.ackAt || "-")}`;
                    buttonText = "工程師已收到任務";
                    buttonDisabled = true;
                    buttonExtraClass = "acknowledged";
                  } else if (mailSent) {
                    statusClassName = "waiting";
                    statusText = `已寄出，等待工程師確認｜${escapeHtml(mailInfo.sentAt || "-")}`;
                    buttonText = "已寄出，等待確認";
                    buttonDisabled = true;
                    buttonExtraClass = "sent";
                  }

                  return `
                    <div class="engineer-ack-status ${statusClassName}">
                      ${statusText}
                    </div>

                    <button
                      type="button"
                      class="send-warning-btn ${buttonExtraClass}"
                      data-assignment-index="${index}"
                      data-task-id="${escapeHtml(taskId)}"
                      ${buttonDisabled ? "disabled" : ""}
                    >
                      ${buttonText}
                    </button>
                  `;
                })()}
            </article>
          `).join("")}
        </div>

        <section class="acceptance-checklist">
          <h3>改善是否有效，看該小時後的資料</h3>
          <ul>
            ${assignments.slice(0, 1).map(item => `
              <li>${escapeHtml(item.station)} / ${escapeHtml(item.processLayer)}：${escapeHtml(item.issueDirection)} 是否消失</li>
              <li>${escapeHtml(qualityMode.scoreLabel)}是否回到 92% 以上或停止下降</li>
              <li>堵塞率、流量、噴幅、稼動率、Cycle Time 是否回到可接受範圍</li>
            `).join("")}
          </ul>
        </section>

        <div class="data-reminder">
          任務分派現在依照選定日期與選定小時的 API-shaped snapshot 產生。若下一小時恢復正常，仍可回到問題小時查看當時該叫誰檢查、檢查什麼。
        </div>
      </div>
    ` : buildRecommendationNoActionBlock(summary)}
  `;
}

function buildAssignmentTaskId(assignment) {
  const db = currentDatabaseResponse || MANAGER_MOCK_SUMMARY.rawDatabaseResponse;
  const dateKey = getResponseDateKeyFromDb(db);
  const dateText = String(dateKey || getActiveApiDateKey()).replace(/-/g, "");
  const hourText = String(getCurrentDataHour()).padStart(2, "0");
  const lineId = assignment.lineId || "line";
  const priority = assignment.priority || "P";

  return `TASK-${dateText}-${hourText}-${lineId}-${priority}`;
}
function buildEngineerWarningPayload(assignment) {
  const summary = MANAGER_MOCK_SUMMARY;
  const level = assignment.level || getOperationLevel(summary);
  const dateLabel = formatDateLabel(getResponseDateKeyFromDb(currentDatabaseResponse || summary.rawDatabaseResponse));
  const hourLabel = `${String(getCurrentDataHour()).padStart(2, "0")}:00`;
  const taskId = buildAssignmentTaskId(assignment);
  const batchInfo = getCurrentBatchInfo(summary, assignment);
  console.log("[MAIL DEBUG] assignment email:", assignment.email);
  return {
    action: "send_task",
    taskId: taskId,
    warningId: taskId,

    timestamp: new Date().toLocaleString("zh-TW", { timeZone: "Asia/Taipei" }),
    source: summary.dataSource,
    apiVersion: summary.apiVersion,
    dataDate: dateLabel,
    dataHour: hourLabel,
    hourKey: hourLabel,
    reviewMode: getTimeReviewModeLabel(),

    recipientRole: assignment.owner,
    recipientEmail: assignment.email,
    engineerName: assignment.owner,
    engineerEmail: assignment.email,
    to: assignment.email,

    level,
    riskLevel: level === "緊急" ? "High" : "Warning",

    line: summary.lineName,
    station: assignment.station,
    processLayer: assignment.processLayer,
    processStep: assignment.processLayer,
    machine: assignment.station,

    title: `${assignment.priority} ${assignment.owner} ${dateLabel} ${hourLabel} 站別任務通知`,
    issue: assignment.issue,
    issueDirection: assignment.issueDirection,

    batch: batchInfo,
    batchId: batchInfo.batchId || "-",

    evidence: assignment.evidence,
    impact: assignment.impact,
    task: assignment.task,
    due: assignment.due,
    acceptance: assignment.acceptance,

    message:
      `Manager Dashboard 偵測 ${assignment.station} / ${assignment.processLayer} 可能有問題。` +
      `請依照 ${dateLabel} ${hourLabel} 的資料處理：${assignment.issueDirection}。` +
      `證據：${assignment.evidence}。任務：${assignment.task}`,

    mainCause: assignment.evidence,
    suggestedAction: assignment.task,

    stationMetrics: assignment.stationMetrics || summary.mainStationMetrics,

    predictedOkRate: summary.predictedOkRate,
    predictedNgPcs: summary.predictedNgPcs,
    lostProductionPcs: summary.lostProductionPcs,

    metrics: {
      okRate: formatPercent(summary.predictedOkRate),
      ngPcs: String(summary.predictedNgPcs),
      utilization: assignment.stationMetrics && assignment.stationMetrics.utilization_pct !== undefined
        ? formatPercent(assignment.stationMetrics.utilization_pct)
        : "--",
      cycleTime: assignment.stationMetrics && assignment.stationMetrics.cycle_time_sec !== undefined
        ? `${Number(assignment.stationMetrics.cycle_time_sec).toFixed(1)} sec`
        : "--"
    },

    dataStatus: selectedReportHourMode === "live"
      ? "目前 Current 小時資料，當天品質分數仍屬待 QC / 預測品質。"
      : `${getCurrentQualityScoreMode().sourceStatus}；歷史回顧小時資料，用於追查當時異常與任務分派。`
  };
}
function postEngineerWarningPayload(payload) {
  if (!CONFIG.WARNING_APP_SCRIPT_URL) {
    console.log("[MAIL DEBUG] No Apps Script URL. Payload:", payload);
    return Promise.resolve({ ok: true, mock: true });
  }

  console.log("[MAIL POST DEBUG] form POST to:", CONFIG.WARNING_APP_SCRIPT_URL);
  console.log("[MAIL POST DEBUG] taskId:", payload.taskId);
  console.log("[MAIL POST DEBUG] to:", payload.to);

  return new Promise((resolve, reject) => {
    try {
      const form = document.createElement("form");
      form.method = "POST";
      form.action = CONFIG.WARNING_APP_SCRIPT_URL;
      form.target = "_blank";
      form.style.display = "none";

      const input = document.createElement("input");
      input.type = "hidden";
      input.name = "payload";
      input.value = JSON.stringify(payload);

      form.appendChild(input);
      document.body.appendChild(form);

      form.submit();

      setTimeout(() => {
        form.remove();
        resolve({
          ok: true,
          method: "form-post-new-tab",
          note: "Form POST submitted to Apps Script in a new tab."
        });
      }, 800);
      setTimeout(() => {
        syncEngineerAckStatusForSentTasks();
      }, 1500);

      setInterval(() => {
        syncEngineerAckStatusForSentTasks();
      }, 15000);
    } catch (error) {
      reject(error);
    }
  });
}

async function sendEngineerWarningEmail(index) {
  const assignment = CURRENT_RECOMMENDATION_ASSIGNMENTS[index] || ASSIGNMENT_CARDS[index];
  if (!assignment) return;

  const payload = buildEngineerWarningPayload(assignment);
  const button = document.querySelector(`[data-assignment-index="${index}"]`);
  console.log("[MAIL DEBUG] assignment email:", assignment.email);
  console.log("[MAIL DEBUG] payload.to:", payload.to);
  console.log("[MAIL DEBUG] full payload:", payload);
  try {
    if (button) {
      button.disabled = true;
      button.textContent = "發送中...";
      button.classList.remove("failed");
    }

    await postEngineerWarningPayload(payload);

    markEngineerTaskMailSent(payload.taskId, {
      station: assignment.station,
      processLayer: assignment.processLayer,
      engineerName: assignment.owner,
      engineerEmail: assignment.email
    });

    if (button) {
      button.disabled = true;
      button.textContent = "已寄出，等待工程師確認";
      button.classList.add("sent");
    }

    if (typeof renderCockpit === "function") {
      renderCockpit();
    }

    console.log("[TASK MAIL SENT] Engineer task payload:", payload);
  } catch (error) {
    console.error("[TASK MAIL ERROR] Engineer task failed:", error);

    if (button) {
      button.disabled = false;
      button.textContent = "發送失敗，重試";
      button.classList.add("failed");
    }
  }
}

function renderDataStatusBar() {
  const dataStatus = MANAGER_MOCK_SUMMARY.dataStatus;
  const bar = document.getElementById("dataStatusBar");
  const quality = getSelectedQualityInfo(MANAGER_MOCK_SUMMARY);
  const dateLabel = formatDateLabel(selectedReportDate);

  bar.innerHTML = `
    <div class="data-status-compact">
      <div class="data-status-main">
        <span class="live-dot ${latestDataError ? "error" : "ok"}"></span>
        <strong>資料狀態：</strong>
        ${escapeHtml(dateLabel)}｜${escapeHtml(getTimeReviewModeLabel())}｜品質等級 ${escapeHtml(quality.grade)}｜${escapeHtml(quality.value)}｜${escapeHtml(quality.sourceStatus)}
      </div>
      <div class="data-status-detail">
        來源 ${escapeHtml(dataStatus.source)}｜契約 ${escapeHtml(dataStatus.apiVersion)}｜今日資料完整度 ${escapeHtml(dataStatus.todayCompleteness)}%｜
        本週 ${escapeHtml(dataStatus.weekProgress)}｜未來 7 天為 forecastNoAction 推估｜最後更新 ${escapeHtml(formatLastUpdateTime(lastDataUpdateAt))}
      </div>
    </div>
  `;
}


function getDecisionSnapshotFromSummary(summary) {
  const diagnosis = buildRealtimeDiagnosis(summary);
  const main = diagnosis.main;

  if (!main) {
    return {
      key: "normal",
      label: "目前無異常",
      station: "無",
      direction: "無需處理",
      level: "正常",
      hour: getCurrentDataHour()
    };
  }

  return {
    key: `${main.station.lineId}_${main.topIssue.direction}_${main.topIssue.level}`,
    label: `${main.responsibility.stationName} / ${main.responsibility.layerName}：${main.topIssue.direction}`,
    station: `${main.responsibility.stationName} / ${main.responsibility.layerName}`,
    direction: main.topIssue.direction,
    level: main.topIssue.level,
    hour: getCurrentDataHour()
  };
}

function recordSimulatedDecisionAudit(summary) {
  if (!CONFIG.SIMULATED_API_ENABLED) return;

  const snapshot = getDecisionSnapshotFromSummary(summary);
  const currentTime = currentDatabaseResponse?.responseMeta?.dataWindow?.currentEnd || getSimulatedGeneratedAt();

  if (!latestDecisionSnapshot || latestDecisionSnapshot.key !== snapshot.key || latestDecisionSnapshot.hour !== snapshot.hour) {
    previousDecisionSnapshot = latestDecisionSnapshot;
    latestDecisionSnapshot = snapshot;
    SIMULATED_DECISION_HISTORY.unshift({
      ...snapshot,
      time: currentTime,
      uploadNo: SIMULATED_API_UPLOAD_INDEX + 1
    });
    SIMULATED_DECISION_HISTORY = SIMULATED_DECISION_HISTORY.slice(0, 6);
  }
}

function renderApiSimulationStatusPanel(summary) {
  if (!CONFIG.SIMULATED_API_ENABLED) return "";

  const status = getSimulatedApiStatusText();
  const segment = getTimeSegmentSummaryText();
  const currentDecision = latestDecisionSnapshot || getDecisionSnapshotFromSummary(summary);
  const previousDecision = previousDecisionSnapshot;
  const changedText = previousDecision && previousDecision.key !== currentDecision.key
    ? `已變更：${previousDecision.label} → ${currentDecision.label}`
    : "目前決策未變更";

  return `
    <section class="api-simulation-panel">
      <div>
        <p class="content-section-kicker">Simulated API upload</p>
        <h3>API 模擬資料流：每 ${Math.round(status.intervalMs / 1000)} 秒更新一筆</h3>
        <p>目前模擬日期 ${escapeHtml(formatDateLabel(status.dateKey))}，第 ${escapeHtml(status.uploadNo)} 筆 API 回傳，資料時間 ${escapeHtml(status.generatedAt)}。畫面模式：${escapeHtml(getTimeReviewModeLabel())}。</p>
      </div>
      <div class="api-simulation-grid">
        <div>
          <span>日期 / Current 時間</span>
          <strong>${escapeHtml(formatDateLabel(status.dateKey))} ${escapeHtml(String(status.currentHour).padStart(2, "0"))}:00</strong>
          <p>${escapeHtml(segment.pastText)}｜${escapeHtml(segment.currentText)}｜${escapeHtml(segment.futureText)}</p>
        </div>
        <div>
          <span>目前情境</span>
          <strong>${escapeHtml(status.scenarioName)}</strong>
          <p>${escapeHtml(status.scenarioNote)}</p>
        </div>
        <div>
          <span>建議決策驗證</span>
          <strong>${escapeHtml(currentDecision.label)}</strong>
          <p>${escapeHtml(changedText)}</p>
        </div>
      </div>
      <div class="api-simulation-actions">
        <button type="button" class="api-sim-next-btn" data-sim-next-upload="1">立即模擬下一筆 API upload</button>
        <span>用途：驗證不同 DB/API 資料進來後，診斷、建議決策、Past / Current / Future 是否會同步改變。當 23:00 完成後會自動封存當天，下一筆切到隔天 00:00。</span>
      </div>
    </section>
  `;
}


