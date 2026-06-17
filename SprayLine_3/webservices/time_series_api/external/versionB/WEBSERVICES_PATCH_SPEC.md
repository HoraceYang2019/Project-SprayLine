# WebServices 修改規格文件

**目標檔案**：`WebServices/time_series_service_v3/src/api_server.py`
**目的**：新增 Alert API 端點，串聯 `db_alert.py` 的告警 + cause + response + 停機時間 + 負責人資料
**注意**：此文件為規格說明，不直接修改 WebServices 程式碼（唯讀區域）

---

## 現有端點（保留不動）

```
GET  /                                        → 服務狀態
POST /api/time-series                         → 主查詢
POST /api/time-series/ui/summary              → 儀表板初始化
POST /api/time-series/ui/station-detail       → 站點詳細資料
POST /api/time-series/ui/component-detail     → 元件詳細資料
GET  /api/time-series/demo/{current,past,future,random}
```

---

## 新增端點規格（5 個）

### 端點 1：取得告警清單

```
GET /api/alerts
```

**Query 參數**：

| 參數 | 型別 | 預設 | 說明 |
|------|------|------|------|
| `station_id` | str | None | 指定站點，留空查全站 |
| `state` | str | None | `warning` / `fault` |
| `acknowledged` | bool | None | `true`=已確認 / `false`=未確認 |
| `days` | int | 7 | 查詢天數範圍 |
| `limit` | int | 50 | 最大回傳筆數 |

**回傳範例**：
```json
{
  "alerts": [
    {
      "event_id": "uuid-001",
      "station_id": "Station_1",
      "sensor_name": "filter_diff_pressure_bar",
      "measured_value": 0.72,
      "state": "fault",
      "ts": "2026-06-14T08:30:00+08:00",
      "message": "濾網壓差超過 fault 門檻（0.70 bar）",
      "acknowledged": false,
      "acknowledged_at": null
    }
  ],
  "total": 1
}
```

**呼叫 DB 函式**：`get_alerts_by_filters(conn, station_id, state, acknowledged, days, limit)`

---

### 端點 2：取得完整告警卡片

```
GET /api/alerts/{event_id}
```

**Path 參數**：`event_id` (str, UUID)

**回傳範例**：
```json
{
  "event_id": "uuid-001",
  "station_id": "Station_1",
  "sensor_name": "filter_diff_pressure_bar",
  "state": "fault",
  "ts": "2026-06-14T08:30:00+08:00",
  "message": "濾網壓差超過 fault 門檻",
  "acknowledged": false,
  "acknowledged_at": null,

  "causes": [
    {
      "cause_id": "FILTER_CLOG",
      "description_zh": "濾網堵塞",
      "severity": "high",
      "is_primary": true
    }
  ],

  "responses": [
    {
      "response_id": "REPLACE_FILTER",
      "description_zh": "更換濾網",
      "downtime_estimate_min": 30,
      "skill_required": "technician"
    }
  ],

  "primary_cause_zh": "濾網堵塞",
  "max_downtime_min": 30,
  "min_skill_required": "technician",
  "top_response_zh": "更換濾網"
}
```

**呼叫 DB 函式**：`get_alert_ui_card(conn, event_id)`

---

### 端點 3：確認告警

```
PATCH /api/alerts/{event_id}/acknowledge
```

**Path 參數**：`event_id` (str, UUID)

**Request Body**（可選）：
```json
{
  "acknowledged_at": "2026-06-14T09:00:00+08:00"
}
```

**回傳範例**：
```json
{
  "event_id": "uuid-001",
  "acknowledged_at": "2026-06-14T09:00:00+08:00",
  "status": "ok"
}
```

**呼叫 DB 函式**：`acknowledge_alert(conn, event_id, acknowledged_at)` + `conn.commit()`

---

### 端點 4：依原因查詢建議解方

```
GET /api/alerts/causes/{cause_id}/responses
```

**Path 參數**：`cause_id` (str)

**回傳範例**：
```json
{
  "cause_id": "FILTER_CLOG",
  "responses": [
    {
      "response_id": "REPLACE_FILTER",
      "description_zh": "更換濾網",
      "downtime_estimate_min": 30,
      "skill_required": "technician",
      "occurrence_count": 12
    },
    {
      "response_id": "BACKFLUSH_FILTER",
      "description_zh": "逆洗濾網",
      "downtime_estimate_min": 10,
      "skill_required": "operator",
      "occurrence_count": 5
    }
  ]
}
```

**呼叫 DB 函式**：`get_responses_for_cause(conn, cause_id)`

---

### 端點 5：取得站點未確認告警數量

```
GET /api/alerts/unacknowledged/{station_id}
```

**Path 參數**：`station_id` (str)

**Query 參數**：`limit` (int, 預設 50)

**回傳範例**：
```json
{
  "station_id": "Station_1",
  "count": 3,
  "alerts": [...]
}
```

**呼叫 DB 函式**：`get_unacknowledged_alerts(conn, station_id, limit)`

---

## 實作程式碼片段

以下為可插入 `api_server.py` 底部（`@app.get("/")` 之前）的完整程式碼：

```python
import sys
import os

# 將 Database/versionB 加入 Python 路徑（依實際部署路徑調整）
_DB_MODULE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../Database/versionB")
)
if _DB_MODULE_PATH not in sys.path:
    sys.path.insert(0, _DB_MODULE_PATH)

from db_connection import get_connection
from db_alert import (
    get_alerts_by_filters,
    get_alert_ui_card,
    get_responses_for_cause,
    get_unacknowledged_alerts,
    acknowledge_alert,
)


@app.get("/api/alerts")
def GetAlerts(
    station_id: str = None,
    state: str = None,
    acknowledged: bool = None,
    days: int = 7,
    limit: int = 50,
):
    conn = get_connection()
    try:
        rows = get_alerts_by_filters(
            conn, station_id=station_id, state=state,
            acknowledged=acknowledged, days=days, limit=limit,
        )
        return JSONResponse(content={"alerts": rows, "total": len(rows)})
    finally:
        conn.close()


@app.get("/api/alerts/{event_id}")
def GetAlertCard(event_id: str):
    conn = get_connection()
    try:
        card = get_alert_ui_card(conn, event_id)
        if card is None:
            return JSONResponse(status_code=404, content={"error": "alert not found"})
        return JSONResponse(content=card)
    finally:
        conn.close()


@app.patch("/api/alerts/{event_id}/acknowledge")
def AcknowledgeAlert(event_id: str, body: dict = {}):
    conn = get_connection()
    try:
        ack_at = body.get("acknowledged_at")
        acknowledge_alert(conn, event_id, ack_at)
        conn.commit()
        return JSONResponse(content={"event_id": event_id, "status": "ok"})
    except Exception as e:
        conn.rollback()
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        conn.close()


@app.get("/api/alerts/causes/{cause_id}/responses")
def GetResponsesForCause(cause_id: str):
    conn = get_connection()
    try:
        rows = get_responses_for_cause(conn, cause_id)
        return JSONResponse(content={"cause_id": cause_id, "responses": rows})
    finally:
        conn.close()


@app.get("/api/alerts/unacknowledged/{station_id}")
def GetUnacknowledgedAlerts(station_id: str, limit: int = 50):
    conn = get_connection()
    try:
        rows = get_unacknowledged_alerts(conn, station_id=station_id, limit=limit)
        return JSONResponse(content={
            "station_id": station_id,
            "count": len(rows),
            "alerts": rows,
        })
    finally:
        conn.close()
```

---

## HealthCheck 端點更新

將現有 `HealthCheck()` 回傳中的 endpoint 清單補充：

```python
"alert_endpoints": [
    "GET /api/alerts",
    "GET /api/alerts/{event_id}",
    "PATCH /api/alerts/{event_id}/acknowledge",
    "GET /api/alerts/causes/{cause_id}/responses",
    "GET /api/alerts/unacknowledged/{station_id}"
]
```

---

## 依賴說明

- **DB 連線**：透過環境變數 `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` 設定
- **序列化注意**：`datetime` 物件需轉為 ISO 字串，`json.dumps(default=str)` 或 FastAPI 的 `jsonable_encoder` 皆可處理
- **UUID 序列化**：`event_id` 從 DB 取回為 `uuid.UUID` 型別，需 `str(event_id)` 轉換（`db_alert.py` 的 `insert_alert_event` 已處理）
