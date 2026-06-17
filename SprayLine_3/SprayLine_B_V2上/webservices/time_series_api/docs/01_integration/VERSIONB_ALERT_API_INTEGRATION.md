# versionB Alert API 對接層整合說明

## 1. 本次整合目標

本次目標不是直接把 TimeSeriesService 的資料寫入 PostgreSQL，而是先建立與 `versionB` 的 API 對接層，讓目前 D 方案可以保留原本可執行的 JSON runtime output，同時預留與 DB 查詢函式的串接介面。

整合後架構如下：

```text
UI / WebServices
    ↓
TimeSeriesService D 版 api_server.py
    ↓
versionB Alert API endpoints
    ↓
versionb_alert_adapter.py
    ↓
external/versionB/db_alert.py
    ↓
PostgreSQL sprayline database
```

## 2. 本次新增檔案

```text
src/versionb_loader.py
src/versionb_alert_adapter.py
src/db_config.example.json
external/versionB/
docs/01_integration/VERSIONB_ALERT_API_INTEGRATION.md
report/time_series_service_v3_versionB_today_report.md
report/time_series_service_v3_versionB_today_report.ipynb
```

## 3. versionB 模組載入方式

`versionb_loader.py` 會依序尋找以下路徑：

```text
VERSIONB_PATH 環境變數
package/external/versionB
專案根目錄/versionB
專案根目錄/Database/versionB
目前工作目錄/versionB
```

找到 `db_connection.py` 與 `db_alert.py` 後，會嘗試匯入 versionB 的 DB 查詢函式。

如果尚未安裝 `psycopg2` 或 DB 尚未設定，API 不會讓 service 掛掉，而是回傳：

```json
{
  "db_available": false,
  "message": "versionB DB is not connected yet"
}
```

## 4. 新增 Alert API

本次新增五個 versionB 規格端點：

```text
GET   /api/alerts
GET   /api/alerts/{event_id}
PATCH /api/alerts/{event_id}/acknowledge
GET   /api/alerts/causes/{cause_id}/responses
GET   /api/alerts/unacknowledged/{station_id}
```

另新增狀態檢查端點：

```text
GET /api/versionb/status
```

## 5. 對應 versionB DB 函式

| API | versionB 函式 |
|---|---|
| `GET /api/alerts` | `get_alerts_by_filters()` |
| `GET /api/alerts/{event_id}` | `get_alert_ui_card()` |
| `PATCH /api/alerts/{event_id}/acknowledge` | `acknowledge_alert()` |
| `GET /api/alerts/causes/{cause_id}/responses` | `get_responses_for_cause()` |
| `GET /api/alerts/unacknowledged/{station_id}` | `get_unacknowledged_alerts()` |

## 6. DB 尚未完整時的處理方式

目前 PostgreSQL schema 尚在確認，因此本次採用安全做法：

```text
D 方案原本功能繼續使用 JSON runtime output
versionB API 端點先完成介面與模組載入
若 DB 未連線，API 回傳 db_available=false
若 DB 完整，API 會直接呼叫 versionB db_alert.py 查詢 PostgreSQL
```

這樣 UI 可以先接 API 規格，不會因 DB 尚未完成而影響 TimeSeriesService 主流程。

## 7. DB 啟用條件

若要啟用正式 PostgreSQL 查詢，需要：

```text
1. 安裝 psycopg2 或 psycopg2-binary
2. 建立 sprayline database
3. 執行 versionB/setup_db.sql
4. 確認 data_quality_flag migration 是否已執行
5. 設定 DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME
   或複製 src/db_config.example.json 成 src/db_config.json
```

## 8. 本次整合決策

本次先做 API 對接層，不直接把 D output 寫入 DB，也不把 random data 改成從 sensor_1min / sensor_3min 讀取。

原因：

```text
1. DB schema 還需要確認 future_prediction_result 表
2. sensor_threshold 要決定使用 JSON 還是 DB table
3. sensor_3min 寫入流程尚需確認
4. normal / ok 狀態命名需要統一
5. troubleshooting cause_id / response_id 對照需確認
```

因此正式 DB persistence 會放在下一階段透過 `db_persistence_adapter.py` 實作。
