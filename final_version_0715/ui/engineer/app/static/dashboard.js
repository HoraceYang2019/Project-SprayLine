console.log("UI_V27 dashboard.js loaded: status first + trend below + slider sync");
const AUTO_REFRESH_MS = 15000;
let currentMode = "time";
let autoUpdate = true;
let latestPayload = null;
const openProcess = new Set();
const openImage = new Set();
const openTrend = new Map();
const openDetail = new Map();
let dashboardRequestSeq = 0;
const trendRequestSeq = new Map();
let sliderRefreshTimer = null;

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
    const text = await response.text();
    let payload = null;
    try { payload = text ? JSON.parse(text) : {}; } catch (_) { payload = { detail: text }; }
    if (!response.ok) throw new Error(payload?.detail || `HTTP ${response.status}`);
    return payload;
}

function safeNumber(value, digits = 1, suffix = "") {
    const number = Number(value);
    return Number.isFinite(number) ? `${number.toFixed(digits)}${suffix}` : "--";
}

function snapshotSeed() {
    return Number(latestPayload?.snapshot_seed || 0);
}

function updateSummary(summary) {
    document.getElementById("totalCount").textContent = summary.total_station_count ?? 0;
    document.getElementById("normalCount").textContent = summary.normal_count ?? 0;
    document.getElementById("warningCount").textContent = summary.warning_count ?? 0;
    document.getElementById("riskCount").textContent = summary.predict_risk_count ?? 0;
}

function componentCards(station) {
    return station.components.map(component => {
        const selected = openTrend.get(station.id) === component.key ? "trend-selected" : "";
        const hint = component.level === "ok" ? "點擊查看狀態與趨勢" : "點擊查看原因與趨勢";
        return `
        <div id="component-${station.id}-${component.key}"
             class="component-mini ${escapeHtml(component.level)} ${selected}"
             data-station-id="${station.id}"
             data-component-key="${component.key}"
             onclick="handleComponentClick('${station.id}','${component.key}')">
            <div class="component-icon">${escapeHtml(component.icon)}</div>
            <div class="component-name">${escapeHtml(component.name)}</div>
            <div class="component-en">${escapeHtml(component.en)}</div>
            <div class="component-value">${escapeHtml(component.value)}</div>
            <div class="component-status">${escapeHtml(component.status_text)}</div>
            <div class="component-hint">${hint}</div>
        </div>`;
    }).join("");
}

function processPanel(station) {
    return `
        <div class="section-title">製程參數 ProcessParameters</div>
        <div class="metric-grid">
            <div class="metric"><span>配方 Recipe</span><strong>${escapeHtml(station.recipe)}</strong></div>
            <div class="metric"><span>溫度 Temperature</span><strong>${safeNumber(station.temperature, 1, "°C")}</strong></div>
            <div class="metric"><span>濕度 Humidity</span><strong>${safeNumber(station.humidity, 1, "%RH")}</strong></div>
            <div class="metric"><span>利用率 Utilization</span><strong>${safeNumber(station.utilization, 1, "%")}</strong></div>
            <div class="metric"><span>週期時間 CycleTime</span><strong>${safeNumber(station.cycle, 0, " sec")}</strong></div>
            <div class="metric"><span>資料時間 Timestamp</span><strong style="font-size:13px">${station.timestamp ? new Date(station.timestamp).toLocaleString("zh-TW", {hour12:false}) : "--"}</strong></div>
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
            <div class="trend-selected-summary">點選零件後會自動切換到對應趨勢；下方頁籤仍可自由查看其他零件。</div>
            <div class="trend-tabs">${tabs}</div>
            <div class="trend-chart-wrap" id="trend-chart-${stationId}">趨勢資料載入中...</div>
            <div class="trend-legend">
                <span><i class="legend-line"></i>過去與現在</span>
                <span><i class="legend-line future"></i>未來預測</span>
                <span><i class="legend-dot" style="background:#2e7d32"></i>正常</span>
                <span><i class="legend-dot" style="background:#ef6c00"></i>注意</span>
                <span><i class="legend-dot" style="background:#c62828"></i>異常</span>
                <span><i class="legend-ring"></i>上方卡片時間點</span>
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
            <div class="trend-panel ${openTrend.has(station.id) ? "visible" : ""}" id="trend-${station.id}">${trendPanel(station.id)}</div>
            <div class="process-panel ${openProcess.has(station.id) ? "visible" : ""}" id="process-${station.id}">${processPanel(station)}</div>
            <div class="spray-panel ${openImage.has(station.id) ? "visible" : ""}" id="image-${station.id}">${sprayImage(station)}</div>`;
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

function stationFromCurrentSnapshot(stationId) {
    return latestPayload?.stations?.find(item => item.id === stationId) || null;
}


function ensureDetailBeforeTrend(stationId) {
    const detail = document.getElementById(`detail-${stationId}`);
    const trend = document.getElementById(`trend-${stationId}`);
    if (detail && trend && detail.compareDocumentPosition(trend) & Node.DOCUMENT_POSITION_PRECEDING) {
        trend.parentNode.insertBefore(detail, trend);
    }
}

function handleComponentClick(stationId, componentKey) {
    // V27: 點零件時「狀態說明」先顯示，TrendChart 同步打開但放在狀態說明下方。
    // 不再自動捲到趨勢圖，避免使用者以為狀態說明沒有先出來。
    showComponentDetail(stationId, componentKey);
    showTrendForComponent(stationId, componentKey, false);
    setTimeout(() => {
        const target = document.getElementById(`detail-${stationId}`);
        if (target) target.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }, 120);
}

function showTrendForComponent(stationId, componentKey, scrollIntoView = false) {
    const panel = document.getElementById(`trend-${stationId}`);
    const btn = document.getElementById(`trend-btn-${stationId}`);
    if (!panel || !btn) return;
    openTrend.set(stationId, componentKey);
    panel.classList.add("visible");
    btn.classList.add("trend-active");
    loadTrend(stationId, componentKey);
    if (scrollIntoView) {
        setTimeout(() => {
            const target = document.getElementById(`trend-${stationId}`);
            if (target) target.scrollIntoView({ behavior: "smooth", block: "center" });
        }, 120);
    }
}

function updateSelectedComponentCard(stationId, componentKey) {
    document.querySelectorAll(`.component-mini[data-station-id="${stationId}"]`).forEach(card => {
        card.classList.toggle("trend-selected", card.dataset.componentKey === componentKey);
    });
}
function syncComponentDetailToDashboard(stationId, componentKey, component) {
    if (!latestPayload || !latestPayload.stations) return;

    const station = latestPayload.stations.find(item => item.id === stationId);
    if (!station || !station.components) return;

    const target = station.components.find(item => item.key === componentKey);
    if (!target) return;

    // 1. 把 component-detail 回傳的最新資料寫回 latestPayload
    Object.assign(target, component);

    // 2. 同步更新上方零件卡片 DOM
    const card = document.getElementById(`component-${stationId}-${componentKey}`);
    if (card) {
        card.classList.remove("ok", "warn", "bad", "normal", "warning", "fault");
        card.classList.add(component.level || "ok");

        const valueEl = card.querySelector(".component-value");
        const statusEl = card.querySelector(".component-status");
        const hintEl = card.querySelector(".component-hint");

        if (valueEl) valueEl.textContent = component.value || "--";
        if (statusEl) statusEl.textContent = component.status_text || "--";
        if (hintEl) {
            hintEl.textContent = component.level === "ok"
                ? "點擊查看狀態與趨勢"
                : "點擊查看原因與趨勢";
        }
    }

    // 3. 用零件狀態重新判斷該站狀態
    const hasBad = station.components.some(item => item.level === "bad");
    const hasWarn = station.components.some(item => item.level === "warn");

    if (hasBad) station.overall = "Alarm";
    else if (hasWarn) station.overall = "Maintenance";
    else station.overall = "Running";

    // 4. 同步更新該站外框與站別 badge
    const stationCard = card ? card.closest(".station-card") : null;
    if (stationCard) {
        const state = stateInfo(station.overall);

        stationCard.classList.remove("running", "maintenance", "alarm");
        stationCard.classList.add(state.className);

        const badge = stationCard.querySelector(".status-badge");
        if (badge) badge.textContent = state.label;

        const issues = station.components.filter(item => item.level !== "ok");
        const firstButton = stationCard.querySelector(".action-row .toggle-btn");

        if (firstButton) {
            firstButton.classList.remove("danger", "warn", "success");

            if (issues.some(item => item.level === "bad")) {
                firstButton.classList.add("danger");
                firstButton.textContent = "查看異常原因與改善 FaultDetail";
            } else if (issues.length) {
                firstButton.classList.add("warn");
                firstButton.textContent = "查看異常原因與改善 FaultDetail";
            } else {
                firstButton.classList.add("success");
                firstButton.textContent = "零件正常 NoFault";
            }
        }
    }

    // 5. 重新計算 Summary
    const summary = {
        total_station_count: latestPayload.stations.length,
        normal_count: 0,
        warning_count: 0,
        predict_risk_count: 0
    };

    latestPayload.stations.forEach(st => {
        if (st.overall === "Alarm") summary.predict_risk_count += 1;
        else if (st.overall === "Maintenance") summary.warning_count += 1;
        else summary.normal_count += 1;
    });

    latestPayload.summary = summary;
    updateSummary(summary);
}
async function showComponentDetail(stationId, componentKey, restoring = false) {
    const panel = document.getElementById(`detail-${stationId}`);
    if (!restoring && openDetail.get(stationId)?.type === "component" && openDetail.get(stationId)?.componentKey === componentKey) {
        openDetail.delete(stationId);
        panel.className = "detail-panel";
        panel.innerHTML = "";
        return;
    }

    openDetail.set(stationId, { type: "component", componentKey });
    panel.className = "detail-panel visible";
    panel.innerHTML = `<div class="loading-panel">正在呼叫 Webservices component-detail function...</div>`;
    try {
        const data = await fetchJson(`/api/component-detail?station_id=${encodeURIComponent(stationId)}&component_key=${encodeURIComponent(componentKey)}&mode=${encodeURIComponent(currentMode)}&slider_value=${encodeURIComponent(sliderValue())}&snapshot_seed=${encodeURIComponent(snapshotSeed())}`);
        const component = data.component;

        // 新增這行：把 component-detail 的結果同步回上方卡片
        syncComponentDetailToDashboard(stationId, componentKey, component);

        panel.className = `detail-panel visible ${levelClass(component.level)}`;
        panel.innerHTML = `<div class="detail-title ${levelClass(component.level)}">${escapeHtml(data.station.name)}｜零件狀態說明</div>${faultCard(component)}<button class="toggle-btn" onclick="closeDetail('${stationId}')">收起 Close</button><div class="source-note">已呼叫：${escapeHtml(data.service_api?.route || data.detail_function)}｜component_name：${escapeHtml(data.service_api?.component_name || component.service_component_name)}｜snapshot_seed：${escapeHtml(data.snapshot_seed)}</div>`;
    } catch (error) {
        panel.className = "detail-panel visible fault";
        panel.innerHTML = `<div class="error-panel">Component Service API 讀取失敗：${escapeHtml(error.message)}</div>`;
    }
}

async function showStationDetail(stationId, restoring = false) {
    const panel = document.getElementById(`detail-${stationId}`);
    if (!restoring && openDetail.get(stationId)?.type === "station") {
        closeDetail(stationId);
        return;
    }

    openDetail.set(stationId, { type: "station" });
    panel.className = "detail-panel visible";
    panel.innerHTML = `<div class="loading-panel">正在呼叫 Webservices station-detail function...</div>`;
    try {
        const data = await fetchJson(`/api/station-detail?station_id=${encodeURIComponent(stationId)}&mode=${encodeURIComponent(currentMode)}&slider_value=${encodeURIComponent(sliderValue())}&snapshot_seed=${encodeURIComponent(snapshotSeed())}`);
        const issues = data.issues || [];
        const worst = issues.some(item => item.level === "bad") ? "fault" : issues.length ? "warning" : "normal";
        panel.className = `detail-panel visible ${worst}`;
        panel.innerHTML = `<div class="detail-title ${worst}">${escapeHtml(data.station.name)}｜${issues.length ? "異常與注意原因及改善建議" : "目前無異常"}</div>${issues.length ? issues.map(faultCard).join("") : `<div class="fault-card"><div class="fault-line"><span class="fault-label">狀態：</span><span>Station Service API 回傳所有零件目前正常。</span></div></div>`}<button class="toggle-btn" onclick="closeDetail('${stationId}')">收起 Close</button><div class="source-note">已呼叫：${escapeHtml(data.service_api?.route || data.detail_function)}｜snapshot_seed：${escapeHtml(data.snapshot_seed)}</div>`;
    } catch (error) {
        panel.className = "detail-panel visible fault";
        panel.innerHTML = `<div class="error-panel">Station Service API 讀取失敗：${escapeHtml(error.message)}</div>`;
    }
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
    if (openTrend.has(stationId)) {
        openTrend.delete(stationId);
        panel.classList.remove("visible");
        btn.classList.remove("trend-active");
        updateSelectedComponentCard(stationId, null);
    } else {
        showTrendForComponent(stationId, openTrend.get(stationId) || "width", true);
    }
}

async function loadTrend(stationId, componentKey) {
    openTrend.set(stationId, componentKey);
    updateSelectedComponentCard(stationId, componentKey);
    const panel = document.getElementById(`trend-${stationId}`);
    if (!panel) return;

    const selectedSlider = sliderValue();
    const selectedSeed = snapshotSeed();
    const requestKey = `${stationId}:${componentKey}`;
    const requestId = `${Date.now()}:${Math.random()}:${selectedSlider}:${selectedSeed}`;
    trendRequestSeq.set(requestKey, requestId);

    panel.innerHTML = trendPanel(stationId);
    const chart = document.getElementById(`trend-chart-${stationId}`);
    if (chart) {
        chart.innerHTML = `<div class="loading-panel">趨勢圖載入中：${escapeHtml(componentKey)}／slider=${escapeHtml(selectedSlider)}</div>`;
    }

    try {
        const data = await fetchJson(`/api/trend-data?station_id=${encodeURIComponent(stationId)}&component_key=${encodeURIComponent(componentKey)}&mode=${encodeURIComponent(currentMode)}&slider_value=${encodeURIComponent(selectedSlider)}&snapshot_seed=${encodeURIComponent(selectedSeed)}`);

        // V27: 避免舊請求比較晚回來，把新時間軸的趨勢圖覆蓋掉。
        if (trendRequestSeq.get(requestKey) !== requestId) return;
        if (sliderValue() !== selectedSlider || openTrend.get(stationId) !== componentKey) return;

        renderTrendChart(chart, data);
        const note = document.getElementById(`trend-note-${stationId}`);
        const source = data.threshold_reference?.source || "此欄位無B版門檻，僅顯示數值趨勢";
        const selected = data.selected_snapshot || {};
        if (note) {
            note.textContent = `已呼叫：${data.service_api?.route || "component-detail"}｜趨勢方式：${data.service_api?.method || "time_series"}｜目前 slider：${selectedSlider}｜圈選點：${selected.display_label || "目前卡片"}／${selected.formatted_value || "--"}｜門檻來源：${source}`;
        }
    } catch (error) {
        if (trendRequestSeq.get(requestKey) !== requestId) return;
        if (chart) chart.innerHTML = `<div class="error-panel">趨勢圖讀取失敗：${escapeHtml(error.message)}</div>`;
    }
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

    const integration = payload.integration || {};
    const received = Boolean(integration.data_received);
    const connected = Boolean(integration.webservices_connected);
    const dbConnected = Boolean(integration.database_connected);
    const cls = received && dbConnected ? "connected" : connected ? "fallback" : "offline";
    const title = document.getElementById("connectionTitle");
    const detail = document.getElementById("connectionDetail");
    const dot = document.getElementById("connectionDot");
    const badgeTop = document.getElementById("wsHeaderBadge");
    if (title && detail && dot && badgeTop) {
        title.textContent = received && dbConnected ? "Webservices 與資料庫皆已連線" : connected ? "Webservices 已連線，但資料庫或站別資料異常" : "Webservices 未連線";
        const stationErrors = integration.station_errors || {};
        const stationErrorText = Object.entries(stationErrors).map(([id, message]) => `${id}: ${message}`).join("｜");
        const dbName = integration.database_status?.database?.name || integration.database_status?.config?.dbname || "-";
        detail.textContent = received
            ? `Summary API：成功｜Station API：${integration.route_status?.station_detail_ok_count || 0}/${integration.route_status?.station_detail_expected_count || 0} 成功｜Component API：點擊零件時呼叫｜模式：${integration.api_mode || "demo"}｜資料庫：${integration.database_connected ? `已連線（${dbName}）` : "未連線"}`
            : `Summary API：${integration.summary_received === false ? "失敗" : "成功"}｜Station API：${integration.route_status?.station_detail_ok_count || 0}/${integration.route_status?.station_detail_expected_count || 0} 成功${stationErrorText ? `｜${stationErrorText}` : ""}｜資料庫：${integration.database_connected ? `已連線（${dbName}）` : "未連線"}`;
        dot.className = `connection-dot ${cls}`;
        badgeTop.className = `local-badge ${cls}`;
        badgeTop.textContent = received && dbConnected ? "Webservices＋資料庫：已連線" : connected ? "Webservices 已連線／資料庫或資料異常" : "Webservices：未連線";
    }

    const badge = document.getElementById("liveStatusBadge");
    if (autoUpdate && sliderValue() === 0) {
        badge.className = "live-badge";
        badge.textContent = "即時更新中｜每15秒";
    } else {
        badge.className = "pause-badge";
        badge.textContent = "時間軸檢視中";
    }
}

async function refreshDashboard() {
    const requestSeq = ++dashboardRequestSeq;
    const selectedSlider = sliderValue();
    try {
        const payload = await fetchJson(`/api/dashboard-data?mode=${currentMode}&slider_value=${selectedSlider}`);
        if (requestSeq !== dashboardRequestSeq || sliderValue() !== selectedSlider) return;
        latestPayload = payload;
        updateHeader(payload);
        updateSummary(payload.summary);
        renderStations(payload.stations || []);
        updateTimeline(payload);
        if (!(payload.stations || []).length && payload.integration?.error) {
            document.getElementById("stationArea").innerHTML = `<div class="error-panel">無法取得 Service API 資料：${escapeHtml(payload.integration.error)}<br>請確認 Webservices 與 PostgreSQL 皆已啟動，並重新執行 CONFIGURE_DATABASE.bat。</div>`;
        }
    } catch (error) {
        if (requestSeq !== dashboardRequestSeq) return;
        document.getElementById("stationArea").innerHTML = `<div class="error-panel">Dashboard資料讀取失敗：${escapeHtml(error.message)}<br>請確認 uvicorn 已啟動。</div>`;
    }
}

function handleSliderChange() {
    autoUpdate = sliderValue() === 0;
    clearTimeout(sliderRefreshTimer);
    sliderRefreshTimer = setTimeout(async () => {
        await refreshDashboard();
        // V27: 時間軸改變後，已開啟的 TrendChart 立即重載，讓圈選點跟 slider_value 同步。
        for (const [stationId, componentKey] of openTrend.entries()) {
            loadTrend(stationId, componentKey);
        }
    }, 120);
}
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

async function loadIntegrationStatus() {
    const title = document.getElementById("connectionTitle");
    const detail = document.getElementById("connectionDetail");
    const dot = document.getElementById("connectionDot");
    const badge = document.getElementById("wsHeaderBadge");
    if (!title || !detail || !dot || !badge) return;
    title.textContent = "Webservices 連線檢查中...";
    detail.textContent = "正在確認 UI → Webservices → PostgreSQL。";
    dot.className = "connection-dot checking";
    badge.className = "local-badge checking";
    try {
        const status = await fetchJson("/api/integration-status");
        const cls = status.data_received && status.database_connected ? "connected" : (status.webservices_connected ? "fallback" : "offline");
        title.textContent = status.label;
        const routes = status.route_status || {};
        const routeText = `Summary:${routes.summary?.ok ? "OK" : "失敗"}／Station:${routes.station_detail?.ok ? "OK" : "失敗"}／Component:${routes.component_detail?.ok ? "OK" : "失敗"}`;
        detail.textContent = `${status.detail}｜${routeText}｜位址：${status.base_url}｜模式：${status.mode}｜資料庫：${status.database_connected ? "已連線" : "未連線"}`;
        dot.className = `connection-dot ${cls}`;
        badge.className = `local-badge ${cls}`;
        badge.textContent = status.data_received && status.database_connected ? "Webservices＋資料庫：已連線" : (status.webservices_connected ? "Webservices 已連線／資料庫或資料異常" : "Webservices：未連線");
    } catch (error) {
        title.textContent = "連線狀態檢查失敗";
        detail.textContent = String(error);
        dot.className = "connection-dot offline";
        badge.className = "local-badge offline";
        badge.textContent = "連線檢查失敗";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    // Dashboard loading already verifies summary + station-detail.
    // Full 3-route validation is intentionally manual to avoid concurrent demo
    // requests changing the global random snapshot during first render.
});
