# 0617ver_1 API 整合檢查報告

## 本版處理

1. 以 `少榆0616_B版` 為基礎建立 `少榆0617ver_1`。
2. 合入 past/current 同學的 FastAPI 架構。
3. 新增統一 API 入口：`webservices/api_server.py`。
4. 將 TimeSeries UI 線改成優先呼叫 `IntegratedSprayLineService`，DB 不可用時才 fallback demo。
5. 保留 Service Orchestration 線，負責少榆 Future / Monitoring / Troubleshooting / DB 回寫。
6. 修正 versionB loader 優先順序，避免優先吃到 time_series_api packaged fallback。
7. 新增 `scripts/run_api_smoke_test.py`，可檢查 UI API 是否仍可回應。
8. 僅處理 SprayLine / 噴塗線，未加入老師給的其他範例。

## 需要老師或 DB 環境確認

1. PostgreSQL 實際連線。
2. DataPreprocess 實際寫入 `sensor_1min / sensor_3min` 後，API 是否可查到正式資料。
3. `/api/service-orchestration/*` 寫回 `alert_event / batch_station_status / future_prediction_result` 的端到端結果。

## UI API 檢查方式

啟動 API：

```powershell
python scripts\run_api_server.py
```

另開 PowerShell：

```powershell
python scripts\run_api_smoke_test.py --base-url http://127.0.0.1:8001
```

預期：

```text
GET / -> 200
GET /api/routes -> 200
POST /api/time-series -> 200
POST /api/time-series/ui/summary -> 200
POST /api/time-series/ui/station-detail -> 200
POST /api/time-series/ui/component-detail -> 200
POST /api/service-orchestration/integrated/query -> 200
```

## 自動檢查結果

- Python 檔案數：56
- Python syntax errors：0
- JSON 檔案數：72
- JSON parse errors：0
- 其他範例關鍵字命中：0

### API TestClient 檢查

- `GET /`：HTTP 200
- `GET /api/routes`：HTTP 200
- `GET /api/versionb/status`：HTTP 200
- `GET /api/service-orchestration/status`：HTTP 200
- `POST /api/time-series`：HTTP 200
- `POST /api/time-series/ui/summary`：HTTP 200
- `POST /api/time-series/ui/station-detail`：HTTP 200
- `POST /api/time-series/ui/component-detail`：HTTP 200
- `POST /api/service-orchestration/integrated/query`：HTTP 200
