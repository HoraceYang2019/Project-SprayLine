<!--
0531 狀態註記：
此檔案屬於早期 Past / Current Service reference。
目前 sample_method 採用 TimeSeriesService 0531 規則：
past = mean、current = recent_average、future = latest_valid。
若本檔與 0531 規則衝突，以 README_0531_status.md 與 webservices/time_series_service 為準。
-->

# 01_Past_Current_Service_

本資料夾是沈同學 Past / Current Service 的 對齊版。 
此版以「原版未補強」為主，不加入噴漆三大類額外欄位，因為目前尚未取得更前面的實際資料來源。

## 本版定位

```text
Past Service
 ↓
Current Service
 ↓
Statistics Service
 ↓
UI(E) / Ontology / Runtime TTL
```

Past / Current Service 主要負責提供上游的站別資料，包括：

- `stations[]`
- `state`
- `metrics`
- `process_parameters`
- `window`
- `generated_at`


### 1. 新增 `generated_at`

Past / Current output 新增：

```json
"generated_at": "<datetime-string>"
```

用途：表示 service 產生此份 output 的時間，方便 UI 更新、debug、ontology runtime 個體追蹤。

---

### 2. 新增 `window_id`

Past / Current window 新增：

```json
"window_id": "<string>"
```

用途：方便後續建立 ontology / TTL，例如：

```text
PastStationSnapshotLine1W001
CurrentStationSnapshotLine1W002
```

---

### 3. Past window 補 `window_start` / `window_end`

Past output 的 window 補：

```json
"window_start": "<datetime-string|null>",
"window_end": "<datetime-string|null>"
```

用途：Past Service 是歷史資料，需要保留歷史視窗範圍。

---

### 4. Current window 保留彈性

Current output 的 window 保留：

```json
"window_size": "defined_by_system"
```

目前尚未寫死是 latest、recent N 秒、recent N 筆或 short window summary。 
此部分需與沈同學及組員討論後再定。

---

### 5. 補 state vocabulary 說明

建議狀態名稱統一使用：

```text
Running
Standby
Stop
Maintenance
Alarm
```

JSON / schema 先不強制 enum，但 ontology 中可建立為 `StationState` 的 individuals。

---

### 6. 補欄位責任說明

Past / Current 較可能直接提供：

```text
state
pressure_bar
flow_rate_ml_min
quality_score_pct
temperature_c
utilization_pct
cycle_time_sec
```

較可能由 Statistics / Rule / Future Service 補齊：

```text
availability_pct
clog_rate_pct
maintainability_pct
risk_text
component_overview
summary
trend_series
```

---

## 仍需確認事項

請參考 `past_current_待定.md`：

1. Past Service 的 `sample_method` 尚未確定。
2. `flow_rate_ml_min` 的實際單位需確認。
3. Current Service 的 `window_size` 尚未確定。
4. Current Service 的 `sample_method` 尚未確定。

## 檔案

- `past_current_service_io_.ipynb`：主要 notebook
- `_full_naming_rules.md`：正式命名規則
- `past_current_待定.md`：待確認事項
- `README.md`：本說明檔
