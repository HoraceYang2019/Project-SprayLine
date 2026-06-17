# UserInterfaceDesign 修改規格文件

**目標**：在現有 diagnosis card 中增加停機時間、技能等級、確認告警按鈕的顯示邏輯
**注意**：此文件為規格說明，不直接修改 UI 程式碼（唯讀區域）

---

## 影響檔案

| 檔案 | 路徑 | 修改類型 |
|------|------|---------|
| `diagnosis_rules.json` | `UserInterfaceDesign/UI_v5/UI_V5/` | 新增欄位 |
| `dashboard.js` | `UserInterfaceDesign/spray-manger/` | 新增顯示邏輯 |

---

## 修改一：diagnosis_rules.json 新增欄位

### 現有結構（每條規則）

```json
{
  "component": "filter",
  "level": "bad",
  "direction": "high",
  "issue": "濾網壓差過高，可能導致流量不足或停機。",
  "reason": "可能原因為濾網堵塞...",
  "solution": "建議立即停機更換濾網..."
}
```

### 修改後結構（新增 4 個欄位）

```json
{
  "component": "filter",
  "level": "bad",
  "direction": "high",
  "issue": "濾網壓差過高，可能導致流量不足或停機。",
  "reason": "可能原因為濾網堵塞...",
  "solution": "建議立即停機更換濾網...",

  "cause_id": "FILTER_CLOG",
  "response_ids": ["REPLACE_FILTER", "BACKFLUSH_FILTER"],
  "downtime_estimate_min": 30,
  "skill_required": "technician"
}
```

### 新欄位說明

| 欄位 | 型別 | 說明 | 值範例 |
|------|------|------|--------|
| `cause_id` | str \| null | 對應 `cause_catalog.cause_id`，null 表示無結構化對應 | `"FILTER_CLOG"` |
| `response_ids` | array[str] | 對應 `response_catalog.response_id` 清單 | `["REPLACE_FILTER"]` |
| `downtime_estimate_min` | int \| null | 預估停機分鐘數（最壞情況） | `30` |
| `skill_required` | str \| null | 最低所需技能等級 | `"technician"` |

### 24 條規則的建議值對照表

| component | level | cause_id | response_ids | downtime | skill |
|-----------|-------|---------|--------------|----------|-------|
| arm | ok | null | [] | null | null |
| arm | warn | `ARM_JOINT_WEAR` | `["CHECK_ARM_JOINT", "LUBRICATE_JOINT"]` | 15 | `"operator"` |
| arm | bad | `ARM_SERVO_FAULT` | `["REPLACE_SERVO", "RECALIBRATE_ARM"]` | 120 | `"engineer"` |
| nozzle | ok | null | [] | null | null |
| nozzle | warn | `NOZZLE_PARTIAL_CLOG` | `["CLEAN_NOZZLE"]` | 10 | `"operator"` |
| nozzle | bad | `NOZZLE_FULL_CLOG` | `["REPLACE_NOZZLE", "CLEAN_NOZZLE"]` | 20 | `"technician"` |
| air | ok | null | [] | null | null |
| air | warn | `AIR_PRESSURE_LOW` | `["CHECK_COMPRESSOR", "ADJUST_PRESSURE"]` | 5 | `"operator"` |
| air | bad | `COMPRESSOR_FAULT` | `["SERVICE_COMPRESSOR"]` | 60 | `"engineer"` |
| width | ok | null | [] | null | null |
| width | warn | `SPRAY_WIDTH_DRIFT` | `["RECALIBRATE_NOZZLE_ANGLE"]` | 15 | `"technician"` |
| width | bad | `SPRAY_WIDTH_FAULT` | `["REPLACE_NOZZLE", "RECALIBRATE_NOZZLE_ANGLE"]` | 30 | `"technician"` |
| filter | ok | null | [] | null | null |
| filter | warn | `FILTER_PARTIAL_CLOG` | `["BACKFLUSH_FILTER"]` | 10 | `"operator"` |
| filter | bad | `FILTER_CLOG` | `["REPLACE_FILTER", "BACKFLUSH_FILTER"]` | 30 | `"technician"` |
| quality | ok | null | [] | null | null |
| quality | warn | `QUALITY_DRIFT` | `["ADJUST_RECIPE", "CHECK_ENVIRONMENT"]` | 5 | `"operator"` |
| quality | bad | `QUALITY_FAULT` | `["PAUSE_LINE", "ADJUST_RECIPE", "INSPECT_ALL"]` | 90 | `"engineer"` |

---

## 修改二：dashboard.js — renderStationDiagnosisCard 擴充

### 現有函式（`dashboard.js:3332`）

```javascript
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
```

### 修改後（差異說明）

在 `<div class="diagnosis-action-box">` 後方、`</article>` 前方插入以下區塊：

```javascript
// 新增：停機時間 + 技能等級區塊
${(issue.downtime_estimate_min || issue.skill_required) ? `
  <div class="diagnosis-pdm-meta">
    ${issue.downtime_estimate_min ? `
      <span class="pdm-downtime-badge">
        ⏱ 預估停機 ${issue.downtime_estimate_min} 分鐘
      </span>
    ` : ""}
    ${issue.skill_required ? `
      <span class="pdm-skill-badge pdm-skill-${issue.skill_required}">
        ${renderSkillLabel(issue.skill_required)}
      </span>
    ` : ""}
  </div>
` : ""}

// 新增：確認告警按鈕（僅當有 alert_id 時顯示）
${diagnosisItem.alert_id ? `
  <div class="diagnosis-ack-row">
    ${diagnosisItem.acknowledged ? `
      <span class="ack-done-label">✓ 已確認</span>
    ` : `
      <button class="ack-btn"
              onclick="acknowledgeAlert('${escapeHtml(diagnosisItem.alert_id)}')"
              data-event-id="${escapeHtml(diagnosisItem.alert_id)}">
        確認告警
      </button>
    `}
  </div>
` : ""}
```

### 新增輔助函式

```javascript
// 技能等級中文標籤
function renderSkillLabel(skill) {
  const labels = {
    operator:   "操作員",
    technician: "技術員",
    engineer:   "工程師",
  };
  return labels[skill] || skill;
}

// 確認告警（呼叫 PATCH /api/alerts/{event_id}/acknowledge）
async function acknowledgeAlert(eventId) {
  const btn = document.querySelector(`[data-event-id="${eventId}"]`);
  if (btn) btn.disabled = true;

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/api/alerts/${eventId}/acknowledge`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ acknowledged_at: new Date().toISOString() }),
    });
    if (res.ok) {
      if (btn) {
        btn.closest(".diagnosis-ack-row").innerHTML =
          `<span class="ack-done-label">✓ 已確認</span>`;
      }
    } else {
      if (btn) btn.disabled = false;
      console.error("確認告警失敗", await res.text());
    }
  } catch (err) {
    if (btn) btn.disabled = false;
    console.error("確認告警網路錯誤", err);
  }
}
```

---

## 修改三：CSS 樣式補充

在對應 CSS 檔案（`spray-manger/` 目錄）新增：

```css
/* PdM 元資料列（停機時間 + 技能等級） */
.diagnosis-pdm-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.pdm-downtime-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffc107;
}

.pdm-skill-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.pdm-skill-operator   { background: #d1e7dd; color: #0a3622; border: 1px solid #0f5132; }
.pdm-skill-technician { background: #cff4fc; color: #055160; border: 1px solid #0dcaf0; }
.pdm-skill-engineer   { background: #f8d7da; color: #58151c; border: 1px solid #f5c2c7; }

/* 確認告警區塊 */
.diagnosis-ack-row {
  margin-top: 8px;
  text-align: right;
}

.ack-btn {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 4px;
  border: 1px solid #0d6efd;
  background: #0d6efd;
  color: #fff;
  cursor: pointer;
}

.ack-btn:hover   { background: #0b5ed7; }
.ack-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.ack-done-label {
  font-size: 12px;
  color: #198754;
  font-weight: 600;
}
```

---

## diagnosisItem 物件結構擴充說明

現有 `buildStationDiagnosis()` 產生的 `diagnosisItem` 需在 `topIssue` 中補充：

```javascript
// 從 diagnosis_rules.json 取得對應規則後，補充以下欄位到 issue 物件
issue.downtime_estimate_min = rule.downtime_estimate_min || null;
issue.skill_required        = rule.skill_required || null;

// 若 Alert API 有回傳，補充到 diagnosisItem 層級
diagnosisItem.alert_id    = alertCard?.event_id || null;
diagnosisItem.acknowledged = alertCard?.acknowledged || false;
```

---

## 串聯流程（端到端）

```
前端載入診斷卡片
  ↓
buildStationDiagnosis(evaluation)
  → 查 diagnosis_rules.json 取得 cause_id / response_ids / downtime / skill
  ↓
呼叫 GET /api/alerts/unacknowledged/{station_id}
  → 取得 alert_id + acknowledged 狀態
  ↓
renderStationDiagnosisCard(diagnosisItem)
  → 顯示停機時間 badge + 技能等級 badge + 確認告警按鈕
  ↓
使用者點「確認告警」
  → PATCH /api/alerts/{event_id}/acknowledge
  → 按鈕變為「✓ 已確認」
```
