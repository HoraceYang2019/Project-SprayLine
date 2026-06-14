# SprayLine 資料庫建置指南

**適用版本**：Schema v5.1（`setup_db.sql`）  
**更新日期**：2026-06-14  

---

## 目錄

1. [環境需求](#1-環境需求)
2. [安裝 PostgreSQL 16（Windows）](#2-安裝-postgresql-16windows)
3. [建立資料庫](#3-建立資料庫)
4. [生成一週假資料](#4-生成一週假資料)
5. [連接 Service 層](#5-連接-service-層)
6. [使用 Python Query 函式庫](#6-使用-python-query-函式庫)
7. [WebServices / UI 整合規格（Patch Spec）](#7-webservices--ui-整合規格patch-spec)
8. [Schema 升版（Migration）](#8-schema-升版migration)
9. [資料表結構速查](#9-資料表結構速查)
10. [⚠️ 已知不一致與注意事項](#10-️-已知不一致與注意事項)
11. [常見問題排除](#11-常見問題排除)

---

## 1. 環境需求

| 項目 | 版本 / 規格 | 備註 |
|------|------------|------|
| PostgreSQL | 16.x | 標準版，**不需要** TimescaleDB |
| Python | 3.10 以上 | |
| psycopg2-binary | 最新版 | `pip install psycopg2-binary` |
| 作業系統 | Windows 10/11、Linux、macOS | |

> **不需要 TimescaleDB**：現行 Schema v5 為純 PostgreSQL，`sensor_1min` 使用複合主鍵（`row_id + ts`）而非 Hypertable，不依賴 TimescaleDB 擴充。

---

## 2. 安裝 PostgreSQL 16（Windows）

### 2-1. 下載與安裝

1. 前往 [PostgreSQL 官方下載頁](https://www.postgresql.org/download/windows/)，選擇 **PostgreSQL 16** Windows installer
2. 安裝時記下以下設定（後續步驟需要）：
   - **Port**：預設 `5432`
   - **superuser 密碼**：安裝過程中設定的 `postgres` 使用者密碼
3. 安裝完成後，確認服務已啟動：

```powershell
# PowerShell（系統管理員）
Get-Service -Name postgresql*
# Status 應為 Running
```

### 2-2. 將 `psql` 加入 PATH（可選）

安裝程式通常會自動加入，若未加入：

```powershell
# 將以下路徑加入系統 PATH（版本號依實際安裝調整）
C:\Program Files\PostgreSQL\16\bin
```

### 2-3. 驗證連線

```powershell
psql -U postgres -c "SELECT version();"
# 輸入安裝時設定的密碼
# 應顯示：PostgreSQL 16.x ...
```

---

## 3. 建立資料庫

### 3-1. 安裝 Python 套件

```bash
pip install psycopg2-binary
```

### 3-2. 設定連線環境變數

> **注意**：`setup_db.py` 與 `generate_data.py` 使用 `DB_*` 前綴，與 Service 層的 `SPRAYLINE_DB_*` 不同。詳見第 7 節。

```powershell
# Windows PowerShell
$env:DB_HOST     = "localhost"
$env:DB_PORT     = "5432"
$env:DB_USER     = "postgres"
$env:DB_PASSWORD = "your_password_here"
$env:DB_NAME     = "sprayline"       # 可省略，預設即為 sprayline
```

```bash
# Linux / macOS
export DB_HOST=localhost
export DB_PASSWORD=your_password_here
```

### 3-3. 執行建置腳本

```bash
cd Database/2026-06-09
python setup_db.py
```

**預期輸出：**

```
==================================================
 SprayLine 資料庫一鍵建立
==================================================
目標: localhost:5432/sprayline
[建立] 資料庫 'sprayline' 建立成功
[執行] 正在建立資料表與索引...
[完成] 所有資料表建立成功

── 建立結果驗證 ──────────────────────────────────────
資料表                              筆數
-------------------------------------------
  batch_run                             0
  sensor_1min                           0
  sensor_3min                           0
  batch_station_status                  0
  alert_event                           0
  alert_cause_link                      0
  alert_response_link                   0
  cause_catalog                        17
  response_catalog                     19
  component_catalog                     6
  issue_catalog                        20
  solution_catalog                     18
  component_issue_solution_map         28
-------------------------------------------
```

> `sensor_1hour [錯誤]` 屬已知問題，不影響資料庫正常運作，詳見第 7-1 節。

### 3-4. 重複執行（重建資料庫）

腳本使用 `DROP TABLE IF EXISTS CASCADE` → `CREATE TABLE` 結構，重複執行是安全的：

```bash
python setup_db.py   # 第二次執行：[跳過] 資料庫已存在，重建所有資料表
```

---

## 4. 生成一週假資料

假資料模擬 **2026-06-02（一）～ 2026-06-08（日）** 的生產資料，共 91 批次。

### 4-1. 執行生成腳本

```bash
python generate_data.py
```

**預期筆數（約略值）：**

| 資料表 | 預期筆數 | 說明 |
|--------|----------|------|
| `batch_run` | 91 | 13 批次/天 × 7 天 |
| `sensor_1min` | 約 8,190 | 91 批次 × 3 站 × 30 筆/分鐘 |
| `sensor_3min` | 約 630 | 7 天 × 30 分鐘/批次 × 3 站（環境資料） |
| `batch_station_status` | 273 | 91 批次 × 3 站 |
| `alert_event` | 約 20~30 | 濾網壓差超閾值時寫入（約第 3~4 天首次） |

### 4-2. 衰退模型說明

腳本模擬兩個 PdM 指標的時間序列劣化行為：

**濾網壓差（`filter_diff_pressure_bar`）**
- 初始值：0.15 bar，每批次 +0.008 bar
- 告警閾值：> 0.30 bar（約第 19 批次，第 2 天）
- 故障閾值：> 0.50 bar（約第 44 批次，第 3~4 天，自動重設 0.15 bar）

**伺服負載（`servo_torque_load_pct`）**
- 初始值：40.0%，每批次 +0.12%
- 告警閾值：> 60%（約第 167 批次，超出 7 天範圍）
- 一週內為緩慢上升趨勢，不會觸發故障

### 4-3. 重新生成（清空前次資料）

```bash
python generate_data.py
# 腳本開頭自動 DELETE 生產資料表（保留 catalog 種子資料）
# 可重複執行
```

---

## 5. 連接 Service 層

Service 層（`WebServices/time_series_service_v3/`）使用**不同的環境變數命名**，需分別設定。

### 5-1. 建立 Service 層連線設定檔

```bash
cd WebServices/time_series_service_v3/src
cp db_config.example.json db_config.json
```

編輯 `db_config.json`：

```json
{
  "host":            "localhost",
  "port":            5432,
  "dbname":          "sprayline",
  "user":            "postgres",
  "password":        "your_password_here",
  "connect_timeout": 5
}
```

> `db_config.json` 已加入 `.gitignore`，不會被提交至版本控制。

### 5-2. 或使用環境變數（生產環境建議）

```powershell
# Windows PowerShell（注意：前綴為 SPRAYLINE_DB_，與建置腳本不同）
$env:SPRAYLINE_DB_HOST     = "localhost"
$env:SPRAYLINE_DB_PORT     = "5432"
$env:SPRAYLINE_DB_NAME     = "sprayline"
$env:SPRAYLINE_DB_USER     = "postgres"
$env:SPRAYLINE_DB_PASSWORD = "your_password_here"
```

### 5-3. 啟動 API Server

```bash
cd WebServices/time_series_service_v3/src
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

健康檢查：

```bash
curl http://localhost:8000/
# 應回傳 {"service_name": "TimeSeriesService", "status": "running", ...}
```

### 5-4. 測試 DB 模式查詢

```bash
curl -X POST http://localhost:8000/api/time-series/ui/summary \
  -H "Content-Type: application/json" \
  -d '{"slider_value": 0, "window_type": "current", "line_scope": "all"}'
```

若 `response._metadata.data_type` 為 `"database_raw_data"`，表示已成功連接 DB（而非 demo 模式）。

---

## 6. 使用 Python Query 函式庫

`Database/versionB/sprayline_db_queries.py` 封裝了資料庫所有讀寫操作，共 **42 支函式**，
讓推理引擎、DataPreprocess、Dashboard 等模組不需自行撰寫 SQL。

### 6-1. 模組結構

函式庫已依功能拆分為 7 個獨立模組，`sprayline_db_queries.py` 保留為統一入口（全部 re-export），現有呼叫端不需修改 import 路徑。

```
Database/versionB/
├── db_connection.py      → 連線工具（get_connection, _fetch, _fetchone）
├── db_batch.py           → 批次管理（7 支）
├── db_sensor.py          → 感測資料（7 支）
├── db_status.py          → 站點狀態快照（3 支）
├── db_alert.py           → 告警事件 + UI 串聯（13 支）
├── db_knowledge.py       → 門檻值 + 知識庫（7 支）
├── db_composite.py       → 複合查詢（2 支）
└── sprayline_db_queries.py → 統一入口（全部 re-export，維持向後相容）
```

### 6-2. 引入與連線

```python
# 舊路徑維持不變（統一入口）
from sprayline_db_queries import get_connection, get_latest_batches, insert_batch_run

# 或直接引入特定模組
from db_alert import get_alert_ui_card, get_responses_for_cause
from db_batch import get_latest_batches

conn = get_connection()                          # 讀取 DB_* 環境變數
conn = get_connection(host="192.168.1.10", password="secret")  # 覆蓋連線參數
conn.close()
```

### 6-3. 函式總覽

#### 批次管理（db_batch.py，7 支）

| 函式 | 說明 |
|------|------|
| `get_latest_batches(conn, limit)` | 最近 N 筆批次 |
| `get_batch_by_id(conn, batch_id)` | 依 ID 查詢批次 |
| `get_running_batches(conn)` | 所有進行中批次 |
| `get_batches_by_date_range(conn, start, end, status)` | 日期區間 + 狀態篩選 |
| `get_latest_completed_batch(conn, station_id)` | 最新已完成批次 |
| `insert_batch_run(conn, batch_id, start_time, ...)` | 建立新批次 |
| `update_batch_status(conn, batch_id, status, ended_time)` | 更新批次狀態與結束時間 |

#### 感測資料（db_sensor.py，7 支）

| 函式 | 說明 |
|------|------|
| `get_latest_sensor_1min(conn, station_id)` | 最新一筆感測值 |
| `get_sensor_1min_series(conn, station_id, batch_id, hours)` | 時間序列（批次或小時）|
| `get_pdm_trend(conn, station_id, hours)` | PdM 壓差 + 伺服折線圖資料 |
| `get_batch_sensor_aggregates(conn, batch_id, station_id)` | 批次聚合統計（AVG/MAX/STDDEV）|
| `get_latest_sensor_3min(conn, station_id)` | 最新環境感測值 |
| `get_sensor_3min_series(conn, station_id, ts_start, ts_end, hours)` | 環境感測時間序列 |
| `insert_sensor_readings_batch(conn, readings)` | 批次寫入 sensor_1min（含 data_quality_flag）|

#### 站點狀態（db_status.py，3 支）

| 函式 | 說明 |
|------|------|
| `get_batch_station_status(conn, batch_id, station_id)` | 批次診斷快照 |
| `get_latest_station_status(conn, station_id)` | 最新站點狀態 |
| `upsert_batch_station_status(conn, record)` | 寫入/更新批次站點診斷快照 |

#### 告警事件（db_alert.py，13 支）

| 函式 | 說明 |
|------|------|
| `get_unacknowledged_alerts(conn, station_id, limit)` | 未確認告警 |
| `get_alert_history(conn, station_id, days, limit)` | 歷史告警 |
| `get_alerts_by_filters(conn, station_id, state, acknowledged, days, limit)` | 複合條件告警查詢 |
| `get_alert_detail(conn, event_id)` | 告警 + 原因 + 應對措施 |
| `get_alert_causes(conn, event_id)` | 告警關聯原因清單 |
| `get_alert_responses(conn, event_id)` | 告警關聯應對措施清單 |
| `get_responses_for_cause(conn, cause_id)` | ★ 依故障原因查詢建議解方（含停機時間、技能需求） |
| `get_alert_ui_card(conn, event_id)` | ★ UI 告警完整卡片（整合 cause + response + 聚合派生欄位） |
| `insert_alert_event(conn, ...)` | 寫入告警，回傳 event_id |
| `link_alert_cause(conn, event_id, cause_id, is_primary)` | 關聯告警 ↔ 原因 |
| `link_alert_response(conn, event_id, response_id, ...)` | 關聯告警 ↔ 應對措施 |
| `acknowledge_alert(conn, event_id)` | 單筆確認告警 |
| `acknowledge_alerts_batch(conn, event_ids)` | 批量確認告警，回傳更新筆數 |

> ★ 為本次新增函式，對應 UI 告警卡片的 cause→response+停機時間+負責人 串聯需求。

#### 門檻值 + 知識庫（db_knowledge.py，7 支）

| 函式 | 說明 |
|------|------|
| `get_sensor_thresholds(conn, sensor_name)` | 門檻值清單 |
| `get_single_threshold(conn, sensor_name, threshold_type)` | 單一門檻值（純數值）|
| `get_solutions_for_issue(conn, component_id, issue_id)` | 排序解方清單 |
| `get_issues_for_component(conn, component_id)` | 元件已知問題 |
| `get_cause_info(conn, cause_id)` | 原因詳情 |
| `get_response_info(conn, response_id)` | 應對措施詳情 |
| `get_all_components(conn)` | 元件主檔清單 |

#### 複合查詢（db_composite.py，2 支）

| 函式 | 說明 |
|------|------|
| `get_station_dashboard_snapshot(conn, station_id)` | 儀表板快照（感測 + 狀態 + 告警數）|
| `diagnose_component(conn, component_id, issue_id)` | 診斷 + 推薦解方 |

> 所有寫入函式均不自動 commit，由呼叫端在適當時機執行 `conn.commit()`。

### 6-4. 典型使用範例

**推理引擎完整流程**：

```python
from sprayline_db_queries import (
    get_connection, insert_batch_run, get_batch_sensor_aggregates,
    get_single_threshold, upsert_batch_station_status,
    insert_alert_event, link_alert_cause, link_alert_response,
    update_batch_status,
)
from datetime import datetime, timezone

conn = get_connection()

# 1. 批次開始
insert_batch_run(conn, "B_20260614_001", datetime.now(timezone.utc))
conn.commit()

# 2. 取得批次聚合值，判斷元件狀態
agg = get_batch_sensor_aggregates(conn, "B_20260614_001", "Station_1")
fault_thresh = get_single_threshold(conn, "filter_diff_pressure_bar", "fault")
warn_thresh  = get_single_threshold(conn, "filter_diff_pressure_bar", "warning")

avg_fdp = agg["avg_filter_diff_pressure_bar"]
filter_state = "fault" if avg_fdp > fault_thresh else \
               "warning" if avg_fdp > warn_thresh else "ok"

# 3. 寫入診斷快照
upsert_batch_station_status(conn, {
    "batch_id":          "B_20260614_001",
    "station_id":        "Station_1",
    "filter_state":      filter_state,
    "filter_response_id": "REPLACE_FILTER" if filter_state == "fault" else None,
    # 其餘欄位省略（預設 None）
})

# 4. 若有異常，寫入告警
if filter_state != "ok":
    event_id = insert_alert_event(
        conn,
        batch_id="B_20260614_001", station_id="Station_1",
        sensor_name="filter_diff_pressure_bar",
        measured_value=avg_fdp, state=filter_state,
        cause="FILTER_CLOG",
    )
    link_alert_cause(conn, event_id, "FILTER_CLOG", is_primary=True)
    link_alert_response(conn, event_id, "REPLACE_FILTER")

# 5. 批次結束
update_batch_status(conn, "B_20260614_001",
                    status="warning" if filter_state != "ok" else "ok",
                    ended_time=datetime.now(timezone.utc))
conn.commit()
conn.close()
```

**DataPreprocess 寫入感測資料**：

```python
from sprayline_db_queries import get_connection, insert_sensor_readings_batch

readings = [
    {
        "ts": ..., "batch_id": "B_20260614_001", "station_id": "Station_1",
        "film_thickness_um": 15.1, "filter_diff_pressure_bar": 0.22,
        # ... 其餘感測欄位 ...
        "data_quality_flag": "正常",   # '正常' / '空值' / '突波'
    },
    # ...
]
conn = get_connection()
insert_sensor_readings_batch(conn, readings)
conn.commit()
conn.close()
```

### 6-5. 快速自我測試

```bash
cd Database/versionB
DB_PASSWORD=your_pw python sprayline_db_queries.py
```

執行後會依序呼叫 11 個讀取函式並印出結果，確認連線與資料正確。

---

## 7. WebServices / UI 整合規格（Patch Spec）

`Database/versionB/` 包含兩份修改規格文件，供後續整合 WebServices 與 UI 時參考：

| 文件 | 說明 |
|------|------|
| `WEBSERVICES_PATCH_SPEC.md` | 新增 5 個 Alert API 端點的完整程式碼片段、Request/Response schema、與 `db_alert.py` 函式的對應關係 |
| `UI_PATCH_SPEC.md` | `diagnosis_rules.json` 新增欄位規格、`renderStationDiagnosisCard()` 差異說明、停機時間/技能等級 badge CSS、確認告警按鈕 JS 實作 |

**新增端點一覽**（詳見 WEBSERVICES_PATCH_SPEC.md）：

```
GET  /api/alerts                                  → 告警清單（複合條件過濾）
GET  /api/alerts/{event_id}                       → 完整告警卡片（cause + response + 停機 + 技能）
PATCH /api/alerts/{event_id}/acknowledge          → 確認告警
GET  /api/alerts/causes/{cause_id}/responses      → 依原因查詢建議解方
GET  /api/alerts/unacknowledged/{station_id}      → 站點未確認告警
```

---

## 8. Schema 升版（Migration）

### v5 → v5.1：新增 data_quality_flag

`sensor_1min` 與 `sensor_3min` 於 2026-06-14 新增 `data_quality_flag` 欄位，
記錄 DataPreprocess 的品質標記。

| 值 | 說明 |
|----|------|
| `'正常'` | 原始值通過所有品質檢查（預設值）|
| `'空值'` | 原始為 NULL，已線性插值補值 |
| `'突波'` | IQR 離群值偵測命中，已套用 5 秒滑動平均平滑 |

**全新安裝**：`setup_db.sql` 已包含此欄位，`python setup_db.py` 即可，無需 migration。

**既有資料庫升版**：

```bash
cd Database/versionB
DB_PASSWORD=your_pw python migrate_add_data_quality_flag.py
```

Migration 特性：
- `ADD COLUMN IF NOT EXISTS`，**冪等**，重複執行安全
- 兩張表在同一 transaction，失敗自動 rollback
- 執行後自動驗證欄位存在

---

## 9. 資料表結構速查

### 核心資料表

| 資料表 | 主鍵 | 用途 |
|--------|------|------|
| `batch_run` | `batch_id` | 批次生產記錄 |
| `sensor_1min` | `(row_id, ts)` | 每分鐘感測資料（17 欄，含 PdM + 製程） |
| `sensor_3min` | `(row_id, ts)` | 環境感測資料（溫度、濕度、齒輪箱溫度） |
| `batch_station_status` | `(batch_id, station_id)` | 每批次各站元件狀態 |
| `alert_event` | `event_id` | 告警事件（append-only） |
| `sensor_threshold` | `(sensor_name, threshold_type)` | 感測器告警門檻值 |

### Station ID 命名規則

資料庫中 `station_id` 的值為：

| Station ID | 工序 | line_id（Service 層） |
|------------|------|----------------------|
| `Station_1` | 底漆（Primer） | `line_1` |
| `Station_2` | 面漆（Topcoat） | `line_2` |
| `Station_3` | 金漆（Gold Paint） | `line_3` |

> Service 層的 `station_id` 對應關係定義在 `station_config.json` 的 `"station_id"` 欄位。

---

## 10. ⚠️ 已知不一致與注意事項

### 7-1. ~~`setup_db.py` 驗證步驟誤查 `sensor_1hour`~~（已修正）

`setup_db.py` 第 86 行已將 `"sensor_1hour"` 修正為 `"sensor_3min"`，與 `setup_db.sql` 一致。

---

### 7-2. 感測器數值範圍：資料庫 vs. Service 層不一致

`generate_data.py`（寫入 DB）與 `random_data_provider.py`（Service 層 demo 資料）使用**不同的數值基準**：

| 感測器 | `generate_data.py`（DB） | `random_data_provider.py`（Service demo） |
|--------|--------------------------|------------------------------------------|
| `air_pressure_bar` | 3.0 ~ 3.5 bar | 1.4 ~ 2.8 bar |
| `spray_width_mm` | 82 ~ 120 mm | 40 ~ 56 mm |
| `paint_flow_ml_min` | 70 ~ 130 ml/min | 74 ~ 124 ml/min |

**影響**：若同時使用 DB 真實資料與 Service demo 資料進行比較，數值範圍會有明顯落差，造成誤判。真實 DB 資料接入後，`spray_width_mm` 的顯示值（82~120）會遠高於 `station_config.json` 設定的 `target_spray_width_mm`（52mm），導致 `width_error_pct` 計算異常。

**建議**：真實 DB 接入前，需統一感測器數值基準。建議更新 `station_config.json` 中各站的 `target_spray_width_mm`、`target_min_mm`、`target_max_mm` 為與 `generate_data.py` 一致的值：

```json
"Station_1": { "target_spray_width_mm": 120.0, "target_min_mm": 110.0, "target_max_mm": 130.0 },
"Station_2": { "target_spray_width_mm": 100.0, "target_min_mm":  90.0, "target_max_mm": 110.0 },
"Station_3": { "target_spray_width_mm":  82.0, "target_min_mm":  72.0, "target_max_mm":  92.0 }
```

---

### 7-3. `sensor_threshold` 部分門檻值需重新確認

`sensor_threshold` 的種子資料存在以下疑問：

| sensor_name | threshold_type | 目前值 | 與實際資料的關係 |
|-------------|---------------|--------|----------------|
| `spray_width_mm` | `warning_lo` | 95.0 | Station_3 噴幅（82mm）會持續低於此值，造成持續告警 |
| `spray_width_mm` | `warning_hi` | 125.0 | 合理，Station_1（120mm）尚在範圍內 |
| `air_pressure_bar` | `warning_lo` | 2.30 | DB 中 Station_2（3.2 bar）、Station_3（3.0 bar）遠高於此值，門檻意義不大 |
| `air_pressure_bar` | `warning_hi` | 2.70 | DB 中所有站的壓力均超過此值，會持續觸發告警 |

**修正方式**：依 `generate_data.py` 中 `STATION_CFG` 的實際數值重新設定門檻。可用以下 SQL 更新：

```sql
-- 修正 spray_width 門檻（以 Station_3 為最低基準，加 ±20mm 容許範圍）
UPDATE sensor_threshold SET value = 60.0
WHERE sensor_name = 'spray_width_mm' AND threshold_type = 'warning_lo';

UPDATE sensor_threshold SET value = 140.0
WHERE sensor_name = 'spray_width_mm' AND threshold_type = 'warning_hi';

-- 修正 air_pressure 門檻（基準為 3.0~3.5 bar，容許 ±0.3 bar）
UPDATE sensor_threshold SET value = 2.70
WHERE sensor_name = 'air_pressure_bar' AND threshold_type = 'warning_lo';

UPDATE sensor_threshold SET value = 3.80
WHERE sensor_name = 'air_pressure_bar' AND threshold_type = 'warning_hi';
```

---

### 7-4. 環境變數命名：兩套腳本使用不同前綴

| 腳本 | 環境變數前綴 | 範例 |
|------|------------|------|
| `setup_db.py` / `generate_data.py` | `DB_*` | `DB_HOST`, `DB_PASSWORD` |
| `api_server.py`（Service 層） | `SPRAYLINE_DB_*` | `SPRAYLINE_DB_HOST`, `SPRAYLINE_DB_PASSWORD` |

兩者**不能混用**，需分別設定。

---

### 7-5. `batch_run` 無 `station_id` 欄位

`batch_run` 表只記錄批次時間與狀態，**不包含** `station_id`。若要查詢特定站點的批次，必須透過 `sensor_1min` JOIN：

```sql
-- 正確做法：透過 sensor_1min 關聯站點
SELECT br.batch_id, br.start_time, br.status
FROM batch_run br
WHERE br.batch_id IN (
    SELECT DISTINCT batch_id FROM sensor_1min
    WHERE station_id = 'Station_1'
);

-- 錯誤做法（batch_run 無 station_id 欄位）
-- SELECT * FROM batch_run WHERE station_id = 'Station_1';  ← 語法錯誤
```

---

### 7-6. `sensor_1min` 複合主鍵限制

`sensor_1min` 的主鍵為 `(row_id, ts)` 複合主鍵（非單一 `ts`），因此：

- 同一時間點可以有多筆記錄（不同站點、不同批次）
- 查詢時**必須帶 `station_id` 或 `batch_id` 條件**，避免跨站重複計算
- 若在 `WHERE` 子句只用 `ts` 不加 `station_id`，結果可能重複

---

## 11. 常見問題排除

**Q：`connection refused` / `could not connect to server`**

PostgreSQL 服務未啟動，或 port/host 設定錯誤。

```powershell
# 確認服務狀態（Windows）
Get-Service -Name postgresql*

# 啟動服務
Start-Service -Name "postgresql-x64-16"
```

---

**Q：`FATAL: password authentication failed for user "postgres"`**

密碼錯誤，或 `pg_hba.conf` 要求密碼但未設定。

```powershell
# 確認環境變數是否正確設定
echo $env:DB_PASSWORD          # 建置腳本用
echo $env:SPRAYLINE_DB_PASSWORD # Service 層用
```

開發環境快速解法：將 `pg_hba.conf` 中 `local` 與 `host 127.0.0.1` 的驗證方式改為 `trust`（**僅限開發機，勿用於生產**）。

---

**Q：執行 `generate_data.py` 後 `sensor_3min` 筆數為 0**

`generate_data.py` 目前寫入的是 `sensor_1hour`（依舊版 Schema 命名），而非 `sensor_3min`。確認 `generate_data.py` 中的 INSERT 語句是否使用正確的資料表名稱。

---

**Q：`setup_db.sql` 執行到一半失敗，資料庫殘留部分資料表**

腳本在單一交易（transaction）中執行，失敗時自動 rollback，不會產生部分建立的狀態。直接重新執行 `python setup_db.py` 即可重建。

---

**Q：Service 層啟動後 `_metadata.data_type` 仍為 `"random_raw_data"`**

表示 `db_config` 未被讀取，Service 以 demo 模式運行。確認：
1. `db_config.json` 存在於 `src/` 目錄中
2. 或環境變數 `SPRAYLINE_DB_HOST` 已設定
3. 查看 `uvicorn` 啟動日誌，確認是否有 `DB config loaded from...` 訊息

---

*SETUP_GUIDE.md — 2026-06-14（Schema v5.1）*
