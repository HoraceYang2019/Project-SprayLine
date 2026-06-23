const AUTO_REFRESH_MS = 15000;
let currentMode = "time";
let autoUpdate = true;
let latestPayload = null;
const openProcess = new Set();
const openImage = new Set();
const openTrend = new Map();
const openDetail = new Map();

const COMPONENT_KEYS = [
    ["arm", "機械手臂"], ["nozzle", "噴嘴"], ["air", "空壓機"],
    ["width", "噴幅"], ["filter", "濾網"], ["quality", "品質"]
];

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[ch]));
}
function sliderValue() { return Number(document.getElementById("timeSlider").value); }
function stateInfo(overall) {
    if (overall === "Alarm") return { className: "alarm", label: "異常" };
    if (overall === "Maintenance") return { className: "maintenance", label: "注意" };
    return { className: "running", label: "運行中" };
}
function levelClass(level) { return level === "bad" ? "fault" : level === "warn" ? "warning" : "normal"; }

async function fetchJson(url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
}

function updateSummary(summary) {
    document.getElementById("totalCount").textContent = summary.total_station_count ?? 0;
    document.getElementById("normalCount").textContent = summary.normal_count ?? 0;
    document.getElementById("warningCount").textContent = summary.warning_count ?? 0;
    document.getElementById("riskCount").textContent = summary.predict_risk_count ?? 0;
}

function componentCards(station) {
    return station.components.map(component => `
        <div class="component-mini ${escapeHtml(component.level)}" onclick="showComponentDetail('${station.id}','${component.key}')">
            <div class="component-icon">${escapeHtml(component.icon)}</div>
            <div class="component-name">${escapeHtml(component.name)}</div>
            <div class="component-en">${escapeHtml(component.en)}</div>
            <div class="component-value">${escapeHtml(component.value)}</div>
            <div class="component-status">${escapeHtml(component.status_text)}</div>
            <div class="component-hint">${component.level === "ok" ? "狀態穩定" : "點擊查看原因"}</div>
        </div>
    `).join("");
}

function processPanel(station) {
    return `
        <div class="section-title">製程參數 ProcessParameters</div>
        <div class="metric-grid">
            <div class="metric"><span>配方 Recipe</span><strong>${escapeHtml(station.recipe)}</strong></div>
            <div class="metric"><span>溫度 Temperature</span><strong>${Number(station.temperature).toFixed(1)}°C</strong></div>
            <div class="metric"><span>濕度 Humidity</span><strong>${Number(station.humidity).toFixed(1)}%RH</strong></div>
            <div class="metric"><span>利用率 Utilization</span><strong>${escapeHtml(station.utilization)}%</strong></div>
            <div class="metric"><span>週期時間 CycleTime</span><strong>${escapeHtml(station.cycle)} sec</strong></div>
            <div class="metric"><span>資料時間 Timestamp</span><strong style="font-size:13px">${new Date(station.timestamp).toLocaleString("zh-TW", {hour12:false})}</strong></div>
        </div>`;
}

function sprayImage(station) {
    const width = Number(station.sprayWidth);
    const min = Number(station.targetMin);
    const max = Number(station.targetMax);
    const component = station.components.find(item => item.key === "width");
    const color = component.level === "bad" ? "#c62828" : component.level === "warn" ? "#ef6c00" : "#2e7d32";
    const display = Math.max(70, Math.min(145, width));
    const left = 180 - display * 0.65;
    const right = 180 + display * 0.65;
    return `
        <div class="section-title">噴幅影像 SprayWidthImage</div>
        <div class="spray-inner">
            <svg viewBox="0 0 360 230" class="spray-svg">
                <rect width="360" height="230" rx="16" fill="#f7f9fa"/>
                <text x="20" y="28" font-size="14" font-weight="bold" fill="#263238">噴幅影像 SprayWidthImage</text>
                <rect x="286" y="12" width="52" height="24" rx="12" fill="${color}"/>
                <text x="312" y="29" text-anchor="middle" font-size="12" font-weight="bold" fill="white">${component.status_text}</text>
                <rect x="18" y="45" width="324" height="160" rx="12" fill="white" stroke="#dfe6e9"/>
                <rect x="164" y="60" width="32" height="20" rx="5" fill="#455a64"/>
                <polygon points="180,80 170,96 190,96" fill="#455a64"/>
                <polygon points="180,96 ${left},165 ${right},165" fill="rgba(25,118,210,.18)" stroke="${color}" stroke-width="3"/>
                <rect x="112" y="145" width="136" height="18" rx="8" fill="rgba(46,125,50,.1)" stroke="#2e7d32" stroke-dasharray="5 4"/>
                <text x="180" y="139" text-anchor="middle" font-size="12" fill="#2e7d32">B版正常範圍 ${min}～${max}mm</text>
                <line x1="${left}" y1="164" x2="${left}" y2="180" stroke="${color}" stroke-width="3"/>
                <line x1="${right}" y1="164" x2="${right}" y2="180" stroke="${color}" stroke-width="3"/>
                <line x1="${left}" y1="176" x2="${right}" y2="176" stroke="#263238" stroke-width="2"/>
                <text x="180" y="195" text-anchor="middle" font-size="14" font-weight="bold" fill="#263238">目前噴幅：${width.toFixed(1)}mm</text>
            </svg>
            <div class="spray-note">本區保留 UI_V5 的單點噴幅圖；趨勢圖則用來觀察過去、現在與未來的連續變化。</div>
        </div>`;
}

function trendPanel(stationId) {
    const active = openTrend.get(stationId) || "width";
    const tabs = COMPONENT_KEYS.map(([key, label]) => `<button class="trend-tab ${key === active ? "active" : ""}" onclick="loadTrend('${stationId}','${key}')">${label}</button>`).join("");
    return `
        <div class="section-title">狀態趨勢 TrendViewer</div>
        <div class="trend-inner">
            <div class="trend-tabs">${tabs}</div>
            <div class="trend-chart-wrap" id="trend-chart-${stationId}">趨勢資料載入中...</div>
            <div class="trend-legend">
                <span><i class="legend-line"></i>過去與現在</span>
                <span><i class="legend-line future"></i>未來預測</span>
                <span><i class="legend-dot" style="background:#2e7d32"></i>正常</span>
                <span><i class="legend-dot" style="background:#ef6c00"></i>注意</span>
                <span><i class="legend-dot" style="background:#c62828"></i>異常</span>
            </div>
            <div class="source-note" id="trend-note-${stationId}"></div>
        </div>`;
}

function renderStations(stations) {
    const area = document.getElementById("stationArea");
    area.innerHTML = "";
    stations.forEach(station => {
        const state = stateInfo(station.overall);
        const issues = station.components.filter(item => item.level !== "ok");
        const hasBad = issues.some(item => item.level === "bad");
        const card = document.createElement("article");
        card.className = `station-card ${state.className}`;
        card.innerHTML = `
            <div class="station-title"><div><h2>${escapeHtml(station.name)}</h2><p>${escapeHtml(station.englishName)}</p></div><div class="status-badge">${state.label}</div></div>
            <div class="component-wrap"><div class="section-title">零件狀態 PartStatus</div><div class="component-overview">${componentCards(station)}</div></div>
            <div class="action-row">
                <button class="toggle-btn ${hasBad ? "danger" : issues.length ? "warn" : "success"}" onclick="showStationDetail('${station.id}')">${issues.length ? "查看異常原因與改善 FaultDetail" : "零件正常 NoFault"}</button>
                <button id="process-btn-${station.id}" class="toggle-btn ${openProcess.has(station.id) ? "process-active" : ""}" onclick="togglePanel('process','${station.id}')">製程參數 ProcessParameters</button>
                <button id="image-btn-${station.id}" class="toggle-btn ${openImage.has(station.id) ? "image-active" : ""}" onclick="togglePanel('image','${station.id}')">噴幅影像 SprayWidthImage</button>
                <button id="trend-btn-${station.id}" class="toggle-btn ${openTrend.has(station.id) ? "trend-active" : ""}" onclick="toggleTrend('${station.id}')">趨勢圖 TrendChart</button>
            </div>
            <div class="detail-panel" id="detail-${station.id}"></div>
            <div class="process-panel ${openProcess.has(station.id) ? "visible" : ""}" id="process-${station.id}">${processPanel(station)}</div>
            <div class="spray-panel ${openImage.has(station.id) ? "visible" : ""}" id="image-${station.id}">${sprayImage(station)}</div>
            <div class="trend-panel ${openTrend.has(station.id) ? "visible" : ""}" id="trend-${station.id}">${trendPanel(station.id)}</div>`;
        area.appendChild(card);
    });

    for (const [stationId, detailInfo] of openDetail.entries()) {
        if (detailInfo.type === "station") showStationDetail(stationId, true);
        else showComponentDetail(stationId, detailInfo.componentKey, true);
    }
    for (const [stationId, componentKey] of openTrend.entries()) loadTrend(stationId, componentKey);
}

function faultCard(component) {
    const cls = levelClass(component.level);
    return `<div class="fault-card ${cls}">
        <div class="detail-title ${cls}">${escapeHtml(component.name)} ${escapeHtml(component.en)}｜${escapeHtml(component.status_text)}</div>
        <div class="fault-line"><span class="fault-label">目前數值：</span><span>${escapeHtml(component.value)}</span></div>
        <div class="fault-line"><span class="fault-label">判斷來源：</span><span>${escapeHtml(component.status_source_sensor || "-")} ${component.status_source_value ?? ""}</span></div>
        <div class="fault-line"><span class="fault-label">問題說明：</span><span>${escapeHtml(component.issue)}</span></div>
        <div class="fault-line"><span class="fault-label">可能原因：</span><span>${escapeHtml(component.reason)}</span></div>
        <div class="fault-line"><span class="fault-label">處理建議：</span><span>${escapeHtml(component.solution)}</span></div>
        <div class="source-note">issue_state：${escapeHtml(component.issue_state || "-")}｜cause_id：${escapeHtml(component.cause_id || "-")}｜response_ids：${escapeHtml((component.response_ids || []).join(", ") || "-")}</div>
    </div>`;
}

async function showComponentDetail(stationId, componentKey, restoring = false) {
    const panel = document.getElementById(`detail-${stationId}`);
    if (!restoring && openDetail.get(stationId)?.type === "component" && openDetail.get(stationId)?.componentKey === componentKey) {
        openDetail.delete(stationId); panel.className = "detail-panel"; panel.innerHTML = ""; return;
    }
    try {
        const url = `/api/component-detail?station_id=${encodeURIComponent(stationId)}&component_key=${encodeURIComponent(componentKey)}&mode=${currentMode}&slider_value=${sliderValue()}`;
        const data = await fetchJson(url);
        openDetail.set(stationId, { type: "component", componentKey });
        const component = data.component;
        panel.className = `detail-panel visible ${levelClass(component.level)}`;
        panel.innerHTML = `<div class="detail-title ${levelClass(component.level)}">${escapeHtml(data.station.name)}｜零件狀態說明</div>${faultCard(component)}<button class="toggle-btn" onclick="closeDetail('${stationId}')">收起 Close</button><div class="source-note">Detail來源：${escapeHtml(data.detail_source)}</div>`;
    } catch (error) { panel.className = "detail-panel visible fault"; panel.innerHTML = `<div class="error-panel">讀取零件詳細資料失敗：${escapeHtml(error.message)}</div>`; }
}

async function showStationDetail(stationId, restoring = false) {
    const panel = document.getElementById(`detail-${stationId}`);
    if (!restoring && openDetail.get(stationId)?.type === "station") { closeDetail(stationId); return; }
    try {
        const url = `/api/station-detail?station_id=${encodeURIComponent(stationId)}&mode=${currentMode}&slider_value=${sliderValue()}`;
        const data = await fetchJson(url);
        openDetail.set(stationId, { type: "station" });
        const issues = data.issues || [];
        const worst = issues.some(item => item.level === "bad") ? "fault" : issues.length ? "warning" : "normal";
        panel.className = `detail-panel visible ${worst}`;
        panel.innerHTML = `<div class="detail-title ${worst}">${escapeHtml(data.station.name)}｜${issues.length ? "異常與注意原因及改善建議" : "目前無異常"}</div>${issues.length ? issues.map(faultCard).join("") : `<div class="fault-card"><div class="fault-line"><span class="fault-label">狀態：</span><span>所有零件目前皆位於正常範圍。</span></div></div>`}<button class="toggle-btn" onclick="closeDetail('${stationId}')">收起 Close</button><div class="source-note">Detail來源：${escapeHtml(data.detail_source)}</div>`;
    } catch (error) { panel.className = "detail-panel visible fault"; panel.innerHTML = `<div class="error-panel">讀取整站詳細資料失敗：${escapeHtml(error.message)}</div>`; }
}

function closeDetail(stationId) { openDetail.delete(stationId); const panel = document.getElementById(`detail-${stationId}`); if (panel) { panel.className = "detail-panel"; panel.innerHTML = ""; } }

function togglePanel(type, stationId) {
    const set = type === "process" ? openProcess : openImage;
    const panel = document.getElementById(`${type}-${stationId}`);
    const btn = document.getElementById(`${type}-btn-${stationId}`);
    if (set.has(stationId)) { set.delete(stationId); panel.classList.remove("visible"); btn.classList.remove(type === "process" ? "process-active" : "image-active"); }
    else { set.add(stationId); panel.classList.add("visible"); btn.classList.add(type === "process" ? "process-active" : "image-active"); }
}

function toggleTrend(stationId) {
    const panel = document.getElementById(`trend-${stationId}`);
    const btn = document.getElementById(`trend-btn-${stationId}`);
    if (openTrend.has(stationId)) { openTrend.delete(stationId); panel.classList.remove("visible"); btn.classList.remove("trend-active"); }
    else { openTrend.set(stationId, "width"); panel.classList.add("visible"); btn.classList.add("trend-active"); loadTrend(stationId, "width"); }
}

async function loadTrend(stationId, componentKey) {
    openTrend.set(stationId, componentKey);
    const panel = document.getElementById(`trend-${stationId}`);
    if (!panel) return;
    panel.innerHTML = trendPanel(stationId);
    const chart = document.getElementById(`trend-chart-${stationId}`);
    try {
        const data = await fetchJson(`/api/trend-data?station_id=${encodeURIComponent(stationId)}&component_key=${encodeURIComponent(componentKey)}`);
        renderTrendChart(chart, data);
        const note = document.getElementById(`trend-note-${stationId}`);
        const source = data.threshold_reference?.source || "此欄位無B版門檻，僅顯示數值趨勢";
        note.textContent = `資料來源：${data.source}｜門檻來源：${source}`;
    } catch (error) { chart.innerHTML = `<div class="error-panel">趨勢圖讀取失敗：${escapeHtml(error.message)}</div>`; }
}

function updateTimeline(payload) {
    const viewer = payload.viewer_state;
    document.getElementById("selectedTimeText").textContent = `目前時間點：${viewer.display_label}`;
    document.getElementById("timelineResult").innerHTML = `<b>選取時間：</b>${new Date(viewer.selected_time).toLocaleString("zh-TW", {hour12:false})}<br><b>顯示方式：</b>${viewer.time_type === "past" ? "歷史單點" : viewer.time_type === "future" ? "未來預測單點" : "目前即時單點"}<br><b>補充：</b>每站的「趨勢圖 TrendChart」會同時顯示過去6小時、現在與未來2小時。`;
    ["past", "now", "future"].forEach(key => document.getElementById(`${key}Chip`).classList.remove("active"));
    document.getElementById(viewer.time_type === "past" ? "pastChip" : viewer.time_type === "future" ? "futureChip" : "nowChip").classList.add("active");
}

function updateHeader(payload) {
    document.getElementById("updateTime").textContent = `最後更新時間：${new Date(payload.generated_at).toLocaleString("zh-TW", {hour12:false})}`;
    const _dbEnabled = payload.integration && payload.integration.database_enabled;
    const _srcLabel = _dbEnabled ? 'API 即時資料' : '本機動態模擬資料';
    const _dbLabel  = _dbEnabled ? '已連接 API · 即時資料' : '本機模擬資料';
    document.getElementById("sourceStatus").innerHTML = `<b>目前來源：</b>${_srcLabel}　｜　<b>套用：</b>少榆0616_B版站別、感測欄位、threshold 與 mapping　｜　<b>新增：</b>單點狀態 + 過去/現在/未來趨勢圖　｜　<b>資料庫：</b>${_dbLabel}`;
    const badge = document.getElementById("liveStatusBadge");
    if (autoUpdate && sliderValue() === 0) { badge.className = "live-badge"; badge.textContent = "即時更新中｜每15秒"; }
    else { badge.className = "pause-badge"; badge.textContent = "時間軸檢視中"; }
}

async function refreshDashboard() {
    try {
        const payload = await fetchJson(`/api/dashboard-data?mode=${currentMode}&slider_value=${sliderValue()}`);
        latestPayload = payload;
        updateHeader(payload); updateSummary(payload.summary); renderStations(payload.stations); updateTimeline(payload);
    } catch (error) {
        document.getElementById("stationArea").innerHTML = `<div class="error-panel">Dashboard資料讀取失敗：${escapeHtml(error.message)}<br>請確認 uvicorn 已啟動。</div>`;
    }
}

function handleSliderChange() { autoUpdate = sliderValue() === 0; refreshDashboard(); }
function backToLive() { document.getElementById("timeSlider").value = 0; autoUpdate = true; refreshDashboard(); }
function setMode(mode) {
    currentMode = mode;
    const slider = document.getElementById("timeSlider");
    if (mode === "time") {
        slider.min = -6; slider.max = 4; slider.step = 1; slider.value = 0;
        document.getElementById("sliderLabels").className = "time-labels time-mode";
        document.getElementById("sliderLabels").innerHTML = `<span class="left-label">過去6小時</span><span class="now-label">現在</span><span class="right-label">未來2小時</span>`;
    } else {
        slider.min = -10; slider.max = 10; slider.step = 1; slider.value = 0;
        document.getElementById("sliderLabels").className = "time-labels batch-mode";
        document.getElementById("sliderLabels").innerHTML = `<span class="left-label">過去10批</span><span class="now-label">目前批次</span><span class="right-label">未來10批</span>`;
    }
    document.getElementById("timeModeBtn").classList.toggle("active", mode === "time");
    document.getElementById("batchModeBtn").classList.toggle("active", mode === "batch");
    autoUpdate = true; refreshDashboard();
}

refreshDashboard();
setInterval(() => {
    if (autoUpdate && sliderValue() === 0) refreshDashboard();
    else if (latestPayload) updateHeader(latestPayload);
}, AUTO_REFRESH_MS);
