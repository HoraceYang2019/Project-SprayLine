// ==============================
// Config - keep for future DB / Apps Script integration
// ==============================

const CONFIG = {
  USE_MOCK_DATA: true,
  HISTORICAL_ACTUAL_API_URL: "",
  DB_API_URL: "",
  FORECAST_API_URL: "",
  WARNING_APP_SCRIPT_URL: "https://script.google.com/macros/s/AKfycbyvPzX3epFpOH9AUFLLlD_-W4EXCOULHInUZKfmnCyJHlrCOY_HYTNSCBLtm3ZVzoWnBQ/exec",
  DB_POLL_INTERVAL_MS: 20 * 60 * 1000,
  MOCK_POLL_INTERVAL_MS: 5000
};

// ==============================
// Centralized manager mock data
// ==============================

const MANAGER_MOCK_SUMMARY = {
  lineName: "Spray Line 1",
  mainIssueStation: "Station 2",
  mainIssueRobot: "Robot 2",
  mainIssueProcess: "Top Coat",

  estimatedThisWeekEfficiency: 78.2,
  lastWeekActualEfficiency: 86.0,
  efficiencyChange: -7.8,

  todayEstimatedEfficiency: 76.8,
  yesterdayActualEfficiency: 84.5,
  todayVsYesterdayChange: -7.7,

  monthToDateEstimatedEfficiency: 80.5,
  lastMonthSamePeriodActualEfficiency: 85.2,
  monthChange: -4.7,

  predictedOkRate: 90.2,
  lastWeekActualOkRate: 94.5,
  predictedNgPcs: 610,
  lastWeekActualNgPcs: 420,

  utilization: 74.6,
  lastWeekUtilization: 85.8,

  performance: 84.5,
  lastWeekPerformance: 92.0,

  producedPcs: 11950,
  lastWeekProducedPcs: 12800,

  lostProductionPcs: 850,
  extraPredictedNgPcs: 190,
  extraDowntimeMinutes: 190,

  futureNoActionEfficiency: 72.5,
  futureNoActionOkRate: 87.8,
  futureLostPcs: 840,
  futureExtraNgPcs: 175,

  dataStatus: {
    todayCompleteness: 65,
    weekProgress: "3 / 5 工作日"
  },

  predictionValidation: {
    yesterdayPredictedOkRate: 91.4,
    yesterdayActualOkRate: 92.6,
    predictionErrorPts: 1.2,
    yesterdayPredictedNgPcs: 41,
    yesterdayActualNgPcs: 35,
    modelTrustLevel: "良好"
  }
};

const CATEGORY_LIST = [
  { key: "decision", label: "目前狀態" },
  { key: "impact", label: "損失多少" },
  { key: "action", label: "處理進度" },
  { key: "validation", label: "預測結果驗證" }
];

const ASSIGNMENT_CARDS = [
  {
    priority: "P1",
    owner: "設備工程師",
    email: "equipment.engineer@example.com",
    issue: "Station 2 稼動率下降",
    task: "查 downtime、alarm、pump、氣壓、sensor。",
    due: "今天 16:00",
    status: "待處理",
    acceptance: "Utilization 回升到 80% 以上"
  },
  {
    priority: "P2",
    owner: "製程工程師",
    email: "process.engineer@example.com",
    issue: "Top Coat 品質風險",
    task: "查噴槍、霧化壓力、塗料壓力、供漆穩定性。",
    due: "今天下班前",
    status: "待處理",
    acceptance: "Predicted NG 不再增加"
  },
  {
    priority: "P3",
    owner: "自動化工程師",
    email: "automation.engineer@example.com",
    issue: "Cycle Time 增加",
    task: "查 Robot 2 path、等待時間、治具定位、節拍設定。",
    due: "下一次更新前",
    status: "待處理",
    acceptance: "Cycle Time 回到 baseline +5% 以內"
  },
  {
    priority: "P4",
    owner: "品保工程師",
    email: "qa.engineer@example.com",
    issue: "待 QC 品質確認",
    task: "明天 QC 後查 NG 類型與 Station 2 相關批次分布。",
    due: "明天 QC 後",
    status: "等待 QC",
    acceptance: "確認 NG 沒有擴大"
  }
];

const ACCEPTANCE_CHECKLIST = [
  "Station 2 utilization 回升到 80% 以上",
  "Cycle Time 回到 baseline +5% 以內",
  "Predicted NG 不再增加",
  "本週預估效益開始回升",
  "明天 QC 結果確認 NG 沒有擴大"
];

let activeCategory = "decision";
let lastDataUpdateAt = new Date();
let latestDataError = "";
let selectedReportDate = getDateKey(new Date());
// ==============================
// Helpers
// ==============================

function formatPercent(value, digits = 1) {
  return `${Number(value || 0).toFixed(digits)}%`;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("en-US");
}

function formatDeltaPercent(value) {
  const number = Number(value || 0);
  return `${number > 0 ? "+" : ""}${number.toFixed(1)}%`;
}

function formatDeltaNumber(value, unit = "") {
  const number = Number(value || 0);
  return `${number > 0 ? "+" : ""}${formatNumber(number)}${unit}`;
}

function formatDeltaPoints(value) {
  const number = Number(value || 0);
  return `${number > 0 ? "+" : ""}${number.toFixed(1)} pts`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatLastUpdateTime(date) {
  if (!date) return "--";
  return date.toLocaleTimeString("zh-TW", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit"
  });
}

function getOperationLevel(summary) {
  if (summary.efficiencyChange <= -8 || summary.extraPredictedNgPcs >= 220) {
    return "緊急";
  }

  if (
    summary.efficiencyChange <= -3 ||
    summary.futureNoActionEfficiency < 73 ||
    summary.utilization < 80 ||
    summary.predictedOkRate < 92 ||
    summary.extraPredictedNgPcs >= 100
  ) {
    return "警告";
  }

  return "正常";
}

function statusClass(level) {
  if (level === "緊急") return "emergency";
  if (level === "警告") return "warning";
  return "normal";
}

function assignmentStatusClass(status) {
  if (status.includes("等待")) return "waiting";
  if (status.includes("完成")) return "done";
  return "pending";
}

function changeClass(value) {
  const text = String(value || "");
  if (text.startsWith("-") || text.includes("少產") || text.includes("增加") || text.includes("惡化")) return "negative-text";
  if (text.startsWith("+")) return "good-text";
  return "";
}
// ==============================
// 日期相關
// ==============================
function getDateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseDateKey(dateKey) {
  const [year, month, day] = String(dateKey).split("-").map(Number);
  return new Date(year, month - 1, day);
}

function formatDateLabel(dateKey) {
  const date = parseDateKey(dateKey);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}/${month}/${day}`;
}

function getTodayKey() {
  return getDateKey(new Date());
}

function isSelectedDatePendingQC(dateKey) {
  return dateKey >= getTodayKey();
}

function generateDateOptions(daysBack = 14) {
  const options = [];
  const today = new Date();

  for (let i = 0; i <= daysBack; i += 1) {
    const date = new Date(today);
    date.setDate(today.getDate() - i);

    const key = getDateKey(date);
    const label = i === 0
      ? `${formatDateLabel(key)} 今天`
      : i === 1
        ? `${formatDateLabel(key)} 昨天`
        : formatDateLabel(key);

    options.push({ key, label });
  }

  return options;
}
function getQualityGradeByOkRate(okRate) {
  const rate = Number(okRate || 0);

  if (rate >= 92) {
    return {
      grade: "良好",
      className: "quality-good",
      description: "品質穩定"
    };
  }

  if (rate >= 88) {
    return {
      grade: "警告",
      className: "quality-warning",
      description: "品質有下降風險"
    };
  }

  return {
    grade: "危險",
    className: "quality-danger",
    description: "品質風險偏高"
  };
}
function getSelectedQualityInfo(summary) {
  const pending = isSelectedDatePendingQC(selectedReportDate);

  if (pending) {
    const okRate = summary.predictedOkRate;
    const gradeInfo = getQualityGradeByOkRate(okRate);

    return {
      label: "選定日預測良率",
      value: formatPercent(okRate),
      sourceStatus: "待 QC / 預測品質",
      note: "尚未完成 QC，明日驗證",
      grade: gradeInfo.grade,
      gradeClass: gradeInfo.className,
      description: gradeInfo.description
    };
  }

  const okRate = summary.predictionValidation.yesterdayActualOkRate;
  const gradeInfo = getQualityGradeByOkRate(okRate);

  return {
    label: "選定日實際良率",
    value: formatPercent(okRate),
    sourceStatus: "已完成 QC / 實際品質",
    note: "QC 已完成，可視為實績",
    grade: gradeInfo.grade,
    gradeClass: gradeInfo.className,
    description: gradeInfo.description
  };
}
// ==============================
// Content builders
// ==============================

function buildTopProblemCards(summary) {
  return [
    {
      rank: "1",
      title: "最大拖累 1：稼動率下降",
      metric: `本週 ${formatPercent(summary.utilization)}｜上週 ${formatPercent(summary.lastWeekUtilization)}｜${formatDeltaPercent(summary.utilization - summary.lastWeekUtilization)}`,
      judgement: "Station 2 可能有停機、等待、alarm、pump、氣壓、sensor 或供料不穩定問題。",
      action: "設備工程師先查 Station 2 downtime、alarm、pump、氣壓、sensor。"
    },
    {
      rank: "2",
      title: "最大拖累 2：Cycle Time 變慢",
      metric: `本週 ${formatPercent(summary.performance)}｜上週 ${formatPercent(summary.lastWeekPerformance)}｜${formatDeltaPercent(summary.performance - summary.lastWeekPerformance)}`,
      judgement: "設備可能有運轉，但節拍變慢，可能來自 robot path、等待時間、治具定位或節拍設定問題。",
      action: "自動化工程師與製程工程師檢查 Robot 2 path、等待時間、cycle time 增加原因。"
    },
    {
      rank: "3",
      title: "最大拖累 3：品質風險上升",
      metric: `預測良率 ${formatPercent(summary.predictedOkRate)}｜上週實際 ${formatPercent(summary.lastWeekActualOkRate)}｜${formatDeltaPercent(summary.predictedOkRate - summary.lastWeekActualOkRate)}`,
      judgement: "今日 QC 尚未完成，目前不是實際品質結果，而是 Top Coat 的預測品質風險上升。",
      action: "製程工程師查 Top Coat 噴槍、霧化壓力、塗料壓力、供漆穩定性；品保工程師明天 QC 後比對 NG 類型。"
    }
  ];
}

function buildCategoryContent(summary) {
  const level = getOperationLevel(summary);

  return {
    decision: {
      title: "目前狀態",
      status: level,
      conclusion: {
        meta: `本週預估整體效益 ${formatPercent(summary.estimatedThisWeekEfficiency)}，比上週實際效益 ${formatDeltaPercent(summary.efficiencyChange)}；今日預估效益也比昨日實際效益 ${formatDeltaPercent(summary.todayVsYesterdayChange)}。`,
        reason: `主要拖累是 ${summary.mainIssueStation} 稼動率下降、Cycle Time 增加，以及 ${summary.mainIssueProcess} 預測品質風險上升。`,
        action: `${level}狀態：不建議等明天 QC 完成才處理。今天先派設備工程師與製程工程師做預防性檢查。`
      },
      situation: "系統判斷目前不是單純觀察，因為本週預估效益明顯低於上週實際效益，而且 Station 2 的稼動與節拍同時變差，今日品質仍是待 QC / 預測品質。",
      actionText: "先派設備工程師查 Station 2 downtime、alarm、pump、氣壓與 sensor；再派製程工程師查 Top Coat 噴槍、霧化壓力、塗料壓力與供漆穩定性。",
      evidence: [
        {
          label: "目前狀態",
          answer: level,
          text: `本週預估整體效益 ${formatPercent(summary.estimatedThisWeekEfficiency)}，比上週實際 ${formatPercent(summary.lastWeekActualEfficiency)} 下降 ${Math.abs(summary.efficiencyChange).toFixed(1)}%。`,
          status: "實際 + 預測 + 未來推估"
        },
        {
          label: "昨日 vs 今日",
          answer: formatDeltaPercent(summary.todayVsYesterdayChange),
          text: `今日預估 ${formatPercent(summary.todayEstimatedEfficiency)}，昨日實際 ${formatPercent(summary.yesterdayActualEfficiency)}，下降 ${Math.abs(summary.todayVsYesterdayChange).toFixed(1)}%。`,
          status: "今日待 QC / 預測品質"
        },
        {
          label: "為什麼變差",
          answer: `${summary.mainIssueStation} 拖累`,
          text: `稼動率從上週 ${formatPercent(summary.lastWeekUtilization)} 降到 ${formatPercent(summary.utilization)}，Cycle Time 相關效益從 ${formatPercent(summary.lastWeekPerformance)} 降到 ${formatPercent(summary.performance)}。`,
          status: "製程實際 + 品質預測"
        },
        {
          label: "品質是否已確認",
          answer: "尚未確認",
          text: "今日品質狀態為待 QC / 預測品質，尚不是最終 QC 結果。",
          status: "待 QC / 預測品質"
        }
      ]
    },

    impact: {
      title: "損失多少",
      status: level,
      conclusion: {
        meta: `目前預估少產 ${formatNumber(summary.lostProductionPcs)} pcs，預測不良數增加 ${formatNumber(summary.extraPredictedNgPcs)} pcs，停機增加 ${formatNumber(summary.extraDowntimeMinutes)} min。`,
        reason: "效益下降已經轉成產出缺口、停機增加與預測不良風險。",
        action: "若交期緊，列為 Priority 1；即使交期不緊，也要今天完成 Station 2 初查。"
      },
      situation: "本週效益下降不只是百分比變差，而是已經造成產量損失與品質風險上升。預測不良數增加代表明天 QC 完成後可能出現更多實際品質損失。",
      actionText: "先壓低預估少產與預測不良。只要 Station 2 的稼動與節拍恢復，損失評估會比只看品質欄位更快改善。",
      cards: [
        { label: "預估少產", value: `-${formatNumber(summary.lostProductionPcs)} pcs`, tone: "danger", note: "產能未達本週預期。" },
        { label: "預測不良數增加", value: `+${formatNumber(summary.extraPredictedNgPcs)} pcs`, tone: "danger", note: "今日品質仍待 QC，這是預測風險。" },
        { label: "停機增加", value: `+${formatNumber(summary.extraDowntimeMinutes)} min`, tone: "warning", note: "代表設備或流程穩定性需要檢查。" },
        { label: "Rework / Scrap 風險", value: "上升", tone: "warning", note: "若明天 QC 確認，成本會進一步增加。" },
        { label: "預估額外損失", value: "NT$ xx,xxx", tone: "neutral", note: "待串接成本資料後可自動換算。" },
        { label: "交期 / 客訴風險", value: "中風險", tone: "warning", note: "若後續 7 天不改善，風險會升高。" }
      ]
    },

    action: {
      title: "處理進度",
      status: level,
      conclusion: {
        meta: "派工已按設備、製程、自動化、品保四個角色拆分，重點是下一次資料更新要能驗收改善。",
        reason: "右側派工卡負責固定顯示責任人；本頁用來看各角色任務進度與驗收條件。",
        action: "主管下一步不是再看更多表格，而是確認 P1 / P2 是否在期限前回報，並用驗收條件判斷是否有效。"
      },
      situation: "這一頁不再重複右側派工內容，而是把派工任務轉成可追蹤的進度卡。主管可以用每張卡的期限與驗收條件檢查是否真的改善。",
      actionText: "下一次資料更新要看 Station 2 utilization、Cycle Time、Predicted NG、本週預估效益是否同步回升；明天 QC 後再確認實際 NG 是否沒有擴大。",
      assignments: ASSIGNMENT_CARDS
    },

    validation: {
      title: "預測結果驗證",
      status: Math.abs(summary.predictionValidation.predictionErrorPts) <= 2 ? "正常" : "警告",
      conclusion: {
        meta: `昨日預測良率與今日完成 QC 後實際良率誤差 ${formatDeltaPoints(summary.predictionValidation.predictionErrorPts)}。`,
        reason: `目前預測可信度為 ${summary.predictionValidation.modelTrustLevel}，可以用於今日待 QC / 預測品質的提前風險判斷。`,
        action: "若誤差連續超過 2 points，降低預測信任度並檢查模型輸入欄位。"
      },
      situation: "因為品質 QC 延遲 1 天，所以今天看到的品質是預測值。此區塊用來檢查昨天預測與今天完成 QC 後實際結果差多少。",
      actionText: "若預測誤差超過 2 percentage points，請標示預測可信度為中或低，並提醒工程師檢查模型或資料欄位。",
      validations: [
        { label: "預測良率", predicted: formatPercent(summary.predictionValidation.yesterdayPredictedOkRate), actual: formatPercent(summary.predictionValidation.yesterdayActualOkRate), error: formatDeltaPoints(summary.predictionValidation.predictionErrorPts), result: "良好" },
        { label: "預測不良數", predicted: String(summary.predictionValidation.yesterdayPredictedNgPcs), actual: String(summary.predictionValidation.yesterdayActualNgPcs), error: formatDeltaNumber(summary.predictionValidation.yesterdayActualNgPcs - summary.predictionValidation.yesterdayPredictedNgPcs, " pcs"), result: "良好" },
        { label: "風險等級", predicted: "中風險", actual: "中風險", error: "一致", result: "可信" },
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
  const header = document.getElementById("managerHeader");

  header.innerHTML = `
    <div class="decision-alert">
      <div class="header-title-row">
        <h1>${escapeHtml(summary.lineName)} 噴塗線主管駕駛艙</h1>
        <span class="header-status-pill ${statusClass(level)}">${escapeHtml(level)}</span>
      </div>
      <p class="decision-line primary">
        ${escapeHtml(level)}：本週預估效益比上週實際下降
        <span class="negative">${escapeHtml(Math.abs(summary.efficiencyChange).toFixed(1))}%</span>
      </p>
      <p class="decision-line secondary">
        主要拖累：${escapeHtml(summary.mainIssueStation)} 稼動率下降 + Cycle Time 增加
      </p>
      <p class="decision-line action">
        建議：今天先派設備工程師與製程工程師做預防性檢查。選定日期若為今日，品質為待 QC / 預測品質；昨日以前則為已完成 QC 實績。
      </p>
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
      <div class="overview-note">${escapeHtml(selectedQuality.status)}</div>
    </article>

    <article class="overview-mini-card warning-card">
      <div class="overview-label">本週預估效益</div>
      <div class="overview-value">${escapeHtml(formatPercent(summary.estimatedThisWeekEfficiency))}</div>
      <div class="overview-note">實際 + 預測 + 未來推估</div>
    </article>

    <article class="overview-mini-card actual-card">
      <div class="overview-label">上週實際效益</div>
      <div class="overview-value">${escapeHtml(formatPercent(summary.lastWeekActualEfficiency))}</div>
      <div class="overview-note">已完成 QC 實績</div>
    </article>

    <article class="overview-mini-card danger-card">
      <div class="overview-label">效益差異</div>
      <div class="overview-value">${escapeHtml(formatDeltaPercent(summary.efficiencyChange))}</div>
      <div class="overview-note">本週預估 vs 上週實際</div>
    </article>

    <article class="overview-mini-card">
      <div class="overview-label">主要拖累</div>
      <div class="overview-value small">${escapeHtml(summary.mainIssueStation)}</div>
      <div class="overview-note">${escapeHtml(summary.mainIssueProcess)} / Cycle Time</div>
    </article>

    <article class="overview-mini-card ${escapeHtml(selectedQuality.gradeClass)}">
      <div class="overview-label">${escapeHtml(selectedQuality.label)}</div>
      <div class="overview-value">${escapeHtml(selectedQuality.value)}</div>
      <div class="overview-note">
        品質等級：${escapeHtml(selectedQuality.grade)}｜${escapeHtml(selectedQuality.sourceStatus)}
      </div>
    </article>

  `;
}
function renderSelectedQualityNote() {
  const note = document.getElementById("selectedQualityNote");
  if (!note) return;

  const quality = getSelectedQualityInfo(MANAGER_MOCK_SUMMARY);
  const dateLabel = formatDateLabel(selectedReportDate);

  note.classList.remove(
    "pending-qc",
    "actual-qc",
    "quality-good",
    "quality-warning",
    "quality-danger"
  );

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

  container.innerHTML = CATEGORY_LIST.map(category => `
    <button
      type="button"
      class="category-btn ${activeCategory === category.key ? "active" : ""}"
      data-category="${escapeHtml(category.key)}"
      aria-pressed="${activeCategory === category.key}"
    >
      ${escapeHtml(category.label)}
    </button>
  `).join("");
}

function setActiveCategory(category) {
  if (!CATEGORY_LIST.some(item => item.key === category)) return;
  activeCategory = category;
  renderCategoryButtons();
  renderCategoryContent(category);
}

function renderCategoryContent(category) {
  const contentMap = buildCategoryContent(MANAGER_MOCK_SUMMARY);
  const content = contentMap[category] || contentMap.decision;
  document.getElementById("activeCategoryTitle").textContent = content.title;

  const container = document.getElementById("categoryContent");

  container.innerHTML = `
    ${renderConclusionCard(content)}
    ${renderCategoryEvidence(category, content)}
    ${renderTextSection("情況說明", content.situation)}
    ${renderTextSection("建議行動", content.actionText)}
  `;
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
  if (category === "decision") {
    return `
      ${renderTopProblemCards(MANAGER_MOCK_SUMMARY)}
      ${renderDecisionEvidenceCards(content)}
    `;
  }

  if (category === "impact") return renderImpactCards(content);
  if (category === "action") return renderProgressCards(content);
  if (category === "validation") return renderValidationCards(content);

  return "";
}

function renderTopProblemCards(summary) {
  const cards = buildTopProblemCards(summary);

  return `
    <section class="problem-card-grid" aria-label="Top 3 問題卡">
      ${cards.map(card => `
        <article class="problem-card">
          <div class="problem-rank">Top ${escapeHtml(card.rank)}</div>
          <h3 class="problem-title">${escapeHtml(card.title)}</h3>
          <div class="problem-metric">${escapeHtml(card.metric)}</div>
          <p class="problem-judgement"><strong>判斷：</strong>${escapeHtml(card.judgement)}</p>
          <p class="problem-action"><strong>建議：</strong>${escapeHtml(card.action)}</p>
        </article>
      `).join("")}
    </section>

    <div class="efficiency-note">
      註：本週預估整體效益由稼動效益、節拍效益與預測品質效益綜合判斷；今日品質尚未完成 QC，因此品質效益為預測值。
    </div>
  `;
}

function renderDecisionEvidenceCards(content) {
  return `
    <section class="evidence-panel">
      <p class="content-section-kicker">判斷依據</p>
      <h3>${escapeHtml("判斷依據：目前狀態分級")}</h3>
      <div class="decision-evidence-grid">
        ${content.evidence.map(item => `
          <article class="decision-evidence-card">
            <div class="decision-evidence-label">${escapeHtml(item.label)}</div>
            <div class="decision-evidence-answer ${changeClass(item.answer)}">${escapeHtml(item.answer)}</div>
            <p class="decision-evidence-text">${escapeHtml(item.text)}</p>
            <div class="decision-evidence-status">${escapeHtml(item.status)}</div>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderImpactCards(content) {
  return `
    <section class="evidence-panel">
      <p class="content-section-kicker">判斷依據</p>
      <h3>判斷依據：本週預估損失</h3>
      <div class="impact-card-grid">
        ${content.cards.map(item => `
          <article class="impact-card ${escapeHtml(item.tone)}">
            <div class="impact-label">${escapeHtml(item.label)}</div>
            <div class="impact-value">${escapeHtml(item.value)}</div>
            <p>${escapeHtml(item.note)}</p>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderProgressCards(content) {
  return `
    <section class="evidence-panel">
      <p class="content-section-kicker">判斷依據</p>
      <h3>判斷依據：今日派工狀態與驗收條件</h3>
      <div class="progress-card-grid">
        ${content.assignments.map(item => `
          <article class="progress-card">
            <div class="progress-head">
              <span class="assignment-priority">${escapeHtml(item.priority)}</span>
              <span class="assignment-status ${assignmentStatusClass(item.status)}">${escapeHtml(item.status)}</span>
            </div>
            <h4>${escapeHtml(item.owner)}</h4>
            <p><strong>問題：</strong>${escapeHtml(item.issue)}</p>
            <p><strong>任務：</strong>${escapeHtml(item.task)}</p>
            <p><strong>期限：</strong>${escapeHtml(item.due)}</p>
            <p><strong>驗收：</strong>${escapeHtml(item.acceptance)}</p>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderValidationCards(content) {
  return `
    <section class="evidence-panel">
      <p class="content-section-kicker">判斷依據</p>
      <h3>判斷依據：昨日預測 vs 今日 QC 實績</h3>
      <div class="validation-card-grid">
        ${content.validations.map(item => `
          <article class="validation-card">
            <div class="validation-label">${escapeHtml(item.label)}</div>
            <div class="validation-row"><span>昨日預測</span><strong>${escapeHtml(item.predicted)}</strong></div>
            <div class="validation-row"><span>今日 QC 後實際</span><strong>${escapeHtml(item.actual)}</strong></div>
            <div class="validation-row"><span>誤差</span><strong class="${changeClass(item.error)}">${escapeHtml(item.error)}</strong></div>
            <div class="validation-result">${escapeHtml(item.result)}</div>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderTextSection(title, text) {
  return `
    <section class="content-section text-only-section">
      <p class="content-section-kicker">${escapeHtml(title)}</p>
      <p class="section-text">${escapeHtml(text)}</p>
    </section>
  `;
}

function renderRecommendationPanel() {
  const summary = MANAGER_MOCK_SUMMARY;
  const level = getOperationLevel(summary);
  const panel = document.getElementById("recommendationPanel");

  panel.innerHTML = `
    <div class="recommendation-title">
      <div>
        <p class="rec-eyebrow">派工卡</p>
        <h2>建議派工</h2>
      </div>
      <span class="status-pill ${statusClass(level)}">${escapeHtml(level)}</span>
    </div>

    <div class="future-risk-alert">
      若今天不處理，未來 7 天可能再少產 ${escapeHtml(formatNumber(summary.futureLostPcs))} pcs，預測 NG 再增加 ${escapeHtml(formatNumber(summary.futureExtraNgPcs))} pcs，整體效益可能降到 ${escapeHtml(formatPercent(summary.futureNoActionEfficiency))}。
    </div>

    <div class="assignment-list">
      ${ASSIGNMENT_CARDS.map((item, index) => `
        <article class="assignment-card priority-${index + 1}">
          <div class="assignment-head">
            <span class="assignment-priority">${escapeHtml(item.priority)}</span>
            <span class="assignment-status ${assignmentStatusClass(item.status)}">${escapeHtml(item.status)}</span>
          </div>
          <div class="assignment-owner">${escapeHtml(item.owner)}</div>
          <div class="assignment-grid">
            <div><strong>任務：</strong>${escapeHtml(item.task)}</div>
            <div><strong>期限：</strong>${escapeHtml(item.due)}</div>
            <div><strong>驗收：</strong>${escapeHtml(item.acceptance)}</div>
          </div>
          <button type="button" class="send-warning-btn" data-assignment-index="${index}">發送通知 Email</button>
        </article>
      `).join("")}
    </div>

    <section class="acceptance-checklist">
      <h3>改善是否有效，看下一次資料更新</h3>
      <ul>
        ${ACCEPTANCE_CHECKLIST.map(item => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
    </section>

    <div class="data-reminder">
      今日品質不能視為實際品質結果。今日品質一律為待 QC / 預測品質；良率、不良率、不良數、不良類型都是預測或待驗證。
    </div>
  `;
}

function buildEngineerWarningPayload(assignment) {
  const summary = MANAGER_MOCK_SUMMARY;
  const level = getOperationLevel(summary);

  return {
    warningId: `ENGINEER-${assignment.priority}-${Date.now()}`,
    timestamp: new Date().toLocaleString("zh-TW", { timeZone: "Asia/Taipei" }),
    recipientRole: assignment.owner,
    recipientEmail: assignment.email,
    to: assignment.email,
    level,
    riskLevel: level === "緊急" ? "High" : "Warning",
    line: summary.lineName,
    station: summary.mainIssueStation,
    robot: summary.mainIssueRobot,
    processStep: summary.mainIssueProcess,
    title: `${assignment.priority} ${assignment.owner} 派工通知`,
    issue: assignment.issue,
    task: assignment.task,
    due: assignment.due,
    acceptance: assignment.acceptance,
    message:
      `請處理 ${assignment.issue}。目前本週預估整體效益 ${formatPercent(summary.estimatedThisWeekEfficiency)}，` +
      `比上週實際效益下降 ${Math.abs(summary.efficiencyChange).toFixed(1)}%。` +
      `主要問題為 ${summary.mainIssueStation} 稼動率下降、Cycle Time 增加，以及 ${summary.mainIssueProcess} 預測品質風險上升。`,
    mainCause: `${summary.mainIssueStation} 稼動率下降 + Cycle Time 增加 + ${summary.mainIssueProcess} 預測品質風險上升。`,
    suggestedAction: assignment.task,
    predictedOkRate: summary.predictedOkRate,
    predictedNgPcs: summary.predictedNgPcs,
    lostProductionPcs: summary.lostProductionPcs,
    futureLostPcs: summary.futureLostPcs,
    futureExtraNgPcs: summary.futureExtraNgPcs,
    futureNoActionEfficiency: summary.futureNoActionEfficiency,
    dataStatus: "今日品質為待 QC / 預測品質，不是最終 QC 結果。"
  };
}

function postEngineerWarningPayload(payload) {
  if (!CONFIG.WARNING_APP_SCRIPT_URL) {
    console.log("[MAIL DEBUG] No Apps Script URL. Payload:", payload);
    return Promise.resolve({ ok: true, mock: true });
  }

  return new Promise((resolve, reject) => {
    try {
      const iframeName = "engineerMailFrame_" + Date.now();
      const iframe = document.createElement("iframe");
      iframe.name = iframeName;
      iframe.style.display = "none";

      const form = document.createElement("form");
      form.method = "POST";
      form.action = CONFIG.WARNING_APP_SCRIPT_URL + "?source=engineer_assignment&ts=" + Date.now();
      form.target = iframeName;
      form.style.display = "none";

      const input = document.createElement("input");
      input.type = "hidden";
      input.name = "payload";
      input.value = JSON.stringify(payload);

      form.appendChild(input);
      document.body.appendChild(iframe);
      document.body.appendChild(form);

      let resolved = false;
      iframe.onload = function () {
        if (resolved) return;
        resolved = true;
        setTimeout(() => {
          form.remove();
          iframe.remove();
        }, 1000);
        resolve({ ok: true, method: "hidden-form-post" });
      };

      form.submit();

      setTimeout(() => {
        if (resolved) return;
        resolved = true;
        form.remove();
        iframe.remove();
        resolve({ ok: true, method: "hidden-form-post-timeout" });
      }, 5000);
    } catch (error) {
      reject(error);
    }
  });
}

async function sendEngineerWarningEmail(index) {
  const assignment = ASSIGNMENT_CARDS[index];
  if (!assignment) return;

  const payload = buildEngineerWarningPayload(assignment);
  const button = document.querySelector(`[data-assignment-index="${index}"]`);

  try {
    if (button) {
      button.disabled = true;
      button.textContent = "發送中...";
      button.classList.remove("failed");
    }

    await postEngineerWarningPayload(payload);

    if (button) {
      button.textContent = "已送出";
      button.classList.add("sent");
    }

    console.log("[MAIL SENT] Engineer warning payload:", payload);
  } catch (error) {
    console.error("[MAIL ERROR] Engineer warning failed:", error);
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
        ${escapeHtml(dateLabel)}｜
        品質等級 ${escapeHtml(quality.grade)}｜
        ${escapeHtml(quality.value)}｜
        ${escapeHtml(quality.sourceStatus)}
      </div>
      <div class="data-status-detail">
        今日資料完整度 ${escapeHtml(dataStatus.todayCompleteness)}%｜
        本週 ${escapeHtml(dataStatus.weekProgress)}｜
        未來 7 天為未來推估｜
        最後更新 ${escapeHtml(formatLastUpdateTime(lastDataUpdateAt))}
      </div>
    </div>
  `;
}

function renderCockpit() {
  renderManagerHeader();
  renderSelectedQualityNote();
  renderCategoryButtons();
  renderCategoryContent(activeCategory);
  renderRecommendationPanel();
  renderDataStatusBar();
}

// ==============================
// Future API placeholders
// ==============================

async function fetchHistoricalActualData() {
  if (CONFIG.USE_MOCK_DATA || !CONFIG.HISTORICAL_ACTUAL_API_URL) return null;
  const response = await fetch(CONFIG.HISTORICAL_ACTUAL_API_URL);
  return response.json();
}

async function fetchRealtimeDataFromDB() {
  if (CONFIG.USE_MOCK_DATA || !CONFIG.DB_API_URL) return null;
  const response = await fetch(CONFIG.DB_API_URL);
  return response.json();
}

async function fetchFutureForecastData() {
  if (CONFIG.USE_MOCK_DATA || !CONFIG.FORECAST_API_URL) return null;
  const response = await fetch(CONFIG.FORECAST_API_URL);
  return response.json();
}

function initCockpit() {
  renderCockpit();

  document.getElementById("categoryButtons").addEventListener("click", event => {
    const button = event.target.closest("[data-category]");
    if (!button) return;
    setActiveCategory(button.dataset.category);
  });

  document.getElementById("managerHeader").addEventListener("change", event => {
  const select = event.target.closest("#reportDateSelect");
  if (!select) return;

  selectedReportDate = select.value;
  renderCockpit();
  });
  document.getElementById("recommendationPanel").addEventListener("click", event => {
    const button = event.target.closest("[data-assignment-index]");
    if (!button) return;
    sendEngineerWarningEmail(Number(button.dataset.assignmentIndex));
  });
}

fetchHistoricalActualData().finally(initCockpit);
