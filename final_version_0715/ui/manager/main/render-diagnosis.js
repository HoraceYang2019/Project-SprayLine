// =======================================
// Detailed diagnosis, charts, recommendation rendering, and notification payloads
// Split from the original dashboard.js to keep files focused and maintainable.
// =======================================
function renderRealtimeDiagnosisPanel(summary) {
  const diagnosis = buildRealtimeDiagnosis(summary);
  const main = diagnosis.main;

  if (!main) return "";

  return `
    <section class="evidence-panel diagnosis-panel">
      <div class="diagnosis-head">
        <div>
          <p class="content-section-kicker">Realtime diagnosis</p>
          <h3>目前可能發生什麼：由 DB 指標自動判斷</h3>
        </div>
        <span class="diagnosis-decision-pill ${statusClass(main.topIssue.level)}">${escapeHtml(diagnosis.decision)}</span>
      </div>

      <div class="diagnosis-main-card ${statusClass(main.topIssue.level)}">
        <div>
          <div class="diagnosis-label">最可能問題方向</div>
          <h4>${escapeHtml(main.responsibility.stationName)} / ${escapeHtml(main.responsibility.layerName)}：${escapeHtml(main.topIssue.direction)}</h4>
          <p>${escapeHtml(main.topIssue.impact)}</p>
        </div>
        <div class="diagnosis-main-evidence">
          <strong>資料證據</strong>
          <span>${escapeHtml(main.topIssue.evidence)}</span>
        </div>
      </div>

      <div class="diagnosis-grid">
        ${diagnosis.stationDiagnoses.map(diagnosisItem => renderStationDiagnosisCard(diagnosisItem)).join("")}
      </div>

    </section>
  `;
}

function renderStationDiagnosisCard(diagnosisItem) {
  if (!diagnosisItem || !diagnosisItem.topIssue) return "";

  const issue = diagnosisItem.topIssue;
  const visibleIssues = diagnosisItem.issues.slice(0, 3);

  return `
    <article class="diagnosis-card ${statusClass(issue.level)}">
      <div class="diagnosis-card-head">
        <div>
          <span>${escapeHtml(diagnosisItem.responsibility.stationName)}｜${escapeHtml(diagnosisItem.responsibility.layerName)}</span>
          <h4>${escapeHtml(issue.direction)}</h4>
        </div>
        <span class="table-status ${statusClass(issue.level)}">${escapeHtml(issue.level)}</span>
      </div>
      <p class="diagnosis-evidence-line">${escapeHtml(diagnosisItem.evidenceSummary)}</p>
      <ul>
        ${visibleIssues.map(item => `
          <li>
            <strong>${escapeHtml(item.direction)}</strong>
            <span>${escapeHtml(item.evidence)}</span>
          </li>
        `).join("")}
      </ul>
      <div class="diagnosis-action-box">
        <strong>建議決策</strong>
        <span>${escapeHtml(issue.action)}</span>
      </div>
    </article>
  `;
}


function renderTimeSegmentLegend() {
  const segment = getTimeSegmentSummaryText();

  return `
    <span class="time-segment-chip past">${escapeHtml(segment.pastText)}</span>
    <span class="time-segment-chip current">${escapeHtml(segment.currentText)}</span>
    <span class="time-segment-chip future">${escapeHtml(segment.futureText)}</span>
  `;
}

function renderQualityScoreChartCard(item) {
  const qualityMode = getCurrentQualityScoreMode();
  const station = item.station;
  const responsibility = item.responsibility;
  const series = getHourlyQualityScoreSeries(station.lineId);
  const currentHour = getCurrentDataHour();
  const currentAndPastValues = series
    .filter(row => Number(row.hour) <= currentHour)
    .map(row => row.qualityScore)
    .filter(value => value > 0);
  const currentRow = series.find(row => Number(row.hour) === currentHour) || series[Math.min(currentHour, series.length - 1)];
  const latest = Number(currentRow?.qualityScore || currentAndPastValues[currentAndPastValues.length - 1] || 0);
  const minValue = currentAndPastValues.length ? Math.min(...currentAndPastValues) : latest;
  const avgValue = average(currentAndPastValues.length ? currentAndPastValues : [latest]);
  const level = latest < 90 ? "緊急" : latest < 92 ? "警告" : "正常";

  return `
    <button
      type="button"
      class="quality-chart-card ${statusClass(level)}"
      data-detail-line-id="${escapeHtml(station.lineId)}"
      aria-label="開啟 ${escapeHtml(responsibility.stationName)} ${escapeHtml(responsibility.layerName)} 詳細資料"
    >
      <div class="quality-chart-head">
        <div>
          <p class="quality-chart-kicker">${escapeHtml(responsibility.stationName)}｜${escapeHtml(responsibility.layerName)}</p>
          <h4>${escapeHtml(responsibility.machineName)}</h4>
        </div>
        <span class="table-status ${statusClass(level)}">${escapeHtml(level)}</span>
      </div>

      <div class="quality-chart-kpi-row">
        <div><span>${escapeHtml(qualityMode.isPredicted ? "最新預測平均" : "最新實際平均")}</span><strong>${escapeHtml(formatPercent(latest))}</strong></div>
        <div><span>最低小時平均</span><strong>${escapeHtml(formatPercent(minValue))}</strong></div>
        <div><span>已發生小時平均</span><strong>${escapeHtml(formatPercent(avgValue))}</strong></div>
      </div>

      ${renderQualityScoreSvg(series)}

      <div class="quality-chart-foot">
        ${renderTimeSegmentLegend()}
        <span>Y 軸：${escapeHtml(qualityMode.axisLabel)}</span>
        <span>${escapeHtml(qualityMode.batchAverageNote)}</span>
        <span>管理線：92%</span>
      </div>

      <div class="quality-card-open-hint">點開查看 QC、稼動率與 Cycle Time 詳細圖表</div>
    </button>
  `;
}

function renderQualityScoreSvg(series) {
  const width = 720;
  const height = 240;
  const left = 54;
  const right = 20;
  const top = 22;
  const bottom = 38;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const yMin = 84;
  const yMax = 96;
  const currentHour = getCurrentDataHour();
  const halfStep = plotWidth / 23 / 2;

  const xForHour = hour => left + (Number(hour || 0) / 23) * plotWidth;
  const yForValue = value => top + ((yMax - Number(value || 0)) / (yMax - yMin)) * plotHeight;

  const metricKey = "qualityScore";
  const { pastRows, futureRows, currentRow } = splitSeriesByCurrentHour(series);
  const allPoints = makeSvgPoints(series, xForHour, yForValue, metricKey);
  const pastPoints = makeSvgPoints(pastRows, xForHour, yForValue, metricKey);
  const futurePoints = makeSvgPoints(futureRows, xForHour, yForValue, metricKey);
  const areaPoints = `${left},${top + plotHeight} ${allPoints} ${left + plotWidth},${top + plotHeight}`;
  const thresholdY = yForValue(92);
  const lastPoint = currentRow || series[series.length - 1];
  const lastX = xForHour(lastPoint.hour);
  const lastY = yForValue(lastPoint.qualityScore);
  const currentX = xForHour(currentHour);
  const currentBandX = Math.max(left, currentX - halfStep);
  const currentBandWidth = Math.min(left + plotWidth, currentX + halfStep) - currentBandX;
  const yTicks = [96, 94, 92, 90, 88, 86, 84];
  const xTicks = Array.from(new Set([0, 4, 8, currentHour, 12, 16, 20, 23]))
    .filter(hour => hour >= 0 && hour <= 23)
    .sort((a, b) => a - b);

  return `
    <div class="quality-svg-wrap" aria-label="每小時品質分數折線圖">
      <svg viewBox="0 0 ${width} ${height}" role="img">
        <rect x="0" y="0" width="${width}" height="${height}" rx="16" class="chart-bg"></rect>
        <rect x="${left}" y="${top}" width="${Math.max(0, currentBandX - left).toFixed(1)}" height="${plotHeight}" class="chart-zone-past"></rect>
        <rect x="${currentBandX.toFixed(1)}" y="${top}" width="${currentBandWidth.toFixed(1)}" height="${plotHeight}" class="chart-zone-current"></rect>
        <rect x="${(currentX + halfStep).toFixed(1)}" y="${top}" width="${Math.max(0, left + plotWidth - (currentX + halfStep)).toFixed(1)}" height="${plotHeight}" class="chart-zone-future"></rect>

        ${yTicks.map(value => `
          <line x1="${left}" y1="${yForValue(value).toFixed(1)}" x2="${left + plotWidth}" y2="${yForValue(value).toFixed(1)}" class="chart-grid-line"></line>
          <text x="${left - 12}" y="${(yForValue(value) + 4).toFixed(1)}" text-anchor="end" class="chart-axis-label">${value}%</text>
        `).join("")}

        ${xTicks.map(hour => `
          <text x="${xForHour(hour).toFixed(1)}" y="${height - 12}" text-anchor="middle" class="chart-axis-label ${hour === currentHour ? "chart-current-axis-label" : ""}">${String(hour).padStart(2, "0")}</text>
        `).join("")}

        <line x1="${left}" y1="${thresholdY.toFixed(1)}" x2="${left + plotWidth}" y2="${thresholdY.toFixed(1)}" class="chart-threshold-line"></line>
        <text x="${left + plotWidth - 4}" y="${(thresholdY - 6).toFixed(1)}" text-anchor="end" class="chart-threshold-label">標準線 92%</text>

        <polygon points="${areaPoints}" class="chart-area"></polygon>
        ${pastPoints ? `<polyline points="${pastPoints}" class="chart-line-past"></polyline>` : ""}
        ${futurePoints ? `<polyline points="${futurePoints}" class="chart-line-future"></polyline>` : ""}
        <line x1="${currentX.toFixed(1)}" y1="${top}" x2="${currentX.toFixed(1)}" y2="${top + plotHeight}" class="chart-current-line"></line>
        <text x="${(currentX + 5).toFixed(1)}" y="${top + 14}" class="chart-current-label">Current ${String(currentHour).padStart(2, "0")}:00</text>

        <circle cx="${lastX.toFixed(1)}" cy="${lastY.toFixed(1)}" r="6" class="chart-current-point"></circle>
        <text x="${(lastX - 8).toFixed(1)}" y="${(lastY - 10).toFixed(1)}" text-anchor="end" class="chart-last-label">${lastPoint.qualityScore.toFixed(1)}%</text>
        ${renderSvgHoverPoints({
          series,
          xForHour,
          yForValue,
          metricKey,
          valueFormatter: value => `${value.toFixed(1)}%`,
          plotTop: top,
          plotBottom: top + plotHeight,
          plotLeft: left,
          plotRight: left + plotWidth
        })}
      </svg>
    </div>
  `;
}

function getStationEvaluationByLineId(lineId) {
  return (MANAGER_MOCK_SUMMARY.stationEvaluations || []).find(item => item.station.lineId === lineId) || null;
}

function getStationHourlyDetailSeries(lineId) {
  const detail = MOCK_STATION_DETAIL_HOURLY_TODAY[lineId] || {};
  const fallbackQuality = MOCK_QUALITY_SCORE_HOURLY_TODAY[lineId] || [];
  const apiQuality = getHourlyValuesFromDb(lineId, "quality_score_pct");
  const apiUtilization = getHourlyValuesFromDb(lineId, "utilization_pct");
  const apiCycle = getHourlyValuesFromDb(lineId, "cycle_time_sec");

  return Array.from({ length: 24 }, (_, hour) => ({
    hour,
    hourLabel: `${String(hour).padStart(2, "0")}:00`,
    quality_score_pct: Number((apiQuality || detail.quality_score_pct || fallbackQuality)[hour] ?? 0),
    utilization_pct: Number((apiUtilization || detail.utilization_pct || [])[hour] ?? 0),
    cycle_time_sec: Number((apiCycle || detail.cycle_time_sec || [])[hour] ?? 0)
  }));
}

function getMetricStats(series, key) {
  const currentHour = getCurrentDataHour();
  const values = series
    .filter(row => Number(row.hour) <= currentHour)
    .map(row => Number(row[key] || 0))
    .filter(value => value > 0);
  const currentRow = series.find(row => Number(row.hour) === currentHour) || series[Math.min(currentHour, series.length - 1)];
  const latest = Number(currentRow?.[key] || values[values.length - 1] || 0);
  const safeValues = values.length ? values : [latest].filter(value => value > 0);
  return {
    latest,
    min: safeValues.length ? Math.min(...safeValues) : 0,
    max: safeValues.length ? Math.max(...safeValues) : 0,
    avg: average(safeValues)
  };
}


function renderSvgHoverPoints(options) {
  const {
    series,
    xForHour,
    yForValue,
    metricKey,
    valueFormatter,
    plotTop,
    plotBottom,
    plotLeft,
    plotRight
  } = options;

  const tooltipWidth = 136;
  const tooltipHeight = 46;

  return series.map(row => {
    const x = xForHour(row.hour);
    const y = yForValue(row[metricKey]);
    const valueText = valueFormatter(Number(row[metricKey] || 0));
    const timeText = row.hourLabel || `${String(row.hour).padStart(2, "0")}:00`;
    const segment = getTimeSegment(row.hour);
    const preferLeft = x > plotLeft + (plotRight - plotLeft) * 0.72;
    const tooltipX = preferLeft ? x - tooltipWidth - 12 : x + 12;
    const tooltipY = Math.max(6, Math.min(plotBottom - tooltipHeight - 6, y - tooltipHeight - 10));
    const textX = tooltipX + 10;

    return `
      <g class="chart-hover-point" tabindex="0" aria-label="${escapeHtml(timeText)}，${escapeHtml(valueText)}，${escapeHtml(segment.label)}">
        <line x1="${x.toFixed(1)}" y1="${plotTop}" x2="${x.toFixed(1)}" y2="${plotBottom}" class="chart-hover-guide"></line>
        <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="15" class="chart-hover-hit"></circle>
        <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="5" class="chart-hover-dot ${escapeHtml(segment.key)}"></circle>
        <rect x="${tooltipX.toFixed(1)}" y="${tooltipY.toFixed(1)}" width="${tooltipWidth}" height="${tooltipHeight}" rx="9" class="chart-hover-tooltip-bg"></rect>
        <text x="${textX.toFixed(1)}" y="${(tooltipY + 13).toFixed(1)}" class="chart-hover-tooltip-text">${escapeHtml(timeText)}｜${escapeHtml(segment.key.toUpperCase())}</text>
        <text x="${textX.toFixed(1)}" y="${(tooltipY + 28).toFixed(1)}" class="chart-hover-tooltip-value">${escapeHtml(valueText)}</text>
        <text x="${textX.toFixed(1)}" y="${(tooltipY + 40).toFixed(1)}" class="chart-hover-tooltip-segment">${escapeHtml(segment.label)}</text>
      </g>
    `;
  }).join("");
}

function formatMetricValue(value, unit, digits = 1) {
  const number = Number(value || 0).toFixed(digits);
  return unit === "%" ? `${number}%` : `${number} ${unit}`;
}

function setStationDetailOpen(open, lineId = selectedDetailLineId) {
  isStationDetailOpen = Boolean(open);
  selectedDetailLineId = isStationDetailOpen ? lineId : "";

  const panel = document.getElementById("stationDetailPanel");
  const overlay = document.getElementById("stationDetailOverlay");

  if (panel) {
    if (isStationDetailOpen) {
      panel.innerHTML = renderStationDetailPanel(selectedDetailLineId);
    }

    panel.classList.toggle("open", isStationDetailOpen);
    panel.setAttribute("aria-hidden", String(!isStationDetailOpen));
  }

  if (overlay) {
    overlay.classList.toggle("open", isStationDetailOpen);
  }

  document.body.classList.toggle("detail-open", isStationDetailOpen);
}

function renderStationDetailPanel(lineId) {
  const qualityMode = getCurrentQualityScoreMode();
  const evaluation = getStationEvaluationByLineId(lineId);

  if (!evaluation) {
    return `
      <div class="station-detail-header">
        <div>
          <p class="content-section-kicker">Station detail</p>
          <h3>找不到站別資料</h3>
        </div>
        <button type="button" class="station-detail-close-btn" id="stationDetailCloseBtn">關閉</button>
      </div>
    `;
  }

  const station = evaluation.station;
  const responsibility = evaluation.responsibility;
  const series = getStationHourlyDetailSeries(lineId);
  const qualityStats = getMetricStats(series, "quality_score_pct");
  const utilizationStats = getMetricStats(series, "utilization_pct");
  const cycleStats = getMetricStats(series, "cycle_time_sec");

  return `
    <div class="station-detail-header">
      <div>
        <p class="content-section-kicker">Station detail / today 24 hours</p>
        <h3>${escapeHtml(responsibility.stationName)}｜${escapeHtml(responsibility.layerName)} 詳細資料</h3>
        <p>
          ${escapeHtml(responsibility.machineName)}｜負責：${escapeHtml(responsibility.engineerRole)}｜
          目前風險分數 ${escapeHtml(evaluation.riskScore)}
        </p>
      </div>
      <button type="button" class="station-detail-close-btn" id="stationDetailCloseBtn">關閉</button>
    </div>

    <div class="station-detail-summary-grid">
      <div><span>${escapeHtml(qualityMode.hourlyAverageLabel)}</span><strong>${escapeHtml(formatMetricValue(qualityStats.latest, "%"))}</strong></div>
      <div><span>稼動率最新值</span><strong>${escapeHtml(formatMetricValue(utilizationStats.latest, "%"))}</strong></div>
      <div><span>Cycle Time 最新值</span><strong>${escapeHtml(formatMetricValue(cycleStats.latest, "s"))}</strong></div>
      <div><span>資料時間</span><strong>${escapeHtml(getTimeSegmentSummaryText().currentText)}</strong></div>
    </div>

    <div class="station-detail-chart-stack">
      ${renderMetricDetailChart({
        title: qualityMode.scoreLabel,
        leftLabel: qualityMode.scoreLabel,
        series,
        metricKey: "quality_score_pct",
        unit: "%",
        yMin: 84,
        yMax: 96,
        standardValue: 92,
        standardLabel: "標準線 92%",
        stats: qualityStats,
        lowerIsWorse: true
      })}

      ${renderMetricDetailChart({
        title: "稼動率",
        leftLabel: "稼動率",
        series,
        metricKey: "utilization_pct",
        unit: "%",
        yMin: 68,
        yMax: 90,
        standardValue: station.baseline.utilization_pct,
        standardLabel: `基準 ${station.baseline.utilization_pct.toFixed(1)}%`,
        stats: utilizationStats,
        lowerIsWorse: true
      })}

      ${renderMetricDetailChart({
        title: "Cycle Time",
        leftLabel: "Cycle-Time",
        series,
        metricKey: "cycle_time_sec",
        unit: "s",
        yMin: 44,
        yMax: 56,
        standardValue: station.baseline.cycle_time_sec,
        standardLabel: `基準 ${station.baseline.cycle_time_sec.toFixed(1)}s`,
        stats: cycleStats,
        lowerIsWorse: false
      })}
    </div>
  `;
}

function renderMetricDetailChart(config) {
  return `
    <article class="station-detail-chart-row">
      <div class="station-detail-chart-label">
        <strong>${escapeHtml(config.leftLabel)}</strong>
        <span>${escapeHtml(config.title)}</span>
      </div>
      <div class="station-detail-chart-card">
        <div class="station-detail-chart-head">
          <h4>${escapeHtml(config.title)}</h4>
          <div>
            <span>最新 ${escapeHtml(formatMetricValue(config.stats.latest, config.unit))}</span>
            <span>平均 ${escapeHtml(formatMetricValue(config.stats.avg, config.unit))}</span>
            <span>${escapeHtml(config.lowerIsWorse ? "低於標準為異常" : "高於基準為異常")}</span>
            ${renderTimeSegmentLegend()}
          </div>
        </div>
        ${renderMetricDetailSvg(config)}
      </div>
    </article>
  `;
}

function renderMetricDetailSvg(config) {
  const width = 980;
  const height = 220;
  const left = 62;
  const right = 26;
  const top = 22;
  const bottom = 38;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const yMin = Number(config.yMin);
  const yMax = Number(config.yMax);
  const currentHour = getCurrentDataHour();
  const halfStep = plotWidth / 23 / 2;

  const xForHour = hour => left + (Number(hour || 0) / 23) * plotWidth;
  const yForValueRaw = value => top + ((yMax - Number(value || 0)) / (yMax - yMin)) * plotHeight;
  const clampY = value => Math.max(top, Math.min(top + plotHeight, yForValueRaw(value)));
  const yForValue = value => clampY(value);
  const { pastRows, futureRows, currentRow } = splitSeriesByCurrentHour(config.series);
  const allPoints = makeSvgPoints(config.series, xForHour, yForValue, config.metricKey);
  const pastPoints = makeSvgPoints(pastRows, xForHour, yForValue, config.metricKey);
  const futurePoints = makeSvgPoints(futureRows, xForHour, yForValue, config.metricKey);
  const areaPoints = `${left},${top + plotHeight} ${allPoints} ${left + plotWidth},${top + plotHeight}`;
  const standardY = clampY(config.standardValue);
  const lastPoint = currentRow || config.series[config.series.length - 1];
  const lastX = xForHour(lastPoint.hour);
  const lastY = clampY(lastPoint[config.metricKey]);
  const currentX = xForHour(currentHour);
  const currentBandX = Math.max(left, currentX - halfStep);
  const currentBandWidth = Math.min(left + plotWidth, currentX + halfStep) - currentBandX;
  const tickStep = (yMax - yMin) / 4;
  const yTicks = Array.from({ length: 5 }, (_, index) => yMax - tickStep * index);
  const xTicks = Array.from(new Set([0, 2, 4, 8, currentHour, 12, 16, 20, 23]))
    .filter(hour => hour >= 0 && hour <= 23)
    .sort((a, b) => a - b);

  return `
    <div class="station-detail-svg-wrap">
      <svg viewBox="0 0 ${width} ${height}" role="img">
        <rect x="0" y="0" width="${width}" height="${height}" rx="16" class="chart-bg"></rect>
        <rect x="${left}" y="${top}" width="${Math.max(0, currentBandX - left).toFixed(1)}" height="${plotHeight}" class="chart-zone-past"></rect>
        <rect x="${currentBandX.toFixed(1)}" y="${top}" width="${currentBandWidth.toFixed(1)}" height="${plotHeight}" class="chart-zone-current"></rect>
        <rect x="${(currentX + halfStep).toFixed(1)}" y="${top}" width="${Math.max(0, left + plotWidth - (currentX + halfStep)).toFixed(1)}" height="${plotHeight}" class="chart-zone-future"></rect>

        ${yTicks.map(value => `
          <line x1="${left}" y1="${clampY(value).toFixed(1)}" x2="${left + plotWidth}" y2="${clampY(value).toFixed(1)}" class="chart-grid-line"></line>
          <text x="${left - 12}" y="${(clampY(value) + 4).toFixed(1)}" text-anchor="end" class="chart-axis-label">${value.toFixed(config.unit === "s" ? 1 : 0)}${config.unit}</text>
        `).join("")}

        ${xTicks.map(hour => `
          <text x="${xForHour(hour).toFixed(1)}" y="${height - 12}" text-anchor="middle" class="chart-axis-label ${hour === currentHour ? "chart-current-axis-label" : ""}">${String(hour).padStart(2, "0")}</text>
        `).join("")}

        <line x1="${left}" y1="${standardY.toFixed(1)}" x2="${left + plotWidth}" y2="${standardY.toFixed(1)}" class="detail-standard-line"></line>
        <text x="${left + 6}" y="${(standardY - 8).toFixed(1)}" class="detail-standard-label">${escapeHtml(config.standardLabel)}</text>

        <polygon points="${areaPoints}" class="detail-chart-area"></polygon>
        ${pastPoints ? `<polyline points="${pastPoints}" class="detail-chart-line-past"></polyline>` : ""}
        ${futurePoints ? `<polyline points="${futurePoints}" class="detail-chart-line-future"></polyline>` : ""}
        <line x1="${currentX.toFixed(1)}" y1="${top}" x2="${currentX.toFixed(1)}" y2="${top + plotHeight}" class="chart-current-line"></line>
        <text x="${(currentX + 5).toFixed(1)}" y="${top + 14}" class="chart-current-label">Current ${String(currentHour).padStart(2, "0")}:00</text>

        <circle cx="${lastX.toFixed(1)}" cy="${lastY.toFixed(1)}" r="6" class="chart-current-point"></circle>
        <text x="${(lastX - 8).toFixed(1)}" y="${(lastY - 10).toFixed(1)}" text-anchor="end" class="chart-last-label">${formatMetricValue(lastPoint[config.metricKey], config.unit)}</text>
        ${renderSvgHoverPoints({
          series: config.series,
          xForHour,
          yForValue,
          metricKey: config.metricKey,
          valueFormatter: value => formatMetricValue(value, config.unit),
          plotTop: top,
          plotBottom: top + plotHeight,
          plotLeft: left,
          plotRight: left + plotWidth
        })}
        <text x="${left + plotWidth}" y="${height - 12}" text-anchor="end" class="chart-axis-label">time</text>
      </svg>
    </div>
  `;
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
      註：目前資料由 MOCK_DATABASE_RESPONSE 模擬 web service 回傳；站別風險由 stationTelemetry 與 baseline 比較產生。
    </div>
  `;
}

function renderDecisionEvidenceCards(content) {
  return `
    <section class="evidence-panel">
      <p class="content-section-kicker">判斷依據</p>
      <h3>判斷依據：主管決策來源</h3>
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

function renderCauseCards(content) {
  return `
    <section class="evidence-panel">
      <p class="content-section-kicker">判斷依據</p>
      <h3>判斷依據：異常原因 Top ${content.causes.length}</h3>
      <div class="decision-evidence-grid">
        ${content.causes.map((cause, index) => `
          <article class="decision-evidence-card">
            <div class="decision-evidence-label">原因 ${index + 1}</div>
            <div class="decision-evidence-answer negative-text">${escapeHtml(MANAGER_MOCK_SUMMARY.mainIssueStation)}</div>
            <p class="decision-evidence-text">${escapeHtml(cause)}</p>
            <div class="decision-evidence-status">stationTelemetry vs baseline</div>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderImpactCards(content, title = "判斷依據：本週預估損失") {
  return `
    <section class="evidence-panel">
      <p class="content-section-kicker">判斷依據</p>
      <h3>${escapeHtml(title)}</h3>
      <div class="impact-card-grid">
        ${content.cards.map(item => `
          <article class="impact-card ${escapeHtml(item.tone)}">
            <div class="impact-label">${escapeHtml(item.label)}</div>
            <div class="impact-value ${changeClass(item.value)}">${escapeHtml(item.value)}</div>
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
      <h3>判斷依據：站別工程師與驗收條件</h3>
      <div class="progress-card-grid">
        ${content.assignments.map(item => `
          <article class="progress-card">
            <div class="progress-head">
              <span class="assignment-priority">${escapeHtml(item.priority)}</span>
              <span class="assignment-status ${assignmentStatusClass(item.status)}">${escapeHtml(item.status)}</span>
            </div>
            <h4>${escapeHtml(item.owner)}</h4>
            <p><strong>站別：</strong>${escapeHtml(item.station)} / ${escapeHtml(item.processLayer)}</p>
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
            <div class="validation-row"><span>昨日預測 / 輸入</span><strong>${escapeHtml(item.predicted)}</strong></div>
            <div class="validation-row"><span>今日 QC 後實際</span><strong>${escapeHtml(item.actual)}</strong></div>
            <div class="validation-row"><span>誤差 / 狀態</span><strong class="${changeClass(item.error)}">${escapeHtml(item.error)}</strong></div>
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


