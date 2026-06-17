# SprayLine 整合報告

**日期**：2026-06-16  
**主題**：TimeSeriesService、versionB DB API、少榆 B 版 Service Orchestration 整合  


---

## 一句話總結

今天主要完成的是：

> 將原本分散在 **TimeSeriesService、versionB DB function、少榆 Future / Monitoring / Rule / Troubleshooting 模組** 的功能，整理成一個可以由 API 統一呼叫的整合架構。

重點不是把所有功能重寫，而是把各自負責的模組接起來：

| 負責範圍 | 負責內容 | 今日整合方式 |
|---|---|---|
| 我的 TimeSeriesService | Past / Current / Future 原本 API、UI summary/detail 格式 | 先保留既有 API，避免原流程壞掉 |
| 少榆模組 | Future、Monitoring、EventRule、Troubleshooting、Rule / Ontology | 透過 Service Orchestration Adapter 呼叫 |
| 余同學 versionB | PostgreSQL schema、DB function、Alert / Status / Sensor 查詢 | 透過 versionB adapter 包成 API |
| API Server | 對外提供 HTTP endpoint 給 UI / 測試工具 | 新增統一 FastAPI 入口 |

# 1. 今天整合的主線

今天的工作可以用三層架構來理解：

```text
UI / 測試工具
    ↓
FastAPI API Server
    ↓
Service Orchestration Adapter
    ↓
各功能模組
    ├─ 我的 TimeSeriesService
    ├─ 少榆 Future / Monitoring / EventRule / Troubleshooting
    └─ 余同學 versionB DB function
```

也就是說，今天不是把功能全部混在一起，而是做出一個**統一入口**：

```text
API 負責對外
各 service 負責自己的功能
DB function 負責 PostgreSQL 資料存取
```

這樣後續 UI 不需要知道每個功能是誰做的，只要 call API 即可。

# 2. 整合前後差異

## 2.1 整合前

整合前各自是分開的：

| 模組 | 狀態 | 問題 |
|---|---|---|
| TimeSeriesService | 已可輸出 Past / Current / Future 與 UI summary | 和少榆 Future / Rule 有重疊可能 |
| 少榆 0616 B 版 | 有 Future / Monitoring / EventRule / Troubleshooting function | 原本沒有完整對外 API Server |
| versionB DB | 有 PostgreSQL schema 與 DB function | Service  無法直接呼叫 Python DB function |
| UI | 需要 HTTP API | 不知道該直接接哪個模組 |

## 2.2 整合後

整合後的定位變成：

| 模組 | 新定位 |
|---|---|
| API Server | 對外 HTTP 入口 |
| Service Orchestration Adapter | 統一呼叫各 service function |
| TimeSeriesService | 保留既有 API 與資料格式，作為目前可用主流程 |
| 少榆 service | 負責 Future / Rule / Monitoring / Troubleshooting |
| versionB DB function | 負責 PostgreSQL 讀寫，不被 API 重寫 |

# 3. 今日完成項目總覽

| 編號 | 今日完成項目 | 說明 |
|---:|---|---|
| 1 | 整理 V4 / B 方案既有內容 | 確認 Monitoring、Alert、Future、Troubleshooting payload 已存在 |
| 2 | 建立 versionB API 對接層 | 把 DB function 包成 HTTP API |
| 3 | 加入 DB fallback | DB 未連線時不讓主服務中斷 |
| 4 | 檢查少榆 0616 B 版 | 確認有 Future、Monitoring、EventRule、Troubleshooting 相關模組 |
| 5 | 將 TimeSeriesService API 放入少榆 B 版 | 讓整合包具備 FastAPI 對外入口 |
| 6 | 新增 Service Orchestration Adapter | 讓 API 可以呼叫少榆 function |
| 7 | Rule / Ontology | API 只呼叫少榆 function |
| 8 | 整理今日報告 | 將整合內容整理成可報告版本 |

# 4. 方案原本已具備的功能

 方案的重點是讓 TimeSeriesService 不只回傳 KPI，而是可以同時產生監控、告警、預測與診斷 payload。

## 4.1 已補齊的資料內容

| 類別 | 內容 |
|---|---|
| component_metrics | 8 個 component 的狀態資料 |
| sensor 欄位 | 對齊少榆規則與 DB 所需 sensor 名稱 |
| EventRule | 依 threshold 判斷 normal / warning / fault |
| component_overview | 彙整各元件狀態 |
| fault_detail | 產生異常細節 |
| monitoring payload | 監控資料輸出 |
| alert_event payload | 告警事件輸出 |
| batch_station_status payload | 批次站點狀態輸出 |
| future_prediction payload | 未來預測輸出 |
| troubleshooting payload | 故障排除建議輸出 |

## 4.2 component_metrics 補齊 8 個 component

| component | 中文說明 | 用途 |
|---|---|---|
| quality_module | 品質模組 | 厚度、覆蓋率、品質分數 |
| nozzle | 噴嘴 | 流量、堵塞率、噴嘴角度 |
| filter_mesh | 濾網 | 壓差、流入流出、濾網狀態 |
| pump_unit | 泵浦 | 電流、壓力、流量 |
| air_compressor | 空壓機 | 空壓與供氣狀態 |
| spray_width | 噴幅 | 噴幅寬度與偏差 |
| robot_arm | 機械手臂 | 路徑誤差、扭矩、振動 |
| environment | 環境 | 溫度、濕度、資料品質 |

# 5. Sample Method：Past / Current / Future 怎麼取資料

這是今天報告裡最容易混亂的部分，建議報告時用這張表說明：

| time_type | slider_value | sample_method | 資料意義 | 為什麼這樣取 |
|---|---:|---|---|---|
| past | `< 0` | `mean` | 已發生的歷史區間 | 用平均代表整段歷史狀態 |
| current | `= 0` | `recent_average` | 現在附近的即時資料 | 用最近幾筆平均，避免單筆雜訊 |
| future | `> 0` | `latest_valid` | 模型或規則推估的未來狀態 | 用最後有效預測值，避免平均稀釋風險 |

## 5.1 範例

假設 future 預測有三筆：

| 預測序列 | risk |
|---|---|
| 第 1 筆 | normal |
| 第 2 筆 | warning |
| 第 3 筆 | fault |

如果用平均，最後可能只看起來像 warning；但實際上最後一筆已經是 fault。  
因此 future 採用：

```text
sample_method = latest_valid
```

代表取最後一筆有效預測值作為未來狀態。

# 6. versionB API 對接層

versionB 是余同學提供的 DB schema 與 DB function。今日做的事情不是重寫 ，而是把 function 包成 API。

## 6.1 versionB 對應資料表

| 資料表 | 用途 |
|---|---|
| alert_event | 告警事件 |
| alert_cause_link | 告警與原因關聯 |
| alert_response_link | 告警與建議處理方式關聯 |
| batch_station_status | 批次站點狀態 |
| sensor_1min | 製程感測資料 |
| sensor_3min | 環境感測資料 |
| component_catalog | 元件主檔 |
| issue_catalog | 問題主檔 |
| solution_catalog | 解法主檔 |
| component_issue_solution_map | 元件、問題、解法對照 |

## 6.2 新增檔案

| 檔案 | 功能 |
|---|---|
| `versionb_loader.py` | 尋找 versionB 資料夾並載入 DB function |
| `versionb_alert_adapter.py` | 包裝 alert 相關 DB function |
| `db_config.example.json` | PostgreSQL 連線設定範例 |
| `external/versionB/` | 保留 versionB 原始參考檔 |

# 7. versionB Alert API

新增的 API 如下：

| API | 功能 | 實際呼叫 |
|---|---|---|
| `GET /api/versionb/status` | 檢查 versionB / DB 狀態 | `versionb_loader.get_versionb_status()` |
| `GET /api/alerts` | 查詢告警列表 | `get_alerts_by_filters()` |
| `GET /api/alerts/{event_id}` | 查詢告警詳細卡片 | `get_alert_ui_card()` |
| `PATCH /api/alerts/{event_id}/acknowledge` | 確認告警 | `acknowledge_alert()` |
| `GET /api/alerts/causes/{cause_id}/responses` | 依原因查解方 | `get_responses_for_cause()` |
| `GET /api/alerts/unacknowledged/{station_id}` | 查未確認告警 | `get_unacknowledged_alerts()` |

## 7.1 呼叫範例

```http
GET /api/alerts?station_id=Station_1&acknowledged=false
```

回傳概念：

```json
{
  "db_available": true,
  "alerts": [
    {
      "event_id": "EVT_001",
      "station_id": "Station_1",
      "state": "warning",
      "sensor_name": "filter_diff_pressure_bar",
      "measured_value": 0.35
    }
  ],
  "total": 1
}
```

## 7.2 API 這層的定位

```text
API 不重寫 SQL
API 不修改 DB schema
API 只把余同學的 DB function 包成 HTTP endpoint
```

# 8. DB fallback 設計

因為 PostgreSQL 尚未正式部署，所以 API 必須能在 DB 還沒連上時繼續運作。

## 8.1 fallback 回傳範例

```json
{
  "db_available": false,
  "message": "versionB DB is not connected yet",
  "alerts": [],
  "total": 0
}
```

## 8.2 這樣設計的好處

| 好處 | 說明 |
|---|---|
| 主流程不會中斷 | DB 還沒建好時，TimeSeriesService 仍可跑 demo / JSON output |
| UI 可先接 API | 前端可以先對 endpoint 開發 |
| DB 完成後可直接切換 | 安裝 psycopg2 並設定 db_config.json 後即可啟用 |

# 9. 少榆 0616 B 版目前包含的模組

少榆版本不是每個功能都叫 `xxx_service`，有些是 worker、adapter 或 integrated service。

| 模組位置 | 功能 | 說明 |
|---|---|---|
| `webservices/future_service/future_service.py` | FutureService | 產生 future prediction payload |
| `webservices/monitoring_worker/monitoring_worker.py` | MonitoringWorker | 讀資料、判斷 threshold、寫 alert/status |
| `webservices/event_rule_service/event_rule_service.py` | EventRuleService | 規則判斷 |
| `webservices/troubleshooting_service/troubleshooting_service.py` | TroubleshootingService | 故障排除建議 |
| `webservices/integrated_service/sprayline_integrated_service.py` | IntegratedSprayLineService | 整合 past / current / future 查詢概念 |
| `webservices/integration_adapter/database_versionb_adapter.py` | Database adapter | 呼叫 versionB DB function |
| `rules/sensor_thresholds.json` | Rule threshold | 門檻規則 |
| `rules/sensor_event_mapping.json` | Rule mapping | sensor 與 cause / response 對應 |
| `ontology/` | Ontology | 少榆維護的本體資料 |
| `knowledge/` | Knowledge | 診斷或知識資料 |

因此少榆 B 版有內部 service 功能，但原本缺少完整對外 FastAPI API Server。

# 10. 為什麼先把 TimeSeriesService API 放進少榆 B 版

這一步的目的是先保留已經測過的 API 與 response 格式，降低整合風險。

## 10.1 放入內容

| 新增位置 | 內容 |
|---|---|
| `webservices/time_series_api/` | 放入 TimeSeriesService API 相關模組 |
| `webservices/api_server.py` | 統一 FastAPI 入口 |
| `scripts/run_api_server.py` | 啟動 API Server |
| `webservices/requirements.txt` | 補上 `fastapi`、`uvicorn` 等需求 |

## 10.2 這不是最終分工，而是保守整合

目前這樣做的優點：

| 優點 | 說明 |
|---|---|
| 原本 API 不會壞 | `/api/time-series/...` 仍可用 |
| 少榆 function 可以逐步掛接 | 不需要一次改掉全部架構 |
| DB function 可以先測 | `/api/versionb/status`、`/api/alerts` 可先使用 |

# 11. Service Orchestration Adapter


## 11.1 它負責呼叫什麼

| 被呼叫模組 | 功能 |
|---|---|
| IntegratedSprayLineService | past / current / future 整合查詢 |
| FutureService | 建立或儲存 future prediction |
| MonitoringWorker | 執行監控與告警判斷 |
| TroubleshootingService | 查詢故障排除建議 |
| DatabaseVersionBAdapter | 呼叫 PostgreSQL DB function |

## 11.2 它不做什麼

```text
不重寫 Rule
不重寫 Ontology
不重寫 SQL
不重新定義 DB schema
```

# 12. Service Orchestration API

新增 API：

| Endpoint | 功能 | 是否需要 DB |
|---|---|---|
| `GET /api/service-orchestration/status` | 檢查各模組是否可 import | 不一定 |
| `POST /api/service-orchestration/integrated/query` | 呼叫 IntegratedSprayLineService 查詢 | 視查詢來源 |
| `GET /api/service-orchestration/integrated/demo/{time_type}` | 快速 demo past/current/future | 視 demo 設計 |
| `POST /api/service-orchestration/future/payload` | 建立 future prediction payload | 不一定 |
| `POST /api/service-orchestration/future/save` | 建立並寫回 future prediction | 需要 |
| `POST /api/service-orchestration/monitoring/run` | 執行 MonitoringWorker | 需要 |
| `GET /api/service-orchestration/troubleshooting/matrix` | 查 troubleshooting matrix | 視資料來源 |
| `GET /api/service-orchestration/troubleshooting/states/{state}/recommendations` | 依狀態查建議 | 視資料來源 |

## 12.1 Future 呼叫範例

```http
POST /api/service-orchestration/future/payload
Content-Type: application/json
```

```json
{
  "batch_id": "B_20260616_001",
  "station_id": "Station_1",
  "slider_value": 30
}
```

回傳概念：

```json
{
  "success": true,
  "sample_method": "latest_valid",
  "future_prediction": {
    "station_id": "Station_1",
    "risk_level": "warning",
    "quality_score": 86.5
  }
}
```

# 13. Rule / Ontology 目前怎麼使用

這點是今天很重要的確認結果。

目前 API 沒有自己維護一份 Rule / Ontology，而是：

```text
API
  ↓
service_orchestration_adapter.py
  ↓
少榆 function
  ↓
rules / ontology / knowledge
```

## 13.1 正確說法

```text
API 是呼叫少榆 function 來使用 Rule / Ontology，
不是把 Rule 複製到我的 API 裡重新判斷。
```

## 13.2 對應關係

| 項目 | 負責來源 |
|---|---|
| Rule threshold | 少榆 `rules/sensor_thresholds.json` |
| sensor-event mapping | 少榆 `rules/sensor_event_mapping.json` |
| Ontology | 少榆 `ontology/` |
| Troubleshooting knowledge | 少榆 `knowledge/` 或 troubleshooting module |
| API endpoint | 我的 API Server |
| DB function | 余同學 versionB |

# 14. UI 呼叫 future 時，sample method 會走哪裡？

目前有兩條可能路線，取決於 UI call 哪個 API。

## 14.1 路線 A：UI call TimeSeriesService API

```text
UI
  ↓
/api/time-series/ui/summary
  ↓
TimeSeriesService
  ↓
future sample_method = latest_valid
```

這條路線是用你原本的 TimeSeriesService 來處理 future sample method。

## 14.2 路線 B：UI call Service Orchestration API

```text
UI
  ↓
/api/service-orchestration/integrated/query
  ↓
service_orchestration_adapter.py
  ↓
IntegratedSprayLineService / FutureService
  ↓
future sample_method = latest_valid
```

這條路線是由少榆的整合 function / FutureService 去處理 future。

## 14.3 建議

如果之後確認 Rule、Ontology、Future 都由少榆負責，建議 UI 的 future request 統一走：

```text
/api/service-orchestration/integrated/query
```

這樣 future 的 sample method、FutureService、Rule / Ontology / Troubleshooting 都會比較明確走少榆那條流程。

# 15. 今天架構上的結論

目前整合版可以分成兩種層級：

| 層級 | 目前狀態 |
|---|---|
| 保守可跑版 | 保留 TimeSeriesService API，確保原流程可跑 |
| 正式乾淨架構 | 未來逐步改成 API Server + Service Orchestration + 各功能模組 |

## 15.1 現在版本

```text
API Server
    ├─ TimeSeriesService API
    ├─ versionB Alert API
    └─ Service Orchestration API
```

## 15.2 未來建議版本

```text
API Server
    ↓
Service Orchestration Adapter
    ├─ Past / Current Service
    ├─ FutureService
    ├─ MonitoringWorker
    ├─ EventRuleService
    ├─ TroubleshootingService
    └─ versionB DB Adapter
```

未來比較乾淨的做法是：

| time_type | 建議負責模組 |
|---|---|
| past | 我的 Past / Current service |
| current | 我的 Past / Current service |
| future | 少榆 FutureService / IntegratedService |

# 16. 尚未完成項目與日後建議順序

## 16.1 尚未完成

| 項目 | 狀態 |
|---|---|
| PostgreSQL 正式部署 | 尚未完成 |
| `db_config.json` 正式設定 | 尚未完成 |
| DB persistence adapter | 尚未完成 |
| Past / Current service 拆分正式測試 | 放到明天 |
| 新 UI `/api/v1/lines/...` adapter | 放到明天 |
| UI future request 最終路線 | 尚未決定 |

## 16.2 日後建議順序

| 順序 | 工作 | 目的 |
|---:|---|---|
| 1 | 測 `/api/service-orchestration/status` | 確認少榆 function 掛接正常 |
| 2 | 測 `/api/versionb/status` | 確認 DB adapter 狀態 |
| 3 | 測 future payload | 確認 FutureService 可呼叫 |
| 4 | 整理 Past / Current service 拆分版 | 避免和少榆 future/rule 重疊 |
| 5 | 決定 UI future route | 統一 UI 呼叫來源 |
| 6 | 再做新 UI adapter | 對接 `/api/v1/lines/...` |

# 17. 最終結論

今日完成的是一個**整合架構整理**：

| 整合內容 | 結果 |
|---|---|
| TimeSeriesService | 保留既有 API 與 UI response 格式 |
| versionB | 新增 Alert API 對接與 DB fallback |
| 少榆 B 版 | 確認包含 Future / Monitoring / EventRule / Troubleshooting |
| Service Orchestration | 新增 API 呼叫少榆 function 的掛接層 |
| Rule / Ontology | 仍由少榆原本模組負責 |
| DB schema / function | 仍以余同學 versionB 為主 |
| 新 UI adapter | 尚未做，日後處理 |
| PostgreSQL persistence | 尚未做，等 DB 部署後處理 |

ˋ

> 本次把原本分散的 TimeSeriesService、少榆 service function、余同學 DB function 整合成 API 可呼叫的架構；目前保留既有可用流程，下一步再逐步拆分 Past / Current service、統一 future 路線，並對接新 UI 與 PostgreSQL。
