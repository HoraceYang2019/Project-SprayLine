# 0617ver_1 UI API 對照表

## 統一 API 入口

```text
webservices/api_server.py
```

啟動：

```powershell
python scripts
un_api_server.py
```

或：

```powershell
uvicorn webservices.api_server:app --host 0.0.0.0 --port 8001 --reload
```

API 文件：

```text
http://127.0.0.1:8001/docs
```

## 兩條線定位

| 線 | 用途 | 主要 API | 是否寫 DB |
|---|---|---|---|
| TimeSeries UI 線 | UI 查 past/current/future、畫趨勢、站點卡片 | `/api/time-series`, `/api/time-series/ui/*` | 預設不寫 DB |
| Service Orchestration 線 | 少榆正式 service、future/alert/status/troubleshooting、DB 回寫 | `/api/service-orchestration/*` | 指定 save/run 才寫 DB |

## UI 建議優先使用

### 首頁 dashboard / station cards

```text
POST /api/time-series/ui/summary
```

範例 request：

```json
{
  "slider_value": 0,
  "line_scope": "all"
}
```

### 某一站詳細資料

```text
POST /api/time-series/ui/station-detail
```

範例 request：

```json
{
  "slider_value": 0,
  "line_id": "line_1"
}
```

### 元件詳細資料

```text
POST /api/time-series/ui/component-detail
```

範例 request：

```json
{
  "slider_value": 0,
  "line_id": "line_1",
  "component_name": "nozzle"
}
```

## 少榆正式 service API

### 查 integrated service，不寫 DB

```text
POST /api/service-orchestration/integrated/query
```

範例 request：

```json
{
  "slider_value": 0,
  "station_scope": "Station_1",
  "window_minutes": 30
}
```

### 執行一次 integrated service 並寫回 DB

```text
POST /api/service-orchestration/integrated/run-once
```

### 寫入 future_prediction_result

```text
POST /api/service-orchestration/future/save
```

### 觸發 MonitoringWorker 寫入 alert_event / batch_station_status

```text
POST /api/service-orchestration/monitoring/run
```

## 重要規則

UI 拖 slider 時請使用 `/api/time-series` 或 `/api/time-series/ui/*`，預設不寫 DB。  
只有 `/api/service-orchestration/*/save` 或 `/run` 類 API 才應該做 DB write-back。
