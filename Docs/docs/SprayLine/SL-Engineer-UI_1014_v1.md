# Spray Line Engineer UI

本頁整理 Spray Line 專案目前 Engineer UI 的實際架構、畫面功能、前後端模組、API 串接、資料來源、狀態判斷、異常診斷、趨勢圖、時間／批次檢視，以及 Docker 部署與目前已知限制。

本文件以 `final_version_0715` 內目前實際執行的程式為主要依據。`backup_before_v17`、`backup_before_v18`、`backup_before_v21` 與未被 Active Dependency 載入的 Local Demo Data Service，屬於歷史或相容程式，不作為目前主架構。

> 目前 Engineer UI 的主要定位是「產線監控、設備狀態診斷與趨勢檢視」。UI 查詢流程為 Read-only，不會因為開啟 Dashboard 或查看 Detail 就寫回 Database。Manager → Engineer 的派工、通知、確認與回報流程是另一組擴充功能，目前尚未整合進這個 Engineer Dashboard。

---

## 1. Overview

目前 Engineer UI 版本標示為：

```text
UI_V29 Engineer Integrated
```

Engineer UI 使用 FastAPI 提供 HTML、CSS、JavaScript 與 UI 專用 API。Docker 啟動後，預設位址為：

```text
http://localhost:8013
```

Engineer UI 在整個系統中的角色是：

- 顯示三個噴塗 Station 的目前狀態
- 顯示每站六個主要 Component 的數值與狀態
- 依 Sensor Threshold 將數值分類成 Normal、Warning 或 Fault
- 顯示零件或整站的問題說明、可能原因與處理建議
- 顯示製程參數與噴幅示意圖
- 顯示過去、現在與未來的 Component Trend
- 提供 Time Mode 與 Batch Mode
- 顯示 UI、Main API、Webservices 與 PostgreSQL 的連線狀態
- 每 15 秒更新目前畫面

目前主要 Engineer UI 程式位於：

```text
final_version_0715/
└── ui/
    └── engineer/
        ├── main.py
        ├── VERSION.txt
        ├── requirements.txt
        ├── config/
        │   ├── sensor_thresholds.json
        │   ├── sensor_event_mapping.json
        │   └── local_ui_reference.json
        └── app/
            ├── dependencies.py
            ├── routers/
            │   ├── dashboard.py
            │   ├── detail.py
            │   └── trend.py
            ├── services/
            │   ├── dashboard_service.py
            │   ├── webservices_client.py
            │   ├── rules_service.py
            │   ├── diagnosis_service.py
            │   ├── api_data_service.py
            │   └── local_data_service.py
            ├── templates/
            │   └── dashboard.html
            └── static/
                ├── dashboard.js
                ├── trend_chart.js
                └── dashboard.css
```

---

## 2. System Architecture

目前 Engineer UI 是一個獨立 FastAPI Web Application。Browser 不會直接呼叫 PostgreSQL，也不會直接呼叫 Main API，而是先呼叫 Engineer UI 自己的 API，再由 Engineer UI Server 轉接 Main API。

```text
User Browser
    ↓
Engineer UI :8013
    ├── HTML / CSS / JavaScript
    └── GET /api/dashboard-data
        GET /api/component-detail
        GET /api/station-detail
        GET /api/trend-data
            ↓
    DashboardService / WebservicesClient
            ↓ HTTP
Main API :8011
    ├── GET  /api/health
    ├── GET  /api/database/status
    ├── POST /api/time-series/ui/summary
    ├── POST /api/time-series/ui/station-detail
    └── POST /api/time-series/ui/component-detail
            ↓
IntegratedSprayLineService
            ↓
PostgreSQL
    ├── sensor_1min
    ├── sensor_3min
    └── batch_run
```

### 2.1 Active Components

**Engineer UI Application**

```text
ui/engineer/main.py
```

負責建立 FastAPI App、掛載 Static Files、註冊 Router、回傳首頁，以及提供 Health 與 Integration Status。

**Engineer UI Dashboard Service**

```text
ui/engineer/app/services/dashboard_service.py
```

負責把 Main API Response 轉成 Engineer Dashboard 需要的資料格式，並處理：

- 三站資料組合
- 六個 Component 數值與狀態
- Station Overall State
- Summary Count
- Diagnosis Fallback
- Trend 多時間點取樣
- Timestamp Display Mapping
- API Response Cache

**Webservices Client**

```text
ui/engineer/app/services/webservices_client.py
```

負責透過 HTTP 呼叫 Main API。Docker 中使用：

```text
WEBSERVICES_URL=http://api:8000
WEBSERVICES_SOURCE_MODE=integrated
```

**Main API UI Adapter**

```text
api/api_server.py
api/shaoyu_ui_bridge.py
```

`api_server.py` 提供 UI 專用 POST Endpoint；`shaoyu_ui_bridge.py` 將 Integrated Service Output 轉成 Summary、Station Detail 與 Component Detail 格式。

**Integrated Service**

```text
services/integrated_service/sprayline_integrated_service.py
```

負責從正式 Database 讀取 Sensor Data、建立 Current Snapshot、查詢 Batch、衍生品質指標，以及建立 Future Prediction Payload。

---

## 3. Page Layout

Engineer UI 首頁由下列四個主要區域組成。

### 3.1 Header

Header 顯示：

```text
噴塗產線監控系統
SprayingLineMonitoringSystem · UI_V29 Engineer Integrated
最後更新時間
Webservices / Database 狀態 Badge
```

### 3.2 Summary Cards

上方四張 Summary Card 顯示：

| Card | Meaning |
|---|---|
| 總站數 TotalStations | 目前顯示的 Station 數量 |
| 正常 Normal | Overall State 為 `Running` 的 Station 數量 |
| 注意 Warning | Overall State 為 `Maintenance` 的 Station 數量 |
| 預測風險 PredictRisk | Overall State 為 `Alarm` 的 Station 數量 |

Summary Count 不直接採用 Main API 的遠端統計，而是依 Engineer UI 已建立的三張 Station Card 重新計算。

### 3.3 Integration Status

Connection Panel 顯示：

- Engineer UI 是否連到 Main API
- Main API 是否連到 PostgreSQL
- Summary、Station Detail、Component Detail API 是否可用
- Main API Base URL
- API Source Mode
- Database Name

使用者可按下「重新檢查」執行完整 Integration Status Check。

### 3.4 Station Area

目前固定顯示三個 Station：

| UI ID | Line ID | Database Station | 中文名稱 | English Name |
|---|---|---|---|---|
| `M1` | `line_1` | `Station_1` | 底漆站 | Primer Station |
| `M2` | `line_2` | `Station_2` | 面漆站 | Topcoat Station |
| `M3` | `line_3` | `Station_3` | 金漆站 | Gold Paint Station |

每張 Station Card 包含：

- Station Name
- Overall State Badge
- 六個 Component Card
- Station Fault Detail Button
- Process Parameters Panel
- Spray Width Image Panel
- Trend Chart Panel

### 3.5 Time Point Viewer

畫面底部提供單一時間點檢視：

```text
Time Mode
Batch Mode
Back To Live
Past / Now / Future Indicator
Range Slider
Selected Time Description
```

在 `slider_value = 0` 時，UI 每 15 秒自動更新。使用者切換到過去或未來時間點後，自動更新會暫停，以免歷史檢視被最新資料覆蓋。

---

## 4. Station and Component Model

每個 Station 固定顯示六個主要 Component。

| UI Key | Service Component | Component ID | Display Name | Primary Metric | Unit |
|---|---|---|---|---|---|
| `arm` | `robot_arm` | `ROBOT_ARM` | 機械手臂 | `servo_torque_load_pct` | `%` |
| `nozzle` | `nozzle` | `NOZZLE` | 噴嘴 | `paint_flow_ml_min` | `ml/min` |
| `air` | `air_compressor` | `AIR_COMPRESSOR` | 空壓機 | `air_pressure_bar` | `bar` |
| `width` | `spray_width` | `SPRAY_WIDTH` | 噴幅 | `spray_width_mm` | `mm` |
| `filter` | `filter_mesh` | `FILTER` | 濾網 | `filter_diff_pressure_bar` | `bar` |
| `quality` | `quality_module` | `QUALITY` | 品質 | `film_thickness_um` | `µm` |

每個 Component Card 顯示：

```text
Icon
中文名稱
英文名稱
Primary Metric Value
正常 / 注意 / 異常
點擊查看狀態、原因與趨勢
```

---

## 5. Engineer UI Internal APIs

Engineer UI 自己提供四個主要 GET Endpoint。

### 5.1 Dashboard Data

```http
GET /api/dashboard-data?mode=time&slider_value=0
```

用途：

- 取得 Database Status
- 呼叫 Summary API
- 呼叫三次 Station Detail API
- 呼叫三站 × 六元件的 Component Detail API
- 建立 Station Cards
- 重新計算 Summary

### 5.2 Component Detail

```http
GET /api/component-detail
    ?station_id=M1
    &component_key=filter
    &mode=time
    &slider_value=0
    &snapshot_seed=...
```

用途：顯示單一 Component 的目前數值、狀態、問題、原因、處理建議與 Mapping ID。

### 5.3 Station Detail

```http
GET /api/station-detail
    ?station_id=M1
    &mode=time
    &slider_value=0
    &snapshot_seed=...
```

用途：重新呼叫 Station Detail 及六個 Component Detail，列出該站所有非正常 Component。

### 5.4 Trend Data

```http
GET /api/trend-data
    ?station_id=M1
    &component_key=filter
    &mode=time
    &slider_value=0
    &snapshot_seed=...
```

用途：取得 Trend Points、Threshold Reference、Selected Snapshot 與 Chart Metadata。

### 5.5 Health and Integration Status

```http
GET /api/health
GET /api/integration-status
```

`/api/health` 回傳 Engineer UI Version 與主要 Integration Route；`/api/integration-status` 會實際檢查 Main API、Database 與三個 UI Service API。

---

## 6. Main API Integration

Engineer UI 透過 `WebservicesClient` 呼叫 Main API：

```text
GET  /api/health
GET  /api/database/status
POST /api/time-series/ui/summary
POST /api/time-series/ui/station-detail
POST /api/time-series/ui/component-detail
```

共用 Request Payload 主要包含：

```text
schema_version
request_id
mode
window_type
slider_value
ui_slider_value
ui_slider_unit
source_mode
random_seed
line_scope / line_id
component_name
```

Main API 會強制把 UI Query 設為：

```text
source_mode = integrated
```

並執行：

```text
run_integrated_service_query(..., write_back=False)
```

因此目前 Summary、Station Detail、Component Detail 與 Trend Query 都是 Read-only。

---

## 7. Data Flow

### 7.1 Dashboard Load

```text
Browser GET /api/dashboard-data
       ↓
Engineer DashboardService
       ├── GET Database Status
       ├── POST Summary
       ├── POST Station Detail × 3
       └── POST Component Detail × 18
                 ↓
       Build Component Cards
                 ↓
       Aggregate Station State
                 ↓
       Recalculate Summary
                 ↓
       Browser Render
```

### 7.2 Component Click

```text
Click Component Card
       ↓
GET Engineer /api/component-detail
       ↓
POST Main API component-detail
       ↓
Update Component Value and State
       ↓
Update Station Overall State
       ↓
Update Top Summary Count
       ↓
Open Component Diagnosis
       ↓
Open Matching Trend Chart
```

### 7.3 Station Detail

```text
Click FaultDetail / NoFault
       ↓
GET Engineer /api/station-detail
       ↓
POST Station Detail
POST Component Detail × 6
       ↓
Filter level != ok
       ↓
Display all Warning / Fault components
```

### 7.4 Read-only Behavior

Engineer UI Query 不會執行：

```text
insert_alert_event
upsert_batch_station_status
insert_future_prediction_result
```

Database Write-back 必須由其他明確的 Service Orchestration Endpoint 或 Monitoring Worker 執行。

---

## 8. Status and Threshold Logic

### 8.1 State Mapping

Engineer UI 使用：

```text
normal  → ok
warning → warn
fault   → bad
```

畫面顏色：

| UI Level | Display | Color |
|---|---|---|
| `ok` | 正常 | Green |
| `warn` | 注意 | Orange |
| `bad` | 異常 | Red |

### 8.2 Metric-first Classification

Component Status 的實際優先順序是：

```text
Main API Metric Value
       ↓
Engineer UI sensor_thresholds.json
       ↓
normal / warning / fault
```

只有在主要 Metric 不存在時，才會嘗試使用 Main API 的 `component_state`。如果 Primary Metric 完全不存在，UI 會將該 Component 標成 Warning，避免無資料時誤顯示為正常。

### 8.3 Current UI Thresholds

| Sensor | Normal | Warning | Fault |
|---|---|---|---|
| `filter_diff_pressure_bar` | `0–0.30` | `>0.30–0.50` | `>0.50` |
| `servo_torque_load_pct` | `0–50` | `>50–60` | `>60` |
| `air_pressure_bar` | `3.0–3.35` | `2.8–<3.0` or `>3.35–3.6` | `<2.8` or `>3.6` |
| `paint_flow_ml_min` | `105–118` | `100–<105` or `>118–125` | `<100` or `>125` |
| `spray_width_mm` | `75–125` | `65–<75` or `>125–135` | `<65` or `>135` |
| `film_thickness_um` | `14.6–15.4` | `14.2–<14.6` or `>15.4–15.8` | `<14.2` or `>15.8` |

### 8.4 Station Aggregation

Station Overall State 取六個 Component 中最嚴重者：

```text
All Components OK
    → Running

Any Component Warn, no Bad
    → Maintenance

Any Component Bad
    → Alarm
```

Risk Text 對應：

```text
Running     → 低風險
Maintenance → 中風險
Alarm       → 高風險
```

### 8.5 Summary Aggregation

上方 Summary 依 Station Card 重新計算：

```text
normal_count       = Running Station Count
warning_count      = Maintenance Station Count
predict_risk_count = Alarm Station Count
```

這樣可以避免遠端 Summary 仍顯示 Normal，但 Component Detail 已經出現 Warning 或 Fault 時，Station Header 與 Summary 仍保持綠色。

---

## 9. Diagnosis and Recommendation

### 9.1 Preferred Source

如果 Service API Response 有 `troubleshooting`，Engineer UI 會優先使用：

```text
state_name / state_description
cause
countermeasure
countermeasure_id
troubleshooting_state
cause_id
```

### 9.2 Current Fallback Behavior

目前 `shaoyu_ui_bridge.py` 的 Component Detail Output 沒有輸出 `troubleshooting`，因此現有流程通常會使用 Engineer UI 本機 Fallback：

```text
Sensor Name
    ↓
sensor_event_mapping.json
    ↓
issue_state / cause_id / response_ids
    ↓
diagnosis_service.py
    ↓
問題說明 / 可能原因 / 處理建議
```

代表性 Mapping：

| Sensor | Issue State | Cause | Response |
|---|---|---|---|
| `filter_diff_pressure_bar` | `FILTER_CLOG` | `FILTER_CLOG` | `REPLACE_FILTER`, `BACKWASH_FILTER` |
| `paint_flow_ml_min` | `NOZZLE_CLOG` | `NOZZLE_CLOG` | `CLEAN_NOZZLE`, `REPLACE_NOZZLE` |
| `air_pressure_bar` | `AIR_PRESSURE_UNSTABLE` | `AIR_PRESSURE_UNSTABLE` | `CALIBRATE_PRESSURE_VALVE` |
| `spray_width_mm` | `SPRAY_WIDTH_DEVIATION` | `SPRAY_WIDTH_DEVIATION` | `ADJUST_TCP_Z`, `ADJUST_FLOW_PRESSURE`, `REPLACE_NOZZLE` |
| `servo_torque_load_pct` | `SERVO_OVERLOAD` | `SERVO_WEAR` | `LUBRICATE_SERVO`, `REPLACE_SERVO` |
| `film_thickness_um` | `FILM_THICKNESS_OOC` | `THICKNESS_DRIFT` | `ADJUST_SPEED_FLOW`, `CALIBRATE_ENV_CONTROL` |

目前 `sensor_event_mapping.json` 自己標示為：

```text
draft_pending_yucheng_confirmation
```

因此 Cause ID 與 Response ID 應視為目前 Mapping，而不是已完成最終確認的正式知識表。

---

## 10. Process Parameters and Spray Width Image

### 10.1 Process Parameters

每站 Process Panel 顯示：

```text
Recipe
Temperature
Humidity
Utilization
Cycle Time
Timestamp
```

若 Main API 沒有提供欄位，畫面顯示 `--`。

### 10.2 Spray Width Image

Engineer UI 使用前端 SVG 畫出噴嘴、噴塗扇形、目標範圍與目前噴幅。

顏色依 `spray_width` Component State：

```text
Normal  → Green
Warning → Orange
Fault   → Red
```

如果 Station Detail 沒有提供 `target_min_mm` / `target_max_mm`，目前 Fallback 為：

```text
105–125 mm
```

但目前 `sensor_thresholds.json` 對 `spray_width_mm` 的 Normal Range 是：

```text
75–125 mm
```

因此 Spray Width Image 顯示的目標範圍與 Component Status 判斷門檻目前可能不一致。

---

## 11. Trend Chart

### 11.1 Chart Components

每站 Trend Panel 提供六個 Tab：

```text
機械手臂
噴嘴
空壓機
噴幅
濾網
品質
```

點擊上方 Component Card 時，會自動切換到對應的 Trend Tab。

### 11.2 Trend Data Generation

目前 Trend Chart 不直接顯示 Main API Response 內的一段原始 `time_series.points`。

Time Mode 會對下列 Slider Point 逐點呼叫 Component Detail：

```text
-6, -5, -4, -3, -2, -1, 0, +1, +2, +3, +4
```

Batch Mode 預設取樣：

```text
-10, -8, -6, -4, -2, 0, +2, +4, +6, +8, +10
```

每一點皆透過 Main API 的 Component Detail Query 取得。

### 11.3 Trend Post-processing

取得各時間點後，Engineer UI 會：

```text
1. 將各點轉成 Float
2. 執行三點 Moving Average
3. 平移整條曲線，使選中點等於上方 Component Card Value
4. 保留原始值為 raw_service_value
5. 限制相鄰點最大變化，避免曲線不連續
6. 依 UI Threshold 重新分類每一點
```

因此 Trend Chart 是以 Service API Query 為基礎、經 UI 平滑處理後的顯示曲線，不是 Database Raw Time-series 的完全原樣輸出。

### 11.4 SVG Rendering

前端 `trend_chart.js` 使用 SVG 顯示：

| Visual | Meaning |
|---|---|
| 灰色實線 | Past and Current |
| 紫色虛線 | Future Prediction |
| 綠點 | Normal |
| 橘點 | Warning |
| 紅點 | Fault |
| 黑色垂直虛線 | Now |
| 藍色垂直虛線及藍圈 | Selected Snapshot |
| 淡綠色區域 | Normal Threshold Band |

### 11.5 Request Race Protection

前端會為 Dashboard 與 Trend Request 保存 Request Sequence。若使用者快速移動 Slider，較舊的 Response 即使較晚回來，也不會覆蓋較新的畫面。

---

## 12. Time Mode

### 12.1 UI Definition

Time Mode Slider：

```text
min  = -6
max  = +4
step = 1
```

畫面標示：

```text
-6 → 過去 6 小時
 0 → 現在
+4 → 未來 2 小時
```

Engineer UI 的 Display Label 規則是：

```text
負值：每格顯示為 1 小時
正值：每格顯示為 0.5 小時
```

### 12.2 Current Backend Interpretation

`WebservicesClient` 目前將 Slider 原值直接送到 Main API。

但是 `IntegratedSprayLineService.build_time_window()` 實際使用：

```text
Past:
anchor_time = now - abs(slider_value) minutes

Future:
prediction_time = now + slider_value minutes
```

也就是目前存在 Unit Mismatch：

```text
UI 顯示：小時
Backend 查詢：分鐘
```

例如 UI 顯示「過去 6 小時」時，Main API 目前實際使用的 Offset 可能是「過去 6 分鐘」。

這是目前 Time Mode 最重要的已知限制。

---

## 13. Batch Mode

Batch Mode Slider：

```text
min  = -10
max  = +10
step = 1
```

顯示方式：

```text
slider = 0  → 目前批次
slider < 0  → 過去第 N 批
slider > 0  → 未來第 N 批
```

Integrated Service 會查詢：

```text
batch_run
JOIN sensor_1min
```

並只選擇實際在該 Station 有 Sensor Data 的 Batch。

Past Batch 會查詢選定 Batch 的：

```text
sensor_1min
sensor_3min
```

Future Batch 目前仍以 Anchor Batch／Latest Batch 作為 Model Input，再建立 Future Prediction Payload。

Engineer UI Request 目前沒有傳送固定的 `anchor_batch_id`，因此 DataProcess 持續新增 Batch 時，最新 Batch Anchor 可能隨更新改變。

---

## 14. Past, Current and Future Data

### 14.1 Past / Current

Past 與 Current 的正式資料來源為：

```text
Database/versionB sensor_1min
Database/versionB sensor_3min
```

Current Snapshot 使用：

```text
Latest sensor_1min row
+
Latest sensor_3min temperature_c / humidity_rh
```

### 14.2 Data Anchor

DataProcess 使用自己的模擬時間軸，Database 最新資料時間可能與電腦現在時間不同，甚至已經位於未來年份。

因此 Integrated Service 會讀取各站最新 `sensor_1min.ts`，以 Database 最新時間作為 Data Anchor。

### 14.3 Future Prediction

目前 Future Prediction 使用 deterministic formula，不是已訓練完成的正式 Machine Learning Model。

主要邏輯：

```text
Current Snapshot
    ↓
Quality Score
    ↓
依 Prediction Distance 套用品質衰退
    ↓
predicted_ok_rate
estimated_defect_rate_pct
predicted_ng_count
```

目前 `prediction_method` 為：

```text
deterministic_formula
```

`model_input_source` 為：

```text
IntegratedSprayLineService:past_current_window
```

正式模型可日後替換，但目前文件不應將這一段描述成正式 AI／ML Prediction Model。

---

## 15. Timestamp Handling

UI_V29 為了處理 Database 模擬時間與使用者電腦時間不一致，將時間拆成兩種語意。

### 15.1 Display Timestamp

Station Card 與 Process Panel 顯示：

```text
viewer / slider selected time
```

此時間跟隨使用者目前電腦時間與 Slider Label。

### 15.2 Data Timestamp

原始 PostgreSQL Timestamp 保存在：

```text
station.data_timestamp
process_parameters.data_timestamp
viewer_state.data_anchor_time
```

這樣畫面不會直接顯示 2029 或 2032 等模擬時間，但 Response 仍保留原始資料時間供追蹤。

### 15.3 Trend Timestamp

Trend Payload 同時保留：

```text
ui_selected_time
data_anchor_time
selected_snapshot.timestamp
selected_snapshot.data_timestamp
```

目前 Chart Point Timestamp 以取樣流程建立的時間為主，Selected Snapshot 則同時保留 UI 與 Data Time。

---

## 16. Data Quality

Integrated Service 的 Time-series Point 會保留：

```text
data_quality_flag
```

但是目前 Engineer UI：

- 沒有在 Component Card 顯示 Data Quality
- 沒有在 Trend Legend 顯示 Normal／Interpolated Data Quality
- 沒有在 UI Layer 排除 `interpolated` Row
- Current Snapshot 直接取查詢範圍內最新 Sensor Row

因此目前 UI 的綠／橘／紅代表 Threshold State，不代表資料一定是原始量測或已補值資料。

---

## 17. Error Handling and Fallback

### 17.1 Database Offline

如果 `/api/database/status` 回傳未連線：

```text
summary = 0
stations = []
integration.database_connected = false
```

畫面顯示 Database 或 Service API Error，不會切換到 Local Demo Data。

### 17.2 Summary API Failure

如果 Summary API 失敗，Engineer UI 回傳空 Station List 與 Integration Error。

### 17.3 Station Detail Failure

若單一 Station Detail 失敗，UI 會嘗試使用 Summary Station 建立可見的 Fallback Card，並將詳細資料標示為待確認。

### 17.4 Component Detail Failure

如果某個 Component Detail 失敗：

- Dashboard 保留該站其他 Component
- 保存 `component_errors`
- 無主要指標的 Component 可能標成 Warning

### 17.5 No Demo Fallback

Main API 的 Formal UI Endpoint 已明確設定：

```text
fallback_to_demo = False
```

因此正式 Engineer UI 不會在 Database 斷線時靜默產生假資料。

---

## 18. Refresh, Cache and Request Volume

### 18.1 Refresh Interval

目前 Engineer UI：

```text
AUTO_REFRESH_MS = 15000
```

只有在：

```text
autoUpdate = true
slider_value = 0
```

時自動更新。

### 18.2 Server Cache

Dashboard Service 依下列資訊保存 Cache：

```text
snapshot_seed
mode
slider_value
station_id
component_key
```

Cache 分為：

```text
station_cache
component_cache
trend_cache
```

Database Status 另有 5 秒 Cache。

### 18.3 Dashboard Request Volume

一次完整 Dashboard Refresh 大約會執行：

```text
Database Status         × 1
Summary                 × 1
Station Detail          × 3
Component Detail        × 18
```

也就是約 23 個上游 Request。

單一 Trend Load 會對約 11 個 Slider Point 進行 Component Detail 取樣。若多站 Trend 同時展開，Refresh 後也會重新載入。

因此目前設計可提供完整且同步的 Component 資訊，但正式部署時應注意 Main API 與 PostgreSQL 負載。

---

## 19. Docker Deployment

目前 `docker-compose.yml` 相關 Service：

| Service | Role | Host Port |
|---|---|---:|
| `db` | PostgreSQL | `5433 → 5432` |
| `api` | Main API | `8011 → 8000` |
| `frontend` | Manager UI | `8012 → 8002` |
| `engineer` | Engineer UI | `8013 → 8000` |

Engineer Service：

```text
working_dir = /app/ui/engineer
command = python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

主要 Environment：

```text
MANAGER_UI_URL=http://localhost:8012
SPRAYLINE_API_BASE=http://api:8000
WEBSERVICES_URL=http://api:8000
API_BASE_URL=http://api:8000
WEBSERVICES_SOURCE_MODE=integrated
```

目前 Active `WebservicesClient` 實際使用的是：

```text
WEBSERVICES_URL
WEBSERVICES_SOURCE_MODE
```

`SPRAYLINE_API_BASE` 只被目前未啟用的 `ApiDataService` 使用；`MANAGER_UI_URL` 與 `API_BASE_URL` 在 Active Engineer UI Path 中沒有被引用。

### 19.1 Startup

`start.ps1` 啟動：

```text
api
frontend
engineer
```

Engineer UI 依賴 Main API，但 Compose 的 `depends_on` 只保證 Container 啟動順序，不保證所有 API Query 已完成初始化，因此首頁已實作 Connection Status 與 Error Panel。

---

## 20. Active and Legacy Files

### 20.1 Active Runtime Files

```text
ui/engineer/main.py
ui/engineer/app/dependencies.py
ui/engineer/app/routers/dashboard.py
ui/engineer/app/routers/detail.py
ui/engineer/app/routers/trend.py
ui/engineer/app/services/dashboard_service.py
ui/engineer/app/services/webservices_client.py
ui/engineer/app/services/rules_service.py
ui/engineer/app/services/diagnosis_service.py
ui/engineer/app/templates/dashboard.html
ui/engineer/app/static/dashboard.js
ui/engineer/app/static/trend_chart.js
ui/engineer/app/static/dashboard.css
ui/engineer/config/sensor_thresholds.json
ui/engineer/config/sensor_event_mapping.json
```

### 20.2 Present but Not Active

目前沒有被 `dependencies.py` 或 Active Runtime Import：

```text
ui/engineer/app/services/api_data_service.py
ui/engineer/app/services/local_data_service.py
ui/engineer/app/services/backup_before_v17/
ui/engineer/app/services/backup_before_v18/
ui/engineer/app/services/backup_before_v21/
```

`LocalDataService` 可產生本機模擬資料；`ApiDataService` 是另一個相容 Adapter。但目前實際依賴鏈為：

```text
DashboardService
    ↓
WebservicesClient
    ↓
Main API
```

---

## 21. Engineer Task Workflow Boundary

Repository 另有 Manager → Engineer Workflow：

```text
api/engineer_task_models.py
api/engineer_task_service.py
api/engineer_task_router.py
database/db_engineer_task.py
apps_script/engineer_task_web_app.gs
ui/manager/main/engineer-task-api.js
ui/manager/main/engineer-ack.js
```

但目前 `ui/engineer/` 沒有引用上述模組，因此目前 Engineer Dashboard 不包含：

- Engineer Task Inbox
- Manager 派工通知
- Engineer Acknowledge
- Task Status Update
- Work Report
- Attachment Upload

這組 Engineer Task Workflow 應視為獨立擴充，不應在 Engineer UI 文件中描述成已整合完成的畫面功能。

---

## 22. Known Version and Documentation Notes

目前 Active Engineer UI 內保留多個版本名稱：

| Location | Version Label |
|---|---|
| `main.py` / HTML Title | UI_V29 |
| `VERSION.txt` | UI_V29 based on UI_V28 |
| `dashboard.js` Console | UI_V27 |
| CSS / JS Query String | V28 |
| Dashboard Response Schema | UI_V16 Database Integrated |
| Source Code Comments | V18–V29 |

這些名稱是多次 Patch 累積留下的歷史標示，不代表 Runtime 同時運行多套 Engineer UI。正式說明應以目前 Active File 為準，版本總稱使用：

```text
UI_V29 Engineer Integrated
```

---

## 23. Known Limitations

### 23.1 Time Slider Unit Mismatch

UI 顯示小時，但 Integrated Service 目前把 Slider Value 當成分鐘。Time Mode Label 與實際查詢範圍尚未完全對齊。

### 23.2 UI and Backend Thresholds Are Different

Engineer UI 使用：

```text
ui/engineer/config/sensor_thresholds.json
```

Main API Runtime Rule 使用 Ontology／共用 Rule Source。兩者目前有不同 Threshold，例如 Servo Load、Filter Differential Pressure、Air Pressure 與 Spray Width。

因此 UI 顯示狀態可能與 Main API 回傳的 Component State 不一致。目前 UI 刻意以顯示數值重新判定為主。

### 23.3 Trend Is a Processed Display Curve

Trend 經過 Multi-time Sampling、Moving Average、Shift 與 Neighbor Clamp，不應描述成 Database Raw Curve。

### 23.4 Troubleshooting Uses Local Fallback

目前 UI Adapter 沒有把完整 Troubleshooting Payload 傳到 Component Detail，因此畫面通常使用本機 Mapping 與 Diagnosis Catalog。

### 23.5 Spray Width Target Range Mismatch

Spray Image Fallback 顯示 `105–125 mm`，UI Threshold 使用 `75–125 mm`。

### 23.6 Data Quality Is Not Exposed

UI 未顯示或篩選 `data_quality_flag`，使用者無法從畫面辨認該點是 `normal` 或 `interpolated`。

### 23.7 Request Volume

每 15 秒的 Dashboard Refresh 會呼叫大量 Station／Component API；Trend 又進行多時間點查詢。

### 23.8 Integration Status Text Difference

畫面 Connection Detail 顯示「Component API：點擊零件時呼叫」，但 Dashboard Initial Load 實際已呼叫三站共 18 次 Component Detail。

### 23.9 No Engineer Dashboard-specific Automated Tests

目前 Repository 的 `test_engineer_task_*` 測試 Engineer Task API，不是 Engineer Dashboard。尚未看到針對 Dashboard Payload、Threshold、Slider、Trend 與 Frontend Interaction 的專用自動測試。

### 23.10 Runtime Visual Verification

本文件已依 Active Source Code、Docker Compose 與 API Call Chain 交叉確認。但本次整理環境沒有可使用的 `docker` 指令，因此尚未完成 Container 實際啟動後的 End-to-end Visual Verification。

---

## 24. Implementation References

本頁主要依據下列實際檔案：

```text
final_version_0715/ui/engineer/main.py
final_version_0715/ui/engineer/VERSION.txt
final_version_0715/ui/engineer/app/dependencies.py
final_version_0715/ui/engineer/app/routers/dashboard.py
final_version_0715/ui/engineer/app/routers/detail.py
final_version_0715/ui/engineer/app/routers/trend.py
final_version_0715/ui/engineer/app/services/dashboard_service.py
final_version_0715/ui/engineer/app/services/webservices_client.py
final_version_0715/ui/engineer/app/services/rules_service.py
final_version_0715/ui/engineer/app/services/diagnosis_service.py
final_version_0715/ui/engineer/app/services/api_data_service.py
final_version_0715/ui/engineer/app/services/local_data_service.py
final_version_0715/ui/engineer/app/templates/dashboard.html
final_version_0715/ui/engineer/app/static/dashboard.js
final_version_0715/ui/engineer/app/static/trend_chart.js
final_version_0715/ui/engineer/app/static/dashboard.css
final_version_0715/ui/engineer/config/sensor_thresholds.json
final_version_0715/ui/engineer/config/sensor_event_mapping.json
final_version_0715/api/api_server.py
final_version_0715/api/shaoyu_ui_bridge.py
final_version_0715/api/database_status.py
final_version_0715/services/integrated_service/sprayline_integrated_service.py
final_version_0715/services/event_rule_service/runtime_rule_classifier.py
final_version_0715/services/integration_adapter/database_versionb_adapter.py
final_version_0715/docker-compose.yml
final_version_0715/start.ps1
final_version_0715/INTEGRATION_0715.md
final_version_0715/README_0620ver_1_hotfix.md
```

---

## 25. Short System Summary

```text
PostgreSQL sensor_1min / sensor_3min / batch_run
                    ↓
       IntegratedSprayLineService
       ├── Past / Current DB Query
       ├── Batch Resolution
       ├── Derived Metrics
       └── Deterministic Future Prediction
                    ↓
             Main API :8011
       ├── UI Summary
       ├── Station Detail
       └── Component Detail
                    ↓
          Engineer UI Server :8013
       ├── Local Threshold Classification
       ├── Station / Summary Aggregation
       ├── Diagnosis Fallback
       ├── Multi-time Trend Sampling
       └── Display Timestamp Mapping
                    ↓
                Browser
       ├── 3 Stations
       ├── 6 Components per Station
       ├── Fault / Recommendation
       ├── Process / Spray Image
       ├── Trend Chart
       └── Time / Batch Viewer
```

這是目前 `final_version_0715` Engineer UI 的主要架構與實際資料流。
