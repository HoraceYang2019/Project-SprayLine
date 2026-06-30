function setTrendDrawerOpen(open, stationId = null, metricKey = null) {
  isTrendDrawerOpen = Boolean(open);
  activeTrendDrawer = isTrendDrawerOpen ? { stationId, metricKey } : null;
  renderTrendDrawer();
}

function renderTrendDrawer() {
  const panel = document.getElementById("recommendationPanel");
  const overlay = document.getElementById("drawerOverlay");
  if (!panel || !overlay) return;

  if (!isTrendDrawerOpen || !activeTrendDrawer) {
    panel.classList.remove("open");
    panel.setAttribute("aria-hidden", "true");
    panel.innerHTML = "";
    overlay.classList.remove("open");
    document.body.classList.remove("drawer-open");
    return;
  }

  const metric = getTrendDrawerMetricData(activeTrendDrawer.stationId, activeTrendDrawer.metricKey);
  if (!metric) {
    panel.classList.remove("open");
    panel.setAttribute("aria-hidden", "true");
    panel.innerHTML = "";
    overlay.classList.remove("open");
    document.body.classList.remove("drawer-open");
    return;
  }

  panel.innerHTML = buildTrendDrawerMarkup(metric, activeTrendDrawer.stationId);
  panel.classList.add("open");
  panel.setAttribute("aria-hidden", "false");
  overlay.classList.add("open");
  document.body.classList.add("drawer-open");
}

function buildTrendDrawerMarkup(metric, stationId) {
  return `
    <div class="trend-drawer-head">
      <div>
        <p class="section-kicker">趨勢圖</p>
        <h2>${escapeHtml(metric.title || getTrendDrawerStationTitle(stationId))}</h2>
        <p class="trend-drawer-mode">模式：${escapeHtml(metric.modeLabel || getSelectedBatchLabel())}</p>
      </div>
      <button type="button" class="drawer-close-btn" id="trendDrawerCloseBtn" aria-label="關閉趨勢圖">關閉</button>
    </div>
    <div class="trend-summary-grid">
      ${(metric.summaryItems || []).map(item => `
        <article class="trend-summary-card">
          <span>${escapeHtml(item.label || "-")}</span>
          <strong>${escapeHtml(item.value || "—")}</strong>
        </article>
      `).join("")}
    </div>
    <div class="trend-chart-card">
      ${renderTrendChartSvg(metric)}
    </div>
  `;
}

function renderTrendChartSvg(metric) {
  const series = Array.isArray(metric.series) ? metric.series : [];
  const numericPoints = series.filter(item => Number.isFinite(Number(item?.value)));
  if (!numericPoints.length) {
    return `<div class="trend-empty-state">目前沒有可顯示的趨勢資料。</div>`;
  }

  const width = 860;
  const height = 320;
  const left = 50;
  const right = 22;
  const top = 24;
  const bottom = 44;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const minValue = Math.min(...numericPoints.map(point => Number(point.value)));
  const maxValue = Math.max(...numericPoints.map(point => Number(point.value)));
  const yMin = minValue === maxValue ? minValue - 1 : minValue;
  const yMax = minValue === maxValue ? maxValue + 1 : maxValue;
  const xForHour = hour => left + (Number(hour || 0) / 23) * plotWidth;
  const yForValue = value => top + ((yMax - Number(value || 0)) / (yMax - yMin)) * plotHeight;
  const linePoints = numericPoints
    .map(point => `${xForHour(point.hour).toFixed(1)},${yForValue(point.value).toFixed(1)}`)
    .join(" ");
  const areaPoints = `${left},${top + plotHeight} ${linePoints} ${left + plotWidth},${top + plotHeight}`;
  const yTicks = Array.from({ length: 5 }, (_, index) => {
    const ratio = index / 4;
    const value = yMax - (yMax - yMin) * ratio;
    return {
      value,
      y: top + plotHeight * ratio
    };
  });

  return `
    <svg class="trend-chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(metric.title || "Trend chart")}">
      <rect x="0" y="0" width="${width}" height="${height}" rx="18" class="trend-chart-bg"></rect>
      ${yTicks.map(tick => `
        <g>
          <line x1="${left}" y1="${tick.y.toFixed(1)}" x2="${left + plotWidth}" y2="${tick.y.toFixed(1)}" class="trend-grid-line"></line>
          <text x="${left - 10}" y="${(tick.y + 4).toFixed(1)}" text-anchor="end" class="trend-axis-label">${escapeHtml(Number(tick.value).toFixed(1))}</text>
        </g>
      `).join("")}
      ${Array.from({ length: 24 }, (_, hour) => `
        <text x="${xForHour(hour).toFixed(1)}" y="${height - 14}" text-anchor="middle" class="trend-axis-label">
          ${hour.toString().padStart(2, "0")}
        </text>
      `).join("")}
      <polygon points="${areaPoints}" class="trend-area"></polygon>
      <polyline points="${linePoints}" class="trend-line"></polyline>
      ${numericPoints.map(point => `
        <circle cx="${xForHour(point.hour).toFixed(1)}" cy="${yForValue(point.value).toFixed(1)}" r="4.5" class="trend-point">
          <title>${escapeHtml(point.hourLabel || `${String(point.hour).padStart(2, "0")}:00`)} | ${escapeHtml(formatMetricValue(metric.metricKey, point.value))}</title>
        </circle>
      `).join("")}
    </svg>
  `;
}
