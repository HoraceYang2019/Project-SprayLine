function renderManagerHeader() {
  const header = document.getElementById("managerHeader");
  if (!header) return;

  const dateOptions = generateDateOptions();
  const hourOptions = generateHourOptionsForSelectedDate();
  const selectedHourValue = getSelectedHourSelectValue();

  header.innerHTML = `
    <div class="manager-header-title">
      <h1>Manager Dashboard</h1>
    </div>
    <div class="manager-header-controls">
      <label class="manager-control">
        <span>Date</span>
        <select id="reportDateSelect">
          ${dateOptions.map(option => `
            <option value="${escapeHtml(option.key)}" ${option.key === selectedReportDate ? "selected" : ""}>
              ${escapeHtml(option.label)}
            </option>
          `).join("")}
        </select>
      </label>
      <div class="manager-control">
        <span>Hour</span>
        <div class="hour-picker" id="reportHourPicker">
          <button
            type="button"
            id="reportHourDropdownTrigger"
            class="hour-picker-trigger"
            aria-haspopup="listbox"
            aria-expanded="false"
          >
            <span>${escapeHtml(hourOptions.find(option => option.value === selectedHourValue)?.label || "選擇小時")}</span>
            <span class="hour-picker-chevron" aria-hidden="true">▾</span>
          </button>
          <div class="hour-picker-menu" id="reportHourDropdownMenu" role="listbox" aria-label="Hour options">
            ${hourOptions.map(option => `
              <button
                type="button"
                class="hour-picker-option ${option.value === selectedHourValue ? "is-selected" : ""}"
                data-report-hour-option="${escapeHtml(option.value)}"
                aria-selected="${option.value === selectedHourValue ? "true" : "false"}"
              >
                ${escapeHtml(option.label)}
              </button>
            `).join("")}
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderOverviewSection() {
  const container = document.getElementById("managerOverviewSection");
  if (!container || !MANAGER_SUMMARY) return;

  container.innerHTML = `
    ${renderKpiSection(MANAGER_SUMMARY)}
    ${renderStationComparisonSection(MANAGER_SUMMARY)}
  `;
}

function renderKpiSection(summary) {
  const kpis = getManagerKpis();
  const dailyProduction = kpis.dailyProduction || {};
  const worstStation = kpis.worstStation || {};

  return `
    <section class="manager-section">
      <div class="manager-section-head">
        <div>
          <p class="section-kicker">今日整體</p>
          <h2>主管重點指標</h2>
        </div>
      </div>
      <div class="kpi-grid">
        <article class="kpi-card">
          <span class="kpi-label">估算 OK rate</span>
          <strong class="kpi-value">${escapeHtml(formatPercent(kpis.estimatedOkRatePct))}</strong>
          <span class="kpi-note">由 selectedDate 感測資料加權估算</span>
        </article>
        <article class="kpi-card">
          <span class="kpi-label">估算 NG rate</span>
          <strong class="kpi-value">${escapeHtml(formatPercent(kpis.estimatedNgRatePct))}</strong>
          <span class="kpi-note">以 100% - 估算 OK rate 計算</span>
        </article>
        <article class="kpi-card">
          <span class="kpi-label">今日產能達成率</span>
          <strong class="kpi-value">${escapeHtml(formatPercent(kpis.productionAchievementPct))}</strong>
          <span class="kpi-note">
            ${escapeHtml(String(dailyProduction.distinctBatchCount ?? 0))} 批 × ${escapeHtml(String(dailyProduction.batchSizePcs ?? 264))} pcs / ${escapeHtml(formatNumber(dailyProduction.dailyTargetPcs ?? 20000))} pcs
          </span>
        </article>
        <article class="kpi-card">
          <span class="kpi-label">目前最嚴重站點</span>
          <strong class="kpi-station">${escapeHtml(worstStation.stationName || "-")} / ${escapeHtml(worstStation.processName || "-")}</strong>
          <span class="kpi-note">${escapeHtml(worstStation.mainIssue || "目前穩定")}</span>
        </article>
      </div>
    </section>
  `;
}

function renderStationComparisonSection(summary) {
  return `
    <section class="manager-section">
      <div class="manager-section-head station-section-head">
        <div>
          <p class="section-kicker">本小時比較</p>
          <h2>三站狀態比較表</h2>
        </div>
        <label class="batch-selector">
          <span>Batch</span>
          <select id="batchSelect">
            <option value="">${escapeHtml(summary.batchSelector?.defaultModeLabel || "全部批號 / 該小時累計")}</option>
            ${getBatchOptions().map(option => `
              <option value="${escapeHtml(option.batchId)}" ${option.batchId === selectedBatchId ? "selected" : ""}>
                ${escapeHtml(option.displayLabel)}
              </option>
            `).join("")}
          </select>
        </label>
      </div>
      <div class="station-table-wrap">
        <table class="station-comparison-table">
          <thead>
            <tr>
              <th>Station / Process</th>
              <th>稼動率 %</th>
              <th>預估 OK pcs</th>
              <th>預估 NG pcs</th>
              <th>主要問題</th>
            </tr>
          </thead>
          <tbody>
            ${getStationComparisonRows().map(renderStationComparisonRow).join("")}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function renderStationComparisonRow(row) {
  const stationLabel = `${row.stationName || "-"} / ${row.processName || "-"}`;
  const issueClass = row.issueLevel ? levelClass(row.issueLevel) : "";

  return `
    <tr>
      <td>
        <div class="station-name-cell">
          <strong>${escapeHtml(stationLabel)}</strong>
        </div>
      </td>
      <td>${renderMetricCell(row, "utilizationPct")}</td>
      <td>${renderMetricCell(row, "estimatedOkPcs")}</td>
      <td>${renderMetricCell(row, "estimatedNgPcs")}</td>
      <td>
        <span class="issue-chip ${escapeHtml(issueClass)}">${escapeHtml(row.mainIssue || "—")}</span>
      </td>
    </tr>
  `;
}

function renderMetricCell(row, metricKey) {
  const hasValue = row.hasData && row[metricKey] !== null && row[metricKey] !== undefined;
  const valueText = hasValue ? formatMetricValue(metricKey, row[metricKey]) : "—";
  const showIcon = row.hasData;

  return `
    <div class="metric-cell">
      <span>${escapeHtml(valueText)}</span>
      ${showIcon ? renderTrendIconButton(row.stationId, metricKey) : ""}
    </div>
  `;
}

function renderTrendIconButton(stationId, metricKey) {
  const label = metricKey === "utilizationPct"
    ? "開啟稼動率趨勢"
    : metricKey === "estimatedOkPcs"
      ? "開啟預估 OK pcs 趨勢"
      : "開啟預估 NG pcs 趨勢";

  return `
    <button
      type="button"
      class="trend-icon-btn"
      data-trend-station-id="${escapeHtml(stationId)}"
      data-trend-metric="${escapeHtml(metricKey)}"
      aria-label="${escapeHtml(label)}"
    >
      <svg viewBox="0 0 20 20" aria-hidden="true">
        <path d="M3 14.5 7.2 10.3l3 2.5 5.8-7.1" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></path>
        <path d="M3 16.5h14" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"></path>
      </svg>
    </button>
  `;
}
