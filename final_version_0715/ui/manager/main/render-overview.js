// =======================================
// Overview content builders and primary dashboard panels
// Split from the original dashboard.js to keep files focused and maintainable.
// =======================================
function buildTopProblemCards(summary) {
  const mainMetrics = summary.mainStationMetrics;
  const mainBaseline = summary.mainStationBaseline;
  const reasons = summary.mainRiskReasons;

  return [
    {
      rank: "1",
      title: `最大風險 1：${summary.mainIssueStation} / ${summary.mainIssueProcess} 風險最高`,
      metric: `風險分數 ${summary.mainStationRiskScore}｜品質分數 ${formatPercent(mainMetrics.quality_score_pct)}｜預測良率 ${formatPercent(summary.predictedOkRate)}`,
      judgement: reasons[0] || `${summary.mainIssueStation} 數據異常，需要工程師確認。`,
      action: `通知 ${summary.responsibleEngineer} 優先處理，檢查壓力、流量、噴幅、噴嘴、濾網與噴塗節拍。`
    },
    {
      rank: "2",
      title: "最大風險 2：堵塞與流量造成噴塗不穩",
      metric: `堵塞率 ${formatPercent(mainMetrics.clog_rate_pct)}｜流量 ${formatNumber(mainMetrics.flow_rate_ml_min)} ml/min｜基準 ${formatNumber(mainBaseline.flow_rate_ml_min)} ml/min`,
      judgement: "堵塞率偏高且流量低於基準，可能造成膜厚不均、色差或局部覆蓋不足。",
      action: `由 ${summary.responsibleEngineer} 確認噴嘴、濾網、供漆流量與塗料壓力。`
    },
    {
      rank: "3",
      title: "最大風險 3：噴幅與節拍偏離基準",
      metric: `噴幅 ${mainMetrics.spray_width_mm} mm｜目標 ${mainMetrics.target_min_mm}-${mainMetrics.target_max_mm} mm｜Cycle Time ${mainMetrics.cycle_time_sec.toFixed(1)} sec`,
      judgement: "噴幅超出目標範圍且 Cycle Time 變慢，會讓品質風險與產能風險同時上升。",
      action: `下一次資料更新前確認 ${summary.mainIssueStation} 噴幅、扇形氣壓、Robot path 與等待時間。`
    }
  ];
}

function buildCategoryContent(summary) {
  const level = getOperationLevel(summary);
  const mainMetrics = summary.mainStationMetrics;
  const mainBaseline = summary.mainStationBaseline;
  const qualityMode = getCurrentQualityScoreMode();

  return {
    monitor: {
      title: "狀態實時監控表",
      status: level,
      conclusion: {
        meta: `${level}：目前即時資料顯示 ${summary.mainIssueStation} / ${summary.mainIssueProcess} 風險最高，風險分數 ${summary.mainStationRiskScore}。`,
        reason: `狀態表由 stationTelemetry / component_metrics 欄位產生，包含壓力、流量、噴幅、堵塞率、品質分數、稼動率與 Cycle Time。`,
        action: `先通知 ${summary.responsibleEngineer} 處理 ${summary.mainIssueStation}，並用下一次 DB 更新確認指標是否回穩。`
      },
      situation: "這一頁是主管主畫面：把三站即時資料整理成一張監控表。主管不需要先看六個分類，而是先看哪一站異常、異常欄位是什麼、工程師是誰。",
      actionText: `目前 P1 是 ${summary.responsibleEngineer}。驗收重點是 ${summary.mainIssueStation} 的風險分數下降、堵塞率降低、噴幅回到目標範圍，以及預測 NG 不再增加。`,
      evidence: [
        {
          label: "最高風險站別",
          answer: `${summary.mainIssueStation} / ${summary.mainIssueProcess}`,
          text: `風險分數 ${summary.mainStationRiskScore}，對應設備 ${summary.mainIssueRobot}，站別 ${summary.responsibleEngineer}。`,
          status: "stationTelemetry + responsibility"
        },
        {
          label: "目前品質",
          answer: formatPercent(summary.predictedOkRate),
          text: `${qualityMode.isPredicted ? "當天品質尚未完成 QC，目前為預測品質分數；隔天 QC 後才會轉為實際品質。" : "選定日期已完成 QC，目前顯示實際品質分數。"}上週實際良率 ${formatPercent(summary.lastWeekActualOkRate)}。`,
          status: qualityMode.sourceStatus
        },
        {
          label: "產出差異",
          answer: `-${formatNumber(summary.lostProductionPcs)} pcs`,
          text: `目前產出 ${formatNumber(summary.producedPcs)} pcs，上週同期間 ${formatNumber(summary.lastWeekProducedPcs)} pcs。`,
          status: "productionKpi"
        },
        {
          label: "資料模式",
          answer: "Mock DB",
          text: `目前使用 mock web service 格式，未來可把 CONFIG.DB_API_URL 換成實際 API。`,
          status: "尚未真連線"
        }
      ]
    },

    decision: {
      title: "現在要不要處理",
      status: level,
      conclusion: {
        meta: `答案：要處理。${summary.mainIssueStation} / ${summary.mainIssueProcess} 是目前風險最高站別，風險分數 ${summary.mainStationRiskScore}。`,
        reason: `資料來源指出 ${summary.mainIssueStation} 品質分數 ${formatPercent(mainMetrics.quality_score_pct)}、堵塞率 ${formatPercent(mainMetrics.clog_rate_pct)}、稼動率 ${formatPercent(mainMetrics.utilization_pct)}，且噴幅 ${mainMetrics.spray_width_mm} mm 已超出目標範圍。`,
        action: `通知 ${summary.responsibleEngineer} 優先處理，不建議等明天 QC 完成才處理。`
      },
      situation: `這一頁是把 mock database / web service 回傳的三站即時資料轉成主管決策。系統比較第一站、第二站、第三站後，判斷 ${summary.mainIssueStation} / ${summary.mainIssueProcess} 的風險最高。`,
      actionText: `今天先通知 ${summary.responsibleEngineer} 處理 ${summary.mainIssueStation}，其他站別負責工程師同步確認前後段是否受到影響。`,
      evidence: [
        {
          label: "決策",
          answer: level === "正常" ? "觀察" : "要處理",
          text: `${summary.mainIssueStation} 風險分數 ${summary.mainStationRiskScore}，高於其他站別。`,
          status: "由 stationTelemetry 計算"
        },
        {
          label: "問題站別",
          answer: `${summary.mainIssueStation} / ${summary.mainIssueProcess}`,
          text: `對應設備：${summary.mainIssueRobot}；對應工程師：${summary.responsibleEngineer}。`,
          status: "由 stationResponsibility 對應"
        },
        {
          label: "主要異常",
          answer: `堵塞率 ${formatPercent(mainMetrics.clog_rate_pct)}`,
          text: summary.mainRiskReasons.slice(0, 2).join(" "),
          status: "壓力 / 流量 / 噴幅 / 堵塞率"
        },
        {
          label: "品質狀態",
          answer: "待 QC / 預測",
          text: `當天品質分數為模型預測 ${formatPercent(summary.predictedOkRate)}，明天 QC 後再驗證。`,
          status: "prediction + QC delay"
        }
      ]
    },

    gap: {
      title: "差多少",
      status: level,
      conclusion: {
        meta: `本週預估效益 ${formatPercent(summary.estimatedThisWeekEfficiency)}，比上週實際 ${formatDeltaPercent(summary.efficiencyChange)}。`,
        reason: `${summary.mainIssueStation} 稼動率比基準低 ${Math.abs(mainMetrics.utilization_pct - mainBaseline.utilization_pct).toFixed(1)} points，Cycle Time 比基準慢 ${(mainMetrics.cycle_time_sec - mainBaseline.cycle_time_sec).toFixed(1)} 秒。`,
        action: "先看差距最大的站別，不要平均看三站，否則會把第二站問題稀釋掉。"
      },
      situation: "這裡顯示的是 database / web service 資料轉換後的差異，不是人工填寫的結論。",
      actionText: `差距主要集中在 ${summary.mainIssueStation}，下一次更新要看稼動率、Cycle Time、堵塞率、噴幅是否回到基準。`,
      cards: [
        { label: "本週效益差異", value: formatDeltaPercent(summary.efficiencyChange), tone: "danger", note: `本週預估 ${formatPercent(summary.estimatedThisWeekEfficiency)} vs 上週實際 ${formatPercent(summary.lastWeekActualEfficiency)}` },
        { label: "今日 vs 昨日", value: formatDeltaPercent(summary.todayVsYesterdayChange), tone: "danger", note: `今日預估 ${formatPercent(summary.todayEstimatedEfficiency)} vs 昨日實際 ${formatPercent(summary.yesterdayActualEfficiency)}` },
        { label: "主站稼動差異", value: `${formatDeltaPercent(mainMetrics.utilization_pct - mainBaseline.utilization_pct)}`, tone: "warning", note: `${summary.mainIssueStation} 現在 ${formatPercent(mainMetrics.utilization_pct)}，基準 ${formatPercent(mainBaseline.utilization_pct)}` },
        { label: "Cycle Time 差異", value: `+${(mainMetrics.cycle_time_sec - mainBaseline.cycle_time_sec).toFixed(1)} sec`, tone: "warning", note: `${summary.mainIssueStation} 現在 ${mainMetrics.cycle_time_sec.toFixed(1)} sec，基準 ${mainBaseline.cycle_time_sec.toFixed(1)} sec` }
      ]
    },

    cause: {
      title: "為什麼變差",
      status: level,
      conclusion: {
        meta: `主要原因集中在 ${summary.mainIssueStation} / ${summary.mainIssueProcess}。`,
        reason: summary.mainRiskReasons.join(" "),
        action: `先由 ${summary.responsibleEngineer} 查 ${summary.mainIssueStation}，不要先分散處理所有站。`
      },
      situation: "原因分析不是寫死文字，而是由每站 pressure、flow rate、spray width、clog rate、quality score、utilization、cycle time 和 baseline 比較後產生。",
      actionText: `優先處理 ${summary.mainIssueStation} 的噴嘴、濾網、供漆流量、噴幅、壓力與節拍。`,
      causes: summary.mainRiskReasons
    },

    impact: {
      title: "損失多少",
      status: level,
      conclusion: {
        meta: `目前預估少產 ${formatNumber(summary.lostProductionPcs)} pcs，預測不良數增加 ${formatNumber(summary.extraPredictedNgPcs)} pcs，停機增加 ${formatNumber(summary.extraDowntimeMinutes)} min。`,
        reason: "這些是由 productionKpi 與 forecastNoAction 推估出的管理風險，不是最終財務損失。",
        action: `${summary.mainIssueStation} 若不改善，未來 7 天可能再少產 ${formatNumber(summary.futureLostPcs)} pcs。`
      },
      situation: "損失區塊要標示為預估 / 預測 / 待驗證，不能說成已發生的實際損失。",
      actionText: "主管應把它當成優先順序判斷依據：先降低預測 NG 與少產風險，再等待 QC 實績驗證。",
      cards: [
        { label: "預估少產風險", value: `-${formatNumber(summary.lostProductionPcs)} pcs`, tone: "danger", note: "currentPeriod.producedPcs vs previousPeriod.producedPcs" },
        { label: "預測 NG 增加風險", value: `+${formatNumber(summary.extraPredictedNgPcs)} pcs`, tone: "danger", note: "currentPeriod.predictedNgPcs vs previousPeriod.actualNgPcs" },
        { label: "停機 / 等待風險", value: `+${formatNumber(summary.extraDowntimeMinutes)} min`, tone: "warning", note: "productionKpi.currentPeriod.estimatedDowntimeMin" },
        { label: "未來 7 天少產風險", value: `-${formatNumber(summary.futureLostPcs)} pcs`, tone: "warning", note: "forecastNoAction.extraLostProductionPcs" },
        { label: "未來 7 天 NG 風險", value: `+${formatNumber(summary.futureExtraNgPcs)} pcs`, tone: "warning", note: "forecastNoAction.extraPredictedNgPcs" },
        { label: "額外成本", value: "待成本資料", tone: "neutral", note: "之後可接成本表自動換算" }
      ]
    },

    action: {
      title: "叫誰處理",
      status: level,
      conclusion: {
        meta: `P1：${summary.responsibleEngineer}。因為 ${summary.mainIssueStation} / ${summary.mainIssueProcess} 是風險最高站別。`,
        reason: "每一站有對應工程師，系統依照 stationResponsibility 與風險分數產生任務分派。",
        action: `先發送通知給 ${summary.responsibleEngineer}，其他站別負責工程師同步確認前後段影響。`
      },
      situation: "這裡不是叫主管自己猜要查哪一站，而是由資料判斷異常站別，再對應該站負責工程師。",
      actionText: "下一次資料更新要用驗收條件確認是否有效：風險分數下降、預測 NG 不再增加、壓力/流量/噴幅回穩。",
      assignments: summary.assignments
    },

    validation: {
      title: "預測可不可信",
      status: Math.abs(summary.predictionValidation.predictionErrorPts) <= 2 ? "正常" : "警告",
      conclusion: {
        meta: `昨日預測良率與今日完成 QC 後實際良率誤差 ${formatDeltaPoints(summary.predictionValidation.predictionErrorPts)}。`,
        reason: `模型輸入來源：${summary.predictionValidation.modelInputSource}；目前預測可信度為 ${summary.predictionValidation.modelTrustLevel}。`,
        action: "若誤差連續超過 2 points，降低預測信任度並檢查資料欄位或模型。"
      },
      situation: "因為品質 QC 延遲 1 天，今天看到的品質是預測值；昨天以前可以用實際 QC 回來驗證模型。",
      actionText: "當天的 NG、品質分數與品質等級都要標示為待 QC / 預測品質，不能當成實際結果；隔天 QC 完成後才可切換為實際品質。",
      validations: [
        { label: "預測良率", predicted: formatPercent(summary.predictionValidation.yesterdayPredictedOkRate), actual: formatPercent(summary.predictionValidation.yesterdayActualOkRate), error: formatDeltaPoints(summary.predictionValidation.predictionErrorPts), result: "良好" },
        { label: "預測不良數", predicted: String(summary.predictionValidation.yesterdayPredictedNgPcs), actual: String(summary.predictionValidation.yesterdayActualNgPcs), error: formatDeltaNumber(summary.predictionValidation.yesterdayActualNgPcs - summary.predictionValidation.yesterdayPredictedNgPcs, " pcs"), result: "可接受" },
        { label: "模型輸入來源", predicted: summary.predictionValidation.modelInputSource, actual: "QC 實績驗證", error: "有對照", result: "可信" },
        { label: "預測可信度", predicted: "-", actual: "-", error: "-", result: summary.predictionValidation.modelTrustLevel }
      ]
    }
  };
}

// ==============================
// Render
// ==============================

function renderManagerHeader() {
  const summary = MANAGER_MOCK_SUMMARY;
  const level = getOperationLevel(summary);
  const selectedQuality = getSelectedQualityInfo(summary);
  const dateOptions = generateDateOptions(14);
  const hourOptions = generateHourOptionsForSelectedDate();
  const selectedHourValue = getSelectedHourSelectValue();
  const header = document.getElementById("managerHeader");

  header.innerHTML = `
    <div class="decision-alert">
      <div class="header-title-row">
        <h1>${escapeHtml(summary.lineName)} 噴塗線主管駕駛艙</h1>
      </div>
      
    </div>

    <div class="overview-card-grid" aria-label="主管總覽摘要">
      <article class="overview-mini-card date-card">
        <label class="overview-label" for="reportDateSelect">資料日期</label>
        <select id="reportDateSelect" class="date-select">
          ${dateOptions.map(option => `
            <option value="${escapeHtml(option.key)}" ${option.key === selectedReportDate ? "selected" : ""}>
              ${escapeHtml(option.label)}
            </option>
          `).join("")}
        </select>
        <div class="overview-note">${escapeHtml(selectedQuality.sourceStatus)}｜${escapeHtml(getSelectedDateMode() === "archive" ? "歷史回顧" : "即時模擬")}</div>
      </article>

      <article class="overview-mini-card time-card">
        <label class="overview-label" for="reportHourDropdownTrigger">資料時間</label>
        <div class="time-review-picker">
          <button
            type="button"
            id="reportHourDropdownTrigger"
            class="time-dropdown-trigger ${hourOptions.find(option => option.value === selectedHourValue)?.problem ? "selected-problem-hour" : ""}"
            aria-haspopup="listbox"
            aria-expanded="false"
          >
            <span>${escapeHtml(hourOptions.find(option => option.value === selectedHourValue)?.label || "選擇時間")}</span>
            <span class="time-dropdown-arrow">⌄</span>
          </button>
          <div class="time-dropdown-menu" id="reportHourDropdownMenu" role="listbox" aria-label="選擇資料時間">
            ${hourOptions.map(option => `
              <button
                type="button"
                class="time-dropdown-option ${option.problem ? `problem-hour-option problem-${option.problemLevel}` : ""} ${option.value === selectedHourValue ? "is-selected" : ""}"
                data-report-hour-option="${escapeHtml(option.value)}"
                role="option"
                aria-selected="${option.value === selectedHourValue ? "true" : "false"}"
              >
                <span class="time-option-hour">${escapeHtml(option.hourLabel || option.label)}</span>
                ${option.problemText ? `<span class="time-option-problem">${escapeHtml(option.problemText)}</span>` : ""}
              </button>
            `).join("")}
          </div>
        </div>
        <select id="reportHourSelect" class="date-select time-select sr-only" aria-hidden="true" tabindex="-1">
          ${hourOptions.map(option => `
            <option value="${escapeHtml(option.value)}" ${option.value === selectedHourValue ? "selected" : ""}>
              ${escapeHtml(option.label)}
            </option>
          `).join("")}
        </select>
        <div class="overview-note">${escapeHtml(getTimeReviewModeLabel())}</div>
      </article>

      <article class="overview-mini-card warning-card">
        <div class="overview-label">本週預估效益</div>
        <div class="overview-value">${escapeHtml(formatPercent(summary.estimatedThisWeekEfficiency))}</div>
      </article>

      <article class="overview-mini-card actual-card">
        <div class="overview-label">上週實際效益</div>
        <div class="overview-value">${escapeHtml(formatPercent(summary.lastWeekActualEfficiency))}</div>
      </article>

      <article class="overview-mini-card danger-card">
        <div class="overview-label">效益差異</div>
        <div class="overview-value">${escapeHtml(formatDeltaPercent(summary.efficiencyChange))}</div>
        <div class="overview-note">預估 vs 實績</div>
      </article>


      <article class="overview-mini-card ${escapeHtml(selectedQuality.gradeClass)}">
        <div class="overview-label">${escapeHtml(selectedQuality.label)}</div>
        <div class="overview-value">${escapeHtml(selectedQuality.value)}</div>
        <div class="overview-note">
          品質等級：${escapeHtml(selectedQuality.grade)}｜${escapeHtml(selectedQuality.sourceStatus)}
        </div>
      </article>
    </div>
  `;
}

function renderSelectedQualityNote() {
  const note = document.getElementById("selectedQualityNote");
  if (!note) return;

  const quality = getSelectedQualityInfo(MANAGER_MOCK_SUMMARY);
  const dateLabel = formatDateLabel(selectedReportDate);

  note.classList.remove("pending-qc", "actual-qc", "quality-good", "quality-warning", "quality-danger");
  note.classList.add(quality.gradeClass);

  note.innerHTML = `
    ${escapeHtml(dateLabel)} 品質等級：
    <strong>${escapeHtml(quality.grade)}</strong>
    <span class="quality-note-sub">
      ｜${escapeHtml(quality.value)}｜${escapeHtml(quality.sourceStatus)}
    </span>
  `;
}

function renderCategoryButtons() {
  const container = document.getElementById("categoryButtons");
  const contentMap = buildCategoryContent(MANAGER_MOCK_SUMMARY);

  container.innerHTML = CATEGORY_LIST.map(category => {
    return `
      <button
        type="button"
        class="category-btn ${activeCategory === category.key ? "active" : ""}"
        data-category="${escapeHtml(category.key)}"
        aria-pressed="${activeCategory === category.key}"
      >
        <span class="category-btn-text">${escapeHtml(category.label)}</span>
      </button>
    `;
  }).join("");
}

function setActiveCategory(category) {
  if (!CATEGORY_LIST.some(item => item.key === category)) return;
  activeCategory = category;
  renderCategoryButtons();
  renderCategoryContent(category);
}

function renderCategoryContent(category) {
  const contentMap = buildCategoryContent(MANAGER_MOCK_SUMMARY);
  const content = contentMap[category] || contentMap.monitor;
  document.getElementById("activeCategoryTitle").textContent = content.title;

  const container = document.getElementById("categoryContent");

  // Manager UI simplified view:
  // 1) 狀態實時監控表：只保留三站即時監控表
  // 2) 預測驗證：只保留預測 vs QC 實績驗證
  // 不再顯示主管決策來源、情況說明、建議行動等文字卡片。
  if (category === "monitor") {
    container.innerHTML = renderStationMonitorTable(MANAGER_MOCK_SUMMARY);
    return;
  }

  if (category === "validation") {
    container.innerHTML = renderValidationCards(content);
    return;
  }

  container.innerHTML = renderCategoryEvidence(category, content);
}

function renderConclusionCard(content) {
  const level = content.status;

  return `
    <section class="conclusion-card ${statusClass(level)}">
      <div class="conclusion-status">
        <div class="conclusion-decision">${escapeHtml(level)}</div>
        <div class="conclusion-meta">${escapeHtml(content.conclusion.meta)}</div>
      </div>

      <div class="conclusion-copy">
        <div class="conclusion-item">
          <h3>主要原因</h3>
          <p>${escapeHtml(content.conclusion.reason)}</p>
        </div>
        <div class="conclusion-item">
          <h3>建議動作</h3>
          <p>${escapeHtml(content.conclusion.action)}</p>
        </div>
      </div>
    </section>
  `;
}

function renderCategoryEvidence(category, content) {
  if (category === "monitor") {
    return `${renderStationMonitorTable(MANAGER_MOCK_SUMMARY)}${renderTopProblemCards(MANAGER_MOCK_SUMMARY)}${renderDecisionEvidenceCards(content)}`;
  }

  if (category === "decision") {
    return `${renderTopProblemCards(MANAGER_MOCK_SUMMARY)}${renderDecisionEvidenceCards(content)}`;
  }

  if (category === "gap") return renderImpactCards(content, "判斷依據：目前差距");
  if (category === "cause") return renderCauseCards(content);
  if (category === "impact") return renderImpactCards(content, "判斷依據：預估損失風險");
  if (category === "action") return renderProgressCards(content);
  if (category === "validation") return renderValidationCards(content);

  return "";
}


function renderStationMonitorTable(summary) {
  const qualityMode = getCurrentQualityScoreMode();
  const stationItems = [...(summary.stationEvaluations || [])].sort((a, b) => {
    const aNo = Number(String(a.station.lineId || "").replace(/[^0-9]/g, "")) || 0;
    const bNo = Number(String(b.station.lineId || "").replace(/[^0-9]/g, "")) || 0;
    return aNo - bNo;
  });

  return `
    ${renderApiSimulationStatusPanel(summary)}
    <section class="evidence-panel quality-chart-panel">
      <p class="content-section-kicker">Today hourly ${escapeHtml(qualityMode.shortLabel)}</p>
      <h3>今日 24 小時${escapeHtml(qualityMode.scoreLabel)}：三站 XY 圖表</h3>
      <p class="quality-data-note">${escapeHtml(qualityMode.explanation)}品質分數採用「該小時所有 batch 分數平均值」。</p>
      <div class="quality-chart-grid">
        ${stationItems.map(item => renderQualityScoreChartCard(item)).join("")}
      </div>
    </section>
    ${renderRealtimeDiagnosisPanel(summary)}
  `;
}

function getHourlyQualityScoreSeries(lineId) {
  const values = getHourlyValuesFromDb(lineId, "quality_score_pct") || MOCK_QUALITY_SCORE_HOURLY_TODAY[lineId] || [];
  return Array.from({ length: 24 }, (_, hour) => ({
    hour,
    hourLabel: `${String(hour).padStart(2, "0")}:00`,
    qualityScore: Number(values[hour] ?? 0)
  }));
}

function average(values) {
  if (!values.length) return 0;
  return values.reduce((sum, value) => sum + Number(value || 0), 0) / values.length;
}


function getMetricDeltaPct(current, baseline) {
  const base = Number(baseline || 0);
  if (!base) return 0;
  return ((Number(current || 0) - base) / base) * 100;
}

function getHourlyTrendStats(lineId) {
  const series = getStationHourlyDetailSeries(lineId);
  const qualityStats = getMetricStats(series, "quality_score_pct");
  const utilizationStats = getMetricStats(series, "utilization_pct");
  const cycleStats = getMetricStats(series, "cycle_time_sec");
  const firstQuality = Number(series[0]?.quality_score_pct || 0);
  const latestQuality = Number(series[series.length - 1]?.quality_score_pct || 0);
  const qualityDrop = latestQuality - firstQuality;

  return {
    series,
    qualityStats,
    utilizationStats,
    cycleStats,
    qualityDrop
  };
}

function severityRank(level) {
  if (level === "緊急") return 3;
  if (level === "警告") return 2;
  return 1;
}

function buildStationDiagnosis(evaluation) {
  const qualityMode = getCurrentQualityScoreMode();
  const station = evaluation.station;
  const responsibility = evaluation.responsibility;
  const metrics = station.metrics;
  const baseline = station.baseline;
  const component = station.componentHealth || {};
  const trend = getHourlyTrendStats(station.lineId);

  const flowDelta = getMetricDeltaPct(metrics.flow_rate_ml_min, baseline.flow_rate_ml_min);
  const pressureDelta = getMetricDeltaPct(metrics.pressure_bar, baseline.pressure_bar);
  const utilizationGap = metrics.utilization_pct - baseline.utilization_pct;
  const cycleGap = metrics.cycle_time_sec - baseline.cycle_time_sec;
  const sprayOut = metrics.spray_width_mm < metrics.target_min_mm || metrics.spray_width_mm > metrics.target_max_mm;
  const qualityWarning = metrics.quality_score_pct < 92 || trend.qualityStats.latest < 92 || trend.qualityDrop <= -2;
  const highClog = metrics.clog_rate_pct >= 10;
  const flowLow = metrics.flow_rate_ml_min < baseline.flow_rate_ml_min * 0.92;
  const pressureAbnormal = Math.abs(pressureDelta) >= 8;
  const utilizationLow = utilizationGap <= -5;
  const cycleSlow = metrics.cycle_time_sec > baseline.cycle_time_sec * 1.08;

  const issues = [];

  (station.projectDiagnosis || [])
    .filter(item => item.severity && item.severity !== "normal")
    .forEach(item => {
      const level = item.severity === "alarm" ? "緊急" : "警告";
      issues.push({
        level,
        direction: item.stateLabel || "DB 診斷異常",
        evidence: item.evidence || `來源：diagnosis_latest.schema.json，confidence=${item.confidence || 0}`,
        impact: "此問題由 diagnosis_result 與 threshold tables 推論，代表目前站別資料已超出正常判斷規則。",
        action: item.action || `請 ${responsibility.engineerRole} 依診斷類別先確認 ${responsibility.stationName} 的噴嘴、濾網、噴幅、壓力流量與製程條件。`
      });
    });

  if (highClog || component.nozzle !== "normal") {
    issues.push({
      level: highClog && flowLow ? "緊急" : "警告",
      direction: "噴嘴可能堵塞 / 霧化不穩",
      evidence: `堵塞率 ${formatPercent(metrics.clog_rate_pct)}；噴嘴狀態 ${component.nozzle || "unknown"}；流量 ${formatNumber(metrics.flow_rate_ml_min)} ml/min，基準 ${formatNumber(baseline.flow_rate_ml_min)} ml/min。`,
      impact: `可能造成霧化不均、膜厚不穩、色差或局部覆蓋不足，進一步拉低${qualityMode.scoreLabel}。`,
      action: `請 ${responsibility.engineerRole} 先檢查 ${responsibility.stationName} 噴嘴是否堵塞、磨耗或噴形異常，必要時清潔或更換。`
    });
  }

  if ((component.filter_mesh && component.filter_mesh !== "normal") || (highClog && flowLow)) {
    issues.push({
      level: highClog && flowLow ? "緊急" : "警告",
      direction: "濾網可能堵塞 / 供漆阻力變大",
      evidence: `濾網狀態 ${component.filter_mesh || "unknown"}；流量偏差 ${flowDelta.toFixed(1)}%；堵塞率 ${formatPercent(metrics.clog_rate_pct)}。`,
      impact: "濾網阻塞會讓供漆流量下降，造成顏色層覆蓋不穩，品質分數與稼動率可能一起下降。",
      action: `檢查 ${responsibility.stationName} 濾網、管路與供漆壓力穩定性，先排除供漆端堵塞。`
    });
  }

  if (sprayOut || component.spray_width === "out_of_range") {
    const side = metrics.spray_width_mm > metrics.target_max_mm ? "偏寬" : "偏窄";
    issues.push({
      level: "緊急",
      direction: `噴幅偏離目標範圍（${side}）`,
      evidence: `目前噴幅 ${metrics.spray_width_mm.toFixed(0)} mm，目標 ${metrics.target_min_mm}-${metrics.target_max_mm} mm；噴幅狀態 ${component.spray_width || "unknown"}。`,
      impact: "噴幅偏離會直接影響顏色均勻性、過噴、邊緣覆蓋與外觀缺陷，是 QC 下降的高關聯原因。",
      action: `立即確認扇形氣壓、噴槍角度、噴槍距離與 Robot path，先把噴幅拉回目標範圍。`
    });
  }

  if (pressureAbnormal || flowLow) {
    const pressureText = pressureDelta >= 0 ? `高於基準 ${Math.abs(pressureDelta).toFixed(1)}%` : `低於基準 ${Math.abs(pressureDelta).toFixed(1)}%`;
    const flowText = flowDelta >= 0 ? `高於基準 ${Math.abs(flowDelta).toFixed(1)}%` : `低於基準 ${Math.abs(flowDelta).toFixed(1)}%`;
    issues.push({
      level: pressureAbnormal && flowLow ? "緊急" : "警告",
      direction: "壓力與流量不匹配",
      evidence: `壓力 ${metrics.pressure_bar.toFixed(2)} bar（${pressureText}）；流量 ${formatNumber(metrics.flow_rate_ml_min)} ml/min（${flowText}）。`,
      impact: "壓力上升但流量下降時，通常代表供漆阻力、堵塞或調壓不穩；會造成噴塗量不穩並影響品質分數。",
      action: "同時查塗料壓力、霧化空氣壓力、扇形氣壓與供漆流量，不要只調單一壓力值。"
    });
  }

  if (qualityWarning) {
    issues.push({
      level: trend.qualityStats.latest < 90 ? "緊急" : "警告",
      direction: `${qualityMode.scoreLabel}正在下降`,
      evidence: `最新${qualityMode.hourlyAverageLabel} ${formatPercent(trend.qualityStats.latest)}；最低 ${formatPercent(trend.qualityStats.min)}；00:00 到 23:00 變化 ${formatDeltaPoints(trend.qualityDrop)}。`,
      impact: qualityMode.isPredicted
        ? "當天品質尚未完成 QC，低於 92% 管理線代表明天 QC 可能出現 NG 增加或缺陷集中在該站相關製程。"
        : "此日期已完成 QC，實際品質分數低於 92% 管理線，代表該小時 batch 的實際品質已經有異常紀錄。",
      action: qualityMode.isPredicted
        ? "先把預測品質下降視為待驗證風險，下一次資料更新看預測品質分數是否停止下滑；隔天 QC 回來後確認缺陷類型。"
        : "回查該小時實際 QC 異常 batch，確認缺陷類型、站別原因與當時處理紀錄。"
    });
  }

  if (utilizationLow || cycleSlow) {
    issues.push({
      level: utilizationLow && cycleSlow ? "警告" : "正常",
      direction: "稼動率下降 / Cycle Time 變慢",
      evidence: `稼動率 ${formatPercent(metrics.utilization_pct)}，基準 ${formatPercent(baseline.utilization_pct)}；Cycle Time ${metrics.cycle_time_sec.toFixed(1)} s，基準 ${baseline.cycle_time_sec.toFixed(1)} s。`,
      impact: "若品質異常同時伴隨節拍變慢，可能代表等待、清槍、重噴、調機或設備狀態不穩。",
      action: "查看該時段是否有停等、清槍、換漆、換濾網、Robot path 等事件，判斷是品質造成產能下降，還是設備造成品質下降。"
    });
  }

  const activeIssues = issues.filter(issue => issue.level !== "正常");
  activeIssues.sort((a, b) => severityRank(b.level) - severityRank(a.level));

  const topIssue = activeIssues[0] || null;
  const decisionLevel = topIssue
    ? topIssue.level === "緊急"
      ? "立即處理"
      : "優先確認"
    : "不顯示";

  return {
    evaluation,
    station,
    responsibility,
    issues: activeIssues,
    topIssue,
    hasProblem: Boolean(topIssue),
    decisionLevel,
    trend,
    evidenceSummary: `${qualityMode.shortLabel} ${formatPercent(metrics.quality_score_pct)}｜堵塞 ${formatPercent(metrics.clog_rate_pct)}｜噴幅 ${metrics.spray_width_mm} mm｜壓力 ${metrics.pressure_bar.toFixed(2)} bar｜流量 ${formatNumber(metrics.flow_rate_ml_min)} ml/min｜稼動 ${formatPercent(metrics.utilization_pct)}｜Cycle ${metrics.cycle_time_sec.toFixed(1)} s`
  };
}

function buildRealtimeDiagnosis(summary) {
  const stationDiagnoses = (summary.stationEvaluations || [])
    .map(buildStationDiagnosis)
    .filter(item => item.hasProblem);

  stationDiagnoses.sort((a, b) => severityRank(b.topIssue.level) - severityRank(a.topIssue.level) || b.evaluation.riskScore - a.evaluation.riskScore);
  const main = stationDiagnoses[0] || null;

  if (!main) {
    return {
      main: null,
      stationDiagnoses: [],
      decision: "無異常",
      decisionText: "目前沒有需要顯示的異常資料。"
    };
  }

  return {
    main,
    stationDiagnoses,
    decision: main.decisionLevel,
    decisionText: main.topIssue.level === "緊急"
      ? `現在先處理 ${main.responsibility.stationName} / ${main.responsibility.layerName}，不要等 QC 完成才處理。`
      : `先請 ${main.responsibility.engineerRole} 確認 ${main.topIssue.direction}，下一次資料更新再決定是否升級。`
  };
}

