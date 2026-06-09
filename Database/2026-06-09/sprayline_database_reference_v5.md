# SprayLine Database Schema v5 — 完整資料表說明文件

> **版本**：v5（對應 ER 圖：`sprayline_er_model_v6.md`）
> **引擎**：PostgreSQL 16
> **資料表**：13 張（無 TimescaleDB Hypertable）
> **更新日期**：2026-06-09

---

## 目錄

- [資料流總覽](#資料流總覽)
- [Zone 2：批次生產](#zone-2批次生產)
  - [batch_run](#batch_run)
- [Zone 3：感測資料](#zone-3感測資料)
  - [sensor_1min（每分鐘）](#sensor_1min每分鐘)
  - [sensor_1hour（每小時）](#sensor_1hour每小時)
  - [六元件分鐘/小時分配原則](#六元件分鐘小時分配原則)
- [Zone 4：批次站點詳細狀態](#zone-4批次站點詳細狀態)
  - [batch_station_status](#batch_station_status)
- [Alert & Event](#alert--event)
  - [alert_event](#alert_event)
  - [alert_cause_link](#alert_cause_link)
  - [alert_response_link](#alert_response_link)
- [Catalog：原因 & 解方](#catalog原因--解方)
  - [cause_catalog](#cause_catalog)
  - [response_catalog](#response_catalog)
- [Zone 5：元件問題解方知識庫](#zone-5元件問題解方知識庫)
  - [component_catalog](#component_catalog)
  - [issue_catalog](#issue_catalog)
  - [solution_catalog](#solution_catalog)
  - [component_issue_solution_map](#component_issue_solution_map)
- [SQL DDL](#sql-ddl)
- [索引彙整](#索引彙整)
- [從 v4 → v5 升版對照](#從-v4--v5-升版對照)

---

## 資料流總覽

```
Edge Server（感測器採集）
    │
    ▼
DataPreprocessingService（DataPreprocess/）
    ├── 空值線性插值
    ├── IQR 突波濾除
    └── 5 秒滑動平均 → _Cleaned JSON
    │
    ├─────────────────────────────────────────────────────────┐
    ▼                                                         ▼
sensor_1min（每分鐘，17 欄）                           sensor_1hour（每小時，3 欄）
    │                                                         │
    │                                                         │
    └────────────┬────────────────────────────────────────────┘
                 │
                 ▼
         批次結束 → batch_station_status（6 狀態 + 6 解方）
                 │
                 ▼
         超過門檻 → alert_event
                 │
                 ├── alert_cause_link → cause_catalog
                 └── alert_response_link → response_catalog

知識庫查詢端：
    操作員/LLM → component_issue_solution_map
                 → 查詢建議 response_id → 回填 batch_station_status
```

---

## Zone 2：批次生產

### `batch_run`

**用途**：記錄每個生產批次的起訖時間與狀態。一個 `batch_id` 對應一次完整的噴塗工序（可跨三個站點、可跨日）。

> **v3 → v5 變更**：移除 `batch_date`（DATE，無法表示跨日批次）、`shift`、`wear_factor`、`updated_at`；`started_at` → `start_time`，`ended_at` → `ended_time`（TIMESTAMPTZ，正確支援跨日記錄）

| 欄位 | 型別 | 約束 | 說明 |
|---|---|---|---|
| `batch_id` | `VARCHAR(32)` | **PK** | 唯一識別碼，格式 `B_YYYYMMDD_NNN` |
| `start_time` | `TIMESTAMPTZ` | NOT NULL | 批次正式開始時間 |
| `ended_time` | `TIMESTAMPTZ` | 可 NULL | 批次結束時間（`NULL` = 仍在進行中） |
| `status` | `VARCHAR(16)` | CHECK | `'running'` / `'ok'` / `'warning'` / `'bad'` |

**被參考的資料表**：`sensor_1min`、`sensor_1hour`、`batch_station_status`、`alert_event`

---

## Zone 3：感測資料

### 感測頻率設計說明

Zone 3 依感測器的**物理變化速率**與**業務用途**，拆分為兩張資料表：

| 類型 | 資料表 | 寫入頻率 | 預估日資料量 |
|---|---|---|---|
| 製程控制 / PdM 核心 | `sensor_1min` | 每分鐘 1 筆 / 站 | 4,320 筆/天（3站 × 1,440分鐘）|
| 環境背景 / 熱管理 | `sensor_1hour` | 每小時 1 筆 / 站 | 72 筆/天（3站 × 24小時）|

### `sensor_1min`（每分鐘）

**用途**：記錄所有需要高頻監控的感測器資料，涵蓋六個元件的核心量測值。

| 欄位群組 | 欄位 | 型別 | 說明 |
|---|---|---|---|
| 識別 | `row_id` | `UUID` | PK（與 `ts` 組合）|
| 識別 | `ts` | `TIMESTAMPTZ` | 量測時間戳 |
| 識別 | `batch_id` | `VARCHAR(32)` | FK → `batch_run` |
| 識別 | `station_id` | `VARCHAR(32)` | 站點識別：Station_1 / Station_2 / Station_3 |
| **品質** | `film_thickness_um` | `REAL` | 膜厚（μm）—— 最終品質 Y 值 |
| **噴嘴** | `paint_flow_ml_min` | `REAL` | 塗料流量（ml/min）|
| **噴嘴** | `nozzle_roll` | `REAL` | 噴嘴翻滾角（degree）|
| **濾網** | `filter_diff_pressure_bar` | `REAL` | **PdM 核心 A**：壓差（bar），隨漆渣累積上升 |
| **濾網** | `filter_inflow_ml_min` | `REAL` | 濾網進液流量（ml/min）|
| **濾網** | `filter_outflow_ml_min` | `REAL` | 濾網出液流量（inflow-outflow 差值 = 實際阻塞量）|
| **#濾網** | `pump_current_a` | `REAL` | 幫浦電流（A）—— 流體衰退早期指標 |
| **空壓機** | `air_pressure_bar` | `REAL` | 霧化空氣壓力（bar）|
| **噴幅** | `spray_width_mm` | `REAL` | CCD 視覺量測噴幅（mm）|
| **機器手臂** | `servo_torque_load_pct` | `REAL` | **PdM 核心 B**：伺服馬達負載（%），隨磨損上升 |
| **#機器手臂** | `path_error_mm` | `REAL` | 軌跡追蹤誤差（mm）|
| **#機器手臂** | `vibration_g` | `REAL` | 三軸振動加速度（G）|
| **機器手臂** | `tcp_x_mm`、`tcp_y_mm`、`tcp_z_mm` | `REAL` | TCP 座標（mm）|
| **機器手臂** | `speed_mm_s` | `REAL` | 移動速度（mm/s）|

**索引**：

| 索引名稱 | 欄位 | 加速查詢 |
|---|---|---|
| `idx_s1min_batch` | `(batch_id, ts DESC)` | 取單批次感測序列 |
| `idx_s1min_station` | `(station_id, ts DESC)` | 儀表板最新感測值 |
| `idx_s1min_pdm` | `(station_id, ts DESC) INCLUDE (filter_diff_pressure_bar, servo_torque_load_pct)` | PdM 趨勢折線圖（Covering Index）|

---

### `sensor_1hour`（每小時）

**用途**：記錄變化緩慢的環境與熱管理感測器。環境溫濕度的熱慣性使每小時記錄已足夠反映趨勢；與 `sensor_1min` 分開儲存可減少每分鐘寫入量，提升查詢效率。

| 欄位群組 | 欄位 | 型別 | 說明 |
|---|---|---|---|
| 識別 | `row_id` | `UUID` | PK |
| 識別 | `ts` | `TIMESTAMPTZ` | 整點時間戳（如 10:00:00、11:00:00）|
| 識別 | `batch_id` | `VARCHAR(32)` | FK → `batch_run` |
| 識別 | `station_id` | `VARCHAR(32)` | 站點識別 |
| **機器手臂熱** | `gearbox_temperature_c` | `REAL` | 減速機溫度（°C）|
| **環境** | `temperature_c` | `REAL` | 噴塗室環境溫度（°C），影響漆料揮發速率 |
| **環境** | `humidity_rh` | `REAL` | 噴塗室濕度（%RH），影響塗料附著性 |

**索引**：`idx_s1hour_station`：`(station_id, ts DESC)`

---

### 六元件分鐘/小時分配原則

| 元件/面向 | 對應感測器 | 頻率 | 理由 |
|---|---|---|---|
| **機器手臂**（PdM 核心 B）| servo_torque_load_pct, path_error_mm, vibration_g, tcp_x/y/z_mm, speed_mm_s | 每分鐘 | 伺服負載快速劣化，需高頻趨勢追蹤以計算 RUL；振動可突發（碰撞） |
| **噴嘴** | paint_flow_ml_min, nozzle_roll | 每分鐘 | 流量直接影響品質，角度偏移需即時偵測 |
| **濾網**（PdM 核心 A）| filter_diff_pressure_bar, inflow/outflow, pump_current_a | 每分鐘 | 壓差是濾網堵塞最直接指標，需高頻記錄衰退曲線 |
| **空壓機** | air_pressure_bar | 每分鐘 | 霧化品質對壓力變化敏感，需即時監控 |
| **噴幅** | spray_width_mm | 每分鐘 | CCD 視覺系統每分鐘量測，品質管制關鍵 |
| **品質** | film_thickness_um | 每分鐘 | 最終品質 Y 值，異常需立即觸發告警 |
| **機器手臂熱管理** | gearbox_temperature_c | 每小時 | 熱慣性大（分鐘級變化不顯著），小時平均足以反映趨勢 |
| **#環境** | temperature_c, humidity_rh | 每小時 | 環境緩慢變化（HVAC 控制），不需高頻記錄 |

---

## Zone 4：批次站點詳細狀態

### `batch_station_status`

**用途**：每個批次 × 每個站點完成後，記錄六元件的最終狀態與對應的解方。取代 v3 的 `batch_summary` + `pdm_degradation_log`，以 composite PK 統一管理。

> **設計原則**：一筆紀錄 = 一個批次在一個站點的完整診斷快照（6 狀態 + 6 解方 FK）。response_id 欄位對應 `response_catalog`，可 NULL（代表無需處置）。

| 欄位 | 型別 | 約束 | 說明 |
|---|---|---|---|
| `batch_id` | `VARCHAR(32)` | **PK**（組合）, FK → `batch_run` | — |
| `station_id` | `VARCHAR(32)` | **PK**（組合）| Station_1 / Station_2 / Station_3 |
| `write_time` | `TIMESTAMPTZ` | NOT NULL DEFAULT now() | 本筆寫入時間 |
| `robot_arm_state` | `VARCHAR(8)` | CHECK | 機器手臂狀態：`ok` / `warning` / `fault` |
| `nozzle_state` | `VARCHAR(8)` | CHECK | 噴嘴狀態 |
| `filter_state` | `VARCHAR(8)` | CHECK | 濾網狀態 |
| `compressor_state` | `VARCHAR(8)` | CHECK | 空壓機狀態 |
| `spray_width_state` | `VARCHAR(8)` | CHECK | 噴幅狀態 |
| `quality_state` | `VARCHAR(8)` | CHECK | 品質（膜厚）狀態 |
| `robot_arm_response_id` | `VARCHAR(32)` | FK → `response_catalog`，可 NULL | 機器手臂建議解方 |
| `nozzle_response_id` | `VARCHAR(32)` | FK → `response_catalog`，可 NULL | 噴嘴建議解方 |
| `filter_response_id` | `VARCHAR(32)` | FK → `response_catalog`，可 NULL | 濾網建議解方 |
| `compressor_response_id` | `VARCHAR(32)` | FK → `response_catalog`，可 NULL | 空壓機建議解方 |
| `spray_width_response_id` | `VARCHAR(32)` | FK → `response_catalog`，可 NULL | 噴幅建議解方 |
| `quality_response_id` | `VARCHAR(32)` | FK → `response_catalog`，可 NULL | 品質建議解方 |

**UNIQUE**：`(batch_id, station_id)` 為複合主鍵，每批次每站只能有一筆。

**使用範例**（一筆完整紀錄）：
```
batch_id         = 'B_20260609_001'
station_id       = 'Station_1'
write_time       = '2026-06-09T09:50:00Z'
filter_state     = 'warning'
filter_response_id = 'REPLACE_FILTER'
quality_state    = 'ok'
-- 其餘 state 均為 'ok'，response_id 為 NULL
```

---

## Alert & Event

### `alert_event`

**用途**：當 Service 層偵測到感測器量測值超過門檻時，即時寫入此表。一個 alert 可透過 M:N junction tables 對應多個原因（`alert_cause_link`）與多個應對措施（`alert_response_link`）。

> **v3 → v5 欄位變更**：
> - `level` → `state`（語義一致性）
> - `event_type` → `cause`（對應 cause_catalog）
> - `event_at` + `created_at` 合併 → `ts`（移除冗餘欄位）
> - 移除 `resolved_at`（解決追蹤由 response_link 負責）
> - 移除 `rule_id`（Zone 1 移除後失去依據）

| 欄位 | 型別 | 約束 | 說明 |
|---|---|---|---|
| `event_id` | `UUID` | **PK** | 自動產生 |
| `batch_id` | `VARCHAR(32)` | FK → `batch_run` | 所屬批次 |
| `station_id` | `VARCHAR(32)` | NOT NULL | 站點識別 |
| `sensor_name` | `VARCHAR(64)` | NOT NULL | 觸發告警的感測器名稱 |
| `measured_value` | `REAL` | NOT NULL | 觸發時的量測值 |
| `state` | `VARCHAR(8)` | CHECK | `'warning'` / `'fault'` |
| `cause` | `VARCHAR(64)` | — | 觸發原因識別（對應 `cause_catalog.cause_id`）|
| `ts` | `TIMESTAMPTZ` | NOT NULL DEFAULT now() | 事件觸發時間 |
| `message` | `TEXT` | — | 說明文字 |
| `acknowledged_at` | `TIMESTAMPTZ` | 可 NULL | 確認時間（`NULL` = 未確認）|

---

### `alert_cause_link`

**用途**：一個告警事件可對應多個原因（M:N）。`is_primary = TRUE` 標記主要原因。

| 欄位 | 型別 | 說明 |
|---|---|---|
| `alert_id` | `UUID` | **PK**（組合），FK → `alert_event` |
| `cause_id` | `VARCHAR(32)` | **PK**（組合），FK → `cause_catalog` |
| `is_primary` | `BOOLEAN` | `TRUE` = 主要原因 |

---

### `alert_response_link`

**用途**：一個告警事件可對應多個應對措施（M:N）。記錄執行時間與執行人員。

| 欄位 | 型別 | 說明 |
|---|---|---|
| `alert_id` | `UUID` | **PK**（組合），FK → `alert_event` |
| `response_id` | `VARCHAR(32)` | **PK**（組合），FK → `response_catalog` |
| `executed_at` | `TIMESTAMPTZ` | 執行時間 |
| `operator_id` | `VARCHAR(64)` | 執行操作員 |

**使用範例**（一次濾網警報的完整流程）：
```
alert_event:
    event_id = 'uuid-abc'
    sensor_name = 'filter_diff_pressure_bar'
    measured_value = 0.52
    state = 'fault'
    cause = 'FILTER_CLOG'
    ts = '2026-06-09T10:00:00Z'

alert_cause_link:
    (alert_id='uuid-abc', cause_id='FILTER_CLOG', is_primary=TRUE)
    (alert_id='uuid-abc', cause_id='PUMP_DEGRADATION', is_primary=FALSE)

alert_response_link:
    (alert_id='uuid-abc', response_id='REPLACE_FILTER', executed_at='2026-06-09T10:15:00Z')
```

---

## Catalog：原因 & 解方

### `cause_catalog`

| 欄位 | 型別 | 說明 |
|---|---|---|
| `cause_id` | `VARCHAR(32)` PK | 如 `FILTER_CLOG`、`SERVO_WEAR` |
| `category` | `VARCHAR(16)` | `pdm_core` / `quality_fluid` / `protection` / `environment` / `process` |
| `description_zh` | `TEXT` | 繁體中文說明 |
| `typical_component` | `VARCHAR(32)` | 常見受影響元件（filter / servo / nozzle / pump / robot）|
| `severity` | `VARCHAR(8)` | `low` / `medium` / `high` |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

**預置資料**：

| cause_id | category | typical_component | severity |
|---|---|---|---|
| FILTER_CLOG | pdm_core | filter | medium |
| SERVO_WEAR | pdm_core | servo | medium |
| PUMP_DEGRADATION | pdm_core | pump | medium |
| NOZZLE_CLOG | quality_fluid | nozzle | high |
| FLOW_UNSTABLE | quality_fluid | pump | medium |
| THICKNESS_DRIFT | quality_fluid | process | medium |
| VIBRATION_HIGH | protection | robot | high |
| PATH_ERROR_HIGH | protection | robot | high |
| GEARBOX_OVERHEAT | protection | gearbox | high |
| AIR_PRESSURE_UNSTABLE | quality_fluid | compressor | medium |
| AIR_MOISTURE_HIGH | quality_fluid | compressor | medium |
| ENV_TEMP_OUT | environment | chamber | medium |
| ENV_HUMID_OUT | environment | chamber | medium |

---

### `response_catalog`

| 欄位 | 型別 | 說明 |
|---|---|---|
| `response_id` | `VARCHAR(32)` PK | 如 `REPLACE_FILTER`、`RECALIBRATE_TCP` |
| `description_zh` | `TEXT` | 繁體中文說明 |
| `downtime_estimate_min` | `INT` | 預估停機分鐘數 |
| `skill_required` | `VARCHAR(16)` | `operator` / `technician` / `engineer` |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

**預置資料**：

| response_id | description_zh | downtime_estimate_min | skill_required |
|---|---|---|---|
| REPLACE_FILTER | 更換濾網（依壓差門檻觸發） | 30 | operator |
| LUBRICATE_SERVO | 定期潤滑伺服馬達與減速機 | 20 | technician |
| REPLACE_SERVO | 更換伺服馬達或減速機 | 120 | engineer |
| RECALIBRATE_TCP | 重新校正工具中心點（TCP） | 45 | technician |
| TIGHTEN_BASE | 緊固基座螺栓、檢查防震墊 | 15 | operator |
| CLEAN_NOZZLE | 拆卸清洗噴嘴 | 20 | operator |
| REPLACE_NOZZLE | 更換磨損噴嘴 | 25 | technician |
| RECALIBRATE_NOZZLE_ANGLE | 重新校正噴嘴角度 | 30 | technician |
| BACKWASH_FILTER | 反洗濾網管路 | 20 | technician |
| INSTALL_DRYER | 加裝/更換乾燥機與油水分離器 | 180 | engineer |
| DRAIN_CONDENSATE | 定期排放冷凝水 | 5 | operator |
| CALIBRATE_PRESSURE_VALVE | 校正壓力調節閥 | 30 | technician |
| ADJUST_TCP_Z | 校正噴嘴與工件距離（TCP Z 軸）| 20 | technician |
| ADJUST_FLOW_PRESSURE | 調整塗料流量與空壓比例 | 10 | operator |
| CCD_PATH_CORRECTION | 啟用 CCD 視覺系統即時路徑校正 | 0 | engineer |
| ADJUST_SPEED_FLOW | 調整噴塗速度與流量 | 10 | operator |
| CALIBRATE_ENV_CONTROL | 校正環境溫濕度控制系統 | 60 | engineer |

---

## Zone 5：元件問題解方知識庫

**設計目的**：提供通用診斷知識庫，獨立於實際事件記錄（alert_event）。用途：
1. 操作員快速查詢「某元件出現某問題時，最佳解方是什麼」
2. LLM 輔助診斷時提供上下文知識
3. 建立 `batch_station_status.response_id` 時的推薦依據

### `component_catalog`

| 欄位 | 型別 | 說明 |
|---|---|---|
| `component_id` | `VARCHAR(32)` PK | 元件識別碼 |
| `display_name` | `VARCHAR(64)` | 顯示名稱（中文） |
| `category` | `VARCHAR(16)` | `hardware`（實體元件）/ `process_metric`（製程指標）|
| `description` | `TEXT` | 說明 |

**預置資料**：

| component_id | display_name | category |
|---|---|---|
| ROBOT_ARM | 機器手臂 | hardware |
| NOZZLE | 噴嘴 | hardware |
| FILTER | 濾網 | hardware |
| AIR_COMPRESSOR | 空壓機 | hardware |
| SPRAY_WIDTH | 噴幅 | process_metric |
| QUALITY | 品質（膜厚） | process_metric |

---

### `issue_catalog`

| 欄位 | 型別 | 說明 |
|---|---|---|
| `issue_id` | `VARCHAR(32)` PK | 問題識別碼 |
| `display_name` | `VARCHAR(128)` | 問題名稱 |
| `description` | `TEXT` | 詳細說明 |
| `severity` | `VARCHAR(8)` | `low` / `medium` / `high` |

**預置資料**：

| issue_id | display_name | severity |
|---|---|---|
| SERVO_OVERLOAD | 伺服馬達負載過高/磨損 | medium |
| PATH_ERROR_HIGH | 軌跡追蹤誤差過大（TCP 偏移）| high |
| VIBRATION_HIGH | 異常振動（軸承鬆動/碰撞）| high |
| GEARBOX_OVERHEAT | 減速機過熱 | high |
| JOINT_BACKLASH | 關節背隙增大 | medium |
| NOZZLE_CLOG | 噴嘴堵塞（漆渣累積）| high |
| NOZZLE_WEAR | 噴嘴孔徑磨損擴大 | medium |
| NOZZLE_ANGLE_DRIFT | 噴嘴翻滾角偏移 | medium |
| FILTER_CLOG | 濾網堵塞（壓差持續上升）| medium |
| FILTER_DAMAGE | 濾網破損洩漏 | high |
| FLOW_IMBALANCE | 進出液流量不平衡 | medium |
| AIR_PRESSURE_UNSTABLE | 空氣壓力不穩/不足 | medium |
| AIR_MOISTURE_HIGH | 壓縮空氣含水量過高 | medium |
| AIR_OIL_CONTAMINATION | 油氣混入污染 | high |
| AIR_LEAKAGE | 漏氣（管路接頭）| medium |
| SPRAY_WIDTH_DEVIATION | 噴幅偏離基準值（過寬/過窄）| medium |
| SPRAY_WIDTH_UNSTABLE | 噴幅不均勻（批次內標準差過大）| medium |
| FILM_THICKNESS_OOC | 膜厚超出規格範圍 | high |
| FILM_THICKNESS_VARIATION | 膜厚不均勻（std 過高）| medium |
| SURFACE_DEFECT | 表面缺陷（橘皮/流掛/氣泡）| high |

---

### `solution_catalog`

與 `response_catalog` 欄位結構相同，但作為知識庫的解方目錄：

| 欄位 | 型別 | 說明 |
|---|---|---|
| `solution_id` | `VARCHAR(32)` PK | 解方識別碼 |
| `description` | `TEXT` | 繁體中文說明 |
| `downtime_estimate_min` | `INT` | 預估停機分鐘數 |
| `skill_required` | `VARCHAR(16)` | `operator` / `technician` / `engineer` |

*預置資料與 response_catalog 相同，solution_id 命名規則亦一致。*

---

### `component_issue_solution_map`

**用途**：三方多對多映射表，記錄「某元件在發生某問題時，可採用某解方」的知識關係。

| 欄位 | 型別 | 說明 |
|---|---|---|
| `map_id` | `UUID` | **PK**，自動產生 |
| `component_id` | `VARCHAR(32)` | FK → `component_catalog` |
| `issue_id` | `VARCHAR(32)` | FK → `issue_catalog` |
| `solution_id` | `VARCHAR(32)` | FK → `solution_catalog` |
| `relevance_rank` | `INT` | 解方優先順序（1 = 首選）|
| `effectiveness_pct` | `REAL` | 歷史有效率（%），可由實際案例統計回填 |
| `note` | `TEXT` | 補充說明 |
| `updated_at` | `TIMESTAMPTZ` | DEFAULT now() |

**UNIQUE**：`(component_id, issue_id, solution_id)`

**預置映射資料**：

| component_id | issue_id | solution_id | relevance_rank |
|---|---|---|---|
| ROBOT_ARM | SERVO_OVERLOAD | LUBRICATE_SERVO | 1 |
| ROBOT_ARM | SERVO_OVERLOAD | REPLACE_SERVO | 2 |
| ROBOT_ARM | PATH_ERROR_HIGH | RECALIBRATE_TCP | 1 |
| ROBOT_ARM | VIBRATION_HIGH | TIGHTEN_BASE | 1 |
| ROBOT_ARM | GEARBOX_OVERHEAT | LUBRICATE_SERVO | 1 |
| NOZZLE | NOZZLE_CLOG | CLEAN_NOZZLE | 1 |
| NOZZLE | NOZZLE_WEAR | REPLACE_NOZZLE | 1 |
| NOZZLE | NOZZLE_ANGLE_DRIFT | RECALIBRATE_NOZZLE_ANGLE | 1 |
| FILTER | FILTER_CLOG | REPLACE_FILTER | 1 |
| FILTER | FILTER_CLOG | BACKWASH_FILTER | 2 |
| FILTER | FILTER_DAMAGE | REPLACE_FILTER | 1 |
| AIR_COMPRESSOR | AIR_PRESSURE_UNSTABLE | CALIBRATE_PRESSURE_VALVE | 1 |
| AIR_COMPRESSOR | AIR_MOISTURE_HIGH | INSTALL_DRYER | 1 |
| AIR_COMPRESSOR | AIR_MOISTURE_HIGH | DRAIN_CONDENSATE | 2 |
| AIR_COMPRESSOR | AIR_LEAKAGE | CALIBRATE_PRESSURE_VALVE | 1 |
| SPRAY_WIDTH | SPRAY_WIDTH_DEVIATION | ADJUST_TCP_Z | 1 |
| SPRAY_WIDTH | SPRAY_WIDTH_DEVIATION | ADJUST_FLOW_PRESSURE | 2 |
| SPRAY_WIDTH | SPRAY_WIDTH_DEVIATION | REPLACE_NOZZLE | 3 |
| SPRAY_WIDTH | SPRAY_WIDTH_UNSTABLE | CCD_PATH_CORRECTION | 1 |
| QUALITY | FILM_THICKNESS_OOC | ADJUST_SPEED_FLOW | 1 |
| QUALITY | FILM_THICKNESS_OOC | CALIBRATE_ENV_CONTROL | 2 |
| QUALITY | SURFACE_DEFECT | ADJUST_FLOW_PRESSURE | 1 |
| QUALITY | SURFACE_DEFECT | CALIBRATE_ENV_CONTROL | 2 |

---

## SQL DDL

```sql
-- =====================================================================
-- ZONE 2：批次生產
-- =====================================================================
CREATE TABLE batch_run (
    batch_id    VARCHAR(32)  PRIMARY KEY,
    start_time  TIMESTAMPTZ  NOT NULL,
    ended_time  TIMESTAMPTZ,
    status      VARCHAR(16)  NOT NULL DEFAULT 'running'
                CHECK (status IN ('running','ok','warning','bad'))
);

CREATE INDEX idx_batch_start ON batch_run (start_time DESC);


-- =====================================================================
-- ZONE 3：感測資料
-- =====================================================================
CREATE TABLE sensor_1min (
    row_id                   UUID         NOT NULL DEFAULT gen_random_uuid(),
    ts                       TIMESTAMPTZ  NOT NULL,
    batch_id                 VARCHAR(32)  NOT NULL REFERENCES batch_run(batch_id),
    station_id               VARCHAR(32)  NOT NULL,
    -- 品質
    film_thickness_um        REAL,
    -- 噴嘴
    paint_flow_ml_min        REAL,
    nozzle_roll              REAL,
    -- 濾網
    filter_diff_pressure_bar REAL,
    filter_inflow_ml_min     REAL,
    filter_outflow_ml_min    REAL,
    pump_current_a           REAL,
    -- 空壓機
    air_pressure_bar         REAL,
    -- 噴幅
    spray_width_mm           REAL,
    -- 機器手臂
    servo_torque_load_pct    REAL,
    path_error_mm            REAL,
    vibration_g              REAL,
    tcp_x_mm                 REAL,
    tcp_y_mm                 REAL,
    tcp_z_mm                 REAL,
    speed_mm_s               REAL,
    PRIMARY KEY (row_id, ts)
);

CREATE INDEX idx_s1min_batch   ON sensor_1min (batch_id, ts DESC);
CREATE INDEX idx_s1min_station ON sensor_1min (station_id, ts DESC);
CREATE INDEX idx_s1min_pdm     ON sensor_1min (station_id, ts DESC)
    INCLUDE (filter_diff_pressure_bar, servo_torque_load_pct);


CREATE TABLE sensor_1hour (
    row_id                UUID         NOT NULL DEFAULT gen_random_uuid(),
    ts                    TIMESTAMPTZ  NOT NULL,
    batch_id              VARCHAR(32)  NOT NULL REFERENCES batch_run(batch_id),
    station_id            VARCHAR(32)  NOT NULL,
    gearbox_temperature_c REAL,
    temperature_c         REAL,
    humidity_rh           REAL,
    PRIMARY KEY (row_id, ts)
);

CREATE INDEX idx_s1hour_station ON sensor_1hour (station_id, ts DESC);


-- =====================================================================
-- CATALOG：原因 & 解方
-- =====================================================================
CREATE TABLE cause_catalog (
    cause_id          VARCHAR(32)  PRIMARY KEY,
    category          VARCHAR(16)  NOT NULL
                      CHECK (category IN ('pdm_core','quality_fluid','protection','environment','process')),
    description_zh    TEXT         NOT NULL,
    typical_component VARCHAR(32),
    severity          VARCHAR(8)   NOT NULL CHECK (severity IN ('low','medium','high')),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE response_catalog (
    response_id           VARCHAR(32)  PRIMARY KEY,
    description_zh        TEXT         NOT NULL,
    downtime_estimate_min INT,
    skill_required        VARCHAR(16)  NOT NULL
                          CHECK (skill_required IN ('operator','technician','engineer')),
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now()
);


-- =====================================================================
-- ZONE 4：批次站點詳細狀態
-- =====================================================================
CREATE TABLE batch_station_status (
    batch_id                  VARCHAR(32)  NOT NULL REFERENCES batch_run(batch_id),
    station_id                VARCHAR(32)  NOT NULL,
    write_time                TIMESTAMPTZ  NOT NULL DEFAULT now(),
    robot_arm_state           VARCHAR(8)   CHECK (robot_arm_state   IN ('ok','warning','fault')),
    nozzle_state              VARCHAR(8)   CHECK (nozzle_state       IN ('ok','warning','fault')),
    filter_state              VARCHAR(8)   CHECK (filter_state       IN ('ok','warning','fault')),
    compressor_state          VARCHAR(8)   CHECK (compressor_state   IN ('ok','warning','fault')),
    spray_width_state         VARCHAR(8)   CHECK (spray_width_state  IN ('ok','warning','fault')),
    quality_state             VARCHAR(8)   CHECK (quality_state      IN ('ok','warning','fault')),
    robot_arm_response_id     VARCHAR(32)  REFERENCES response_catalog(response_id),
    nozzle_response_id        VARCHAR(32)  REFERENCES response_catalog(response_id),
    filter_response_id        VARCHAR(32)  REFERENCES response_catalog(response_id),
    compressor_response_id    VARCHAR(32)  REFERENCES response_catalog(response_id),
    spray_width_response_id   VARCHAR(32)  REFERENCES response_catalog(response_id),
    quality_response_id       VARCHAR(32)  REFERENCES response_catalog(response_id),
    PRIMARY KEY (batch_id, station_id)
);


-- =====================================================================
-- ALERT & EVENT
-- =====================================================================
CREATE TABLE alert_event (
    event_id        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id        VARCHAR(32)  NOT NULL REFERENCES batch_run(batch_id),
    station_id      VARCHAR(32)  NOT NULL,
    sensor_name     VARCHAR(64)  NOT NULL,
    measured_value  REAL         NOT NULL,
    state           VARCHAR(8)   NOT NULL CHECK (state IN ('warning','fault')),
    cause           VARCHAR(64),
    ts              TIMESTAMPTZ  NOT NULL DEFAULT now(),
    message         TEXT,
    acknowledged_at TIMESTAMPTZ
);

CREATE INDEX idx_alert_station ON alert_event (station_id, ts DESC);
CREATE INDEX idx_alert_sensor  ON alert_event (sensor_name, ts DESC);
CREATE INDEX idx_alert_unacked ON alert_event (station_id, ts DESC)
    WHERE acknowledged_at IS NULL;


CREATE TABLE alert_cause_link (
    alert_id   UUID         NOT NULL REFERENCES alert_event(event_id),
    cause_id   VARCHAR(32)  NOT NULL REFERENCES cause_catalog(cause_id),
    is_primary BOOLEAN      NOT NULL DEFAULT FALSE,
    PRIMARY KEY (alert_id, cause_id)
);

CREATE TABLE alert_response_link (
    alert_id    UUID         NOT NULL REFERENCES alert_event(event_id),
    response_id VARCHAR(32)  NOT NULL REFERENCES response_catalog(response_id),
    executed_at TIMESTAMPTZ,
    operator_id VARCHAR(64),
    PRIMARY KEY (alert_id, response_id)
);


-- =====================================================================
-- ZONE 5：元件問題解方知識庫
-- =====================================================================
CREATE TABLE component_catalog (
    component_id VARCHAR(32)  PRIMARY KEY,
    display_name VARCHAR(64)  NOT NULL,
    category     VARCHAR(16)  CHECK (category IN ('hardware','process_metric')),
    description  TEXT
);

CREATE TABLE issue_catalog (
    issue_id     VARCHAR(32)  PRIMARY KEY,
    display_name VARCHAR(128) NOT NULL,
    description  TEXT,
    severity     VARCHAR(8)   CHECK (severity IN ('low','medium','high'))
);

CREATE TABLE solution_catalog (
    solution_id           VARCHAR(32)  PRIMARY KEY,
    description           TEXT         NOT NULL,
    downtime_estimate_min INT,
    skill_required        VARCHAR(16)  CHECK (skill_required IN ('operator','technician','engineer'))
);

CREATE TABLE component_issue_solution_map (
    map_id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    component_id      VARCHAR(32)  NOT NULL REFERENCES component_catalog(component_id),
    issue_id          VARCHAR(32)  NOT NULL REFERENCES issue_catalog(issue_id),
    solution_id       VARCHAR(32)  NOT NULL REFERENCES solution_catalog(solution_id),
    relevance_rank    INT,
    effectiveness_pct REAL         CHECK (effectiveness_pct BETWEEN 0 AND 100),
    note              TEXT,
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (component_id, issue_id, solution_id)
);
```

---

## 索引彙整

| 索引名稱 | 所在表 | 欄位 | 目的 |
|---|---|---|---|
| `idx_batch_start` | `batch_run` | `(start_time DESC)` | 最近批次查詢 |
| `idx_s1min_batch` | `sensor_1min` | `(batch_id, ts DESC)` | 取單批次感測序列 |
| `idx_s1min_station` | `sensor_1min` | `(station_id, ts DESC)` | 儀表板最新感測值 |
| `idx_s1min_pdm` | `sensor_1min` | Covering：包含壓差、伺服 | PdM 趨勢圖（毫秒級）|
| `idx_s1hour_station` | `sensor_1hour` | `(station_id, ts DESC)` | 環境趨勢查詢 |
| `idx_alert_station` | `alert_event` | `(station_id, ts DESC)` | 站點告警歷史 |
| `idx_alert_sensor` | `alert_event` | `(sensor_name, ts DESC)` | 特定感測器告警 |
| `idx_alert_unacked` | `alert_event` | Partial：`acknowledged_at IS NULL` | 未確認告警（毫秒級）|

---

## 從 v4 → v5 升版對照

| v4 設計 | v5 變更 | 原因 |
|---|---|---|
| Zone 1（station_config + sensor_threshold）| **完全移除** | 門檻值與設定由應用層管理，不納入資料庫綱要 |
| `batch_run.shift`、`wear_factor`、`batch_date`、`updated_at` | **移除** | 班別/老化因子非核心記錄；batch_date 由 start_time 取代 |
| `batch_run.started_at / ended_at` | → **`start_time / ended_time`** | 跨日批次需 TIMESTAMPTZ，命名明確化 |
| `sensor_1hz`（1Hz，單張表）| **拆為** `sensor_1min`（17欄）+`sensor_1hour`（3欄）| 依物理量測頻率分開儲存，每分鐘寫入量降低 83%（去除環境欄）|
| `batch_summary` + `pdm_degradation_log` | → **`batch_station_status`**（composite PK）| 統一 6 元件狀態快照 + 6 解方 FK，結構更清晰 |
| `alert_event.level` | → **`state`** | 語義一致性 |
| `alert_event.event_type` | → **`cause`** | 與 cause_catalog 命名對齊 |
| `alert_event.event_at + created_at` | → **`ts`**（單一欄位）| 去除冗餘時間欄位 |
| `alert_event.resolved_at` | **移除** | 解決追蹤由 `alert_response_link.executed_at` 負責 |
| `alert_event.rule_id` | **移除** | Zone 1 移除後失去依據 |
| 無 M:N 告警連結 | **新增** `alert_cause_link` + `alert_response_link` | 一個告警支援多原因 + 多應對 |
| 無元件知識庫 | **新增** Zone 5（4 張表）| 系統化管理診斷知識，支援 LLM 輔助診斷與推薦解方 |
