# TimeSeriesService Random Data Version

這份是隨機資料版本。

## 本版重點

原本固定讀取 `raw_data_demo.json`，所以每次算出來的數值都一樣。  
本版改成：

```text
src/random_data_provider.py
```

每次呼叫 service 都會重新隨機產生 raw data，因此輸出的 metrics 會變動。

## 資料夾結構

```text
time_series_service_random_version/
├─ src/
│  ├─ time_series_service.py
│  ├─ random_data_provider.py
│  └─ api_server.py
├─ examples/
│  ├─ request_current.json
│  ├─ request_past.json
│  ├─ request_future.json
│  ├─ time_series_output_current_demo.json
│  ├─ time_series_output_past_demo.json
│  ├─ time_series_output_future_demo.json
│  └─ processed_result_database_demo.json
├─ report/
│  ├─ time_series_service_report.ipynb
│  └─ time_series_service_report.md
├─ docs/
│  └─ RANDOM_DATA_VERSION.md
└─ README.md
```

## 執行 API

```bash
cd src
uvicorn api_server:app --reload
```

## Demo GET Endpoint

```text
http://127.0.0.1:8000/api/time-series/demo/current
http://127.0.0.1:8000/api/time-series/demo/past
http://127.0.0.1:8000/api/time-series/demo/future
```

每次重新整理頁面，都會重新產生一份 random raw data，所以數值會變。

## 正式 UI Endpoint

```text
POST /api/time-series
```

正式串接時，UI 傳入 request：

```json
{
  "schema_version": "v1.0",
  "service_name": "TimeSeriesService",
  "request_id": "req_001",
  "mode": "time",
  "window_type": "current",
  "slider_value": 0,
  "line_scope": "all",
  "requested_metrics": []
}
```

## 隨機資料來源

本版不再保留固定的 `data/raw_data_demo.json`。

隨機資料由：

```text
src/random_data_provider.py
```

產生。

正式整合 Database 時，只要把：

```python
QueryRawDataFromDatabase()
```

裡面呼叫 `BuildRandomRawDataset()` 的部分換成真正 Database 查詢即可。

## 可重現資料

如果需要讓隨機資料固定，可以在 request 裡加入：

```json
"random_seed": 42
```

如果沒有 `random_seed`，每次會產生不同資料。


## 已移除 Excel 功能

本版只保留 JSON output 與 processed result database，不再輸出 Excel。

保留：

```text
src/time_series_service.py
src/random_data_provider.py
src/api_server.py
examples/processed_result_database_demo.json
```

移除：

```text
src/excel_exporter.py
examples/time_series_latest_output.xlsx
```


## Random Time State

本版新增時間狀態隨機功能。

直接跑：

```bash
cd src
python time_series_service.py
```

會隨機輸出：

```text
past / current / future
```

也新增 API：

```text
GET /api/time-series/demo/random
```

瀏覽器測試：

```text
http://127.0.0.1:8000/api/time-series/demo/random
```

每次重新整理會隨機變成 past/current/future。

注意：  
這裡隨機的是 `viewer_state.time_type`，不是 Rule Service 的 `state`。  
`state / risk_text / fault_detail` 仍保留給 Rule Service。


## JSON 檔案輸出

本版會產生：

```text
examples/time_series_latest_output.json
examples/processed_result_database_demo.json
```

差別是：

```text
time_series_latest_output.json
    最新一次完整 output，每次執行會覆蓋更新。

processed_result_database_demo.json
    歷史紀錄，每次執行會追加一筆。
```

執行：

```bash
cd src
python time_series_service.py
```

執行後會顯示：

```text
Latest JSON output saved to: ../examples/time_series_latest_output.json
Processed result database saved to: ../examples/processed_result_database_demo.json
```
