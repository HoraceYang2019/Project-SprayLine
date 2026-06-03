# TimeSeriesService 最終版本報告整理

## 版本定位

這份是目前最後確認的 **TimeSeriesService 隨機資料 + 隨機時間狀態 + JSON 檔案輸出版本**。

本版主要特色：

```text
1. 不使用固定 raw_data_demo.json
2. raw data 由 random_data_provider.py 隨機產生
3. 直接執行 time_series_service.py 時，時間狀態會隨機 past/current/future
4. API 提供固定 demo endpoint 與 random demo endpoint
5. 每次執行會輸出最新 JSON 檔
6. 每次執行會追加 processed result database
7. 不輸出 Excel
8. Rule 判斷仍不在本 service 裡
```

---

# 1. 我要 call 什麼 function？

## 1.1 最主要要 call 的 function

正式流程中，UI 或 Integration Service 最主要要 call：

```python
HandleTimeSeriesQuery(request)
```

這是 `TimeSeriesService` 的主入口 function。

它接收一個 `request`，然後回傳完整 output JSON。

---

## 1.2 如果用 API 呼叫

API 檔案：

```text
src/api_server.py
```

正式 API endpoint：

```text
POST /api/time-series
```

對應 function：

```python
HandleTimeSeriesRequest(request)
```

它內部會呼叫：

```python
service.HandleTimeSeriesQuery(request)
```

所以 API 流程是：

```text
POST /api/time-series
        ↓
HandleTimeSeriesRequest(request)
        ↓
TimeSeriesService.HandleTimeSeriesQuery(request)
        ↓
return output JSON
```

---

## 1.3 Demo 用 endpoint

為了測試方便，這版也有 demo endpoint：

```text
GET /api/time-series/demo/current
GET /api/time-series/demo/past
GET /api/time-series/demo/future
GET /api/time-series/demo/random
```

對應 function：

```python
DemoCurrent()
DemoPast()
DemoFuture()
DemoRandom()
```

這些 function 會先呼叫：

```python
BuildDemoRequest(time_type)
```

建立 demo request，再呼叫：

```python
service.HandleTimeSeriesQuery(request)
```

---

## 1.4 直接執行 Python 檔案時

直接跑：

```bash
cd src
python time_series_service.py
```

會使用：

```python
BuildRandomTimeSeriesRequest()
```

建立隨機時間狀態 request，然後呼叫：

```python
HandleTimeSeriesQuery(request)
```

所以直接執行流程是：

```text
python time_series_service.py
        ↓
BuildRandomTimeSeriesRequest()
        ↓
HandleTimeSeriesQuery(request)
        ↓
print output JSON
        ↓
SaveProcessedResultToDatabase()
        ↓
SaveLatestOutputJson()
```

---

## 1.5 主要 function 呼叫順序

完整 function 流程：

```text
HandleTimeSeriesQuery(request)
    ↓
ValidateRequest(request)
    ↓
DetermineTimeType(request)
    ↓
GetSampleMethod(time_type)
    ↓
QueryRawDataFromDatabase(request, time_type)
    ↓
BuildRandomRawDataset(time_type, sample_count, seed)
    ↓
ResolveLineScope(request)
    ↓
ApplySampleMethods(raw_line_data, sample_method)
    ↓
ApplySampleMethod(values, method)
    ↓
CalculateLineMetrics(sampled_data)
    ↓
CalculateNozzleMetrics(parameters)
CalculateFilterMetrics(parameters)
CalculateSprayWidthMetrics(parameters)
    ↓
BuildLineOutput(line, calculated_data)
    ↓
BuildOutput(request, time_type, raw_dataset_metadata, stations)
    ↓
SaveProcessedResultToDatabase(output)
    ↓
SaveLatestOutputJson(output)
    ↓
return output
```

---

## 1.6 Function 名稱總表

| Function 名稱 | 位置 | 功能 |
|---|---|---|
| `HandleTimeSeriesQuery()` | `time_series_service.py` | 主入口，接收 request，回傳 output |
| `ValidateRequest()` | `time_series_service.py` | 檢查 request 必要欄位 |
| `DetermineTimeType()` | `time_series_service.py` | 由 `slider_value` 判斷 past/current/future |
| `ResolveLineScope()` | `time_series_service.py` | 根據 `line_scope` 決定處理哪些 line |
| `QueryRawDataFromDatabase()` | `time_series_service.py` | Prototype 階段呼叫隨機資料產生器；正式版可改接 Database |
| `BuildRandomRawDataset()` | `random_data_provider.py` | 產生隨機 raw data |
| `BuildLineRawData()` | `random_data_provider.py` | 產生單一 line 的 raw data |
| `BuildRandomSeries()` | `random_data_provider.py` | 產生隨機數值序列 |
| `BuildRandomBoolSeries()` | `random_data_provider.py` | 產生隨機布林序列 |
| `GetSampleMethod()` | `time_series_service.py` | 根據 time_type 選 sample method |
| `ApplySampleMethods()` | `time_series_service.py` | 對一條 line 的 raw data 套用 sample method |
| `ApplySampleMethod()` | `time_series_service.py` | 對單一欄位取平均、最新值、計數等 |
| `CalculateNozzleMetrics()` | `time_series_service.py` | 計算噴嘴指標 |
| `CalculateFilterMetrics()` | `time_series_service.py` | 計算濾網指標 |
| `CalculateSprayWidthMetrics()` | `time_series_service.py` | 計算噴幅指標 |
| `CalculateLineMetrics()` | `time_series_service.py` | 整合 line-level metrics |
| `BuildLineOutput()` | `time_series_service.py` | 建立單一 station output |
| `BuildOutput()` | `time_series_service.py` | 建立完整 service output |
| `SaveProcessedResultToDatabase()` | `time_series_service.py` | 追加 processed result database |
| `SaveLatestOutputJson()` | `time_series_service.py` | 輸出最新一次完整 JSON |
| `BuildTimeSeriesRequestTemplate()` | `time_series_service.py` | 建立 request template |
| `BuildRandomTimeSeriesRequest()` | `time_series_service.py` | 直接執行時建立隨機時間 request |
| `HandleTimeSeriesRequest()` | `api_server.py` | 正式 API POST 入口 |
| `BuildDemoRequest()` | `api_server.py` | 建立 demo request |
| `DemoCurrent()` | `api_server.py` | 固定 current demo |
| `DemoPast()` | `api_server.py` | 固定 past demo |
| `DemoFuture()` | `api_server.py` | 固定 future demo |
| `DemoRandom()` | `api_server.py` | 隨機 past/current/future demo |

---

# 2. 我要收到什麼資料？

TimeSeriesService 主要會收到兩類資料：

```text
1. UI / Integration Service 傳入的 request
2. QueryRawDataFromDatabase() 取得的 raw dataset
```

目前 prototype 的 raw dataset 是由 `random_data_provider.py` 隨機產生；正式整合時可以把 `QueryRawDataFromDatabase()` 改成真正 Database 查詢。

---

## 2.1 Request 欄位名稱

Service 接收的 request 格式：

```json
{
  "schema_version": "v1.0",
  "service_name": "TimeSeriesService",
  "request_id": "req_001",
  "mode": "time",
  "window_type": "current",
  "slider_value": 0,
  "line_scope": "all",
  "requested_metrics": [
    "availability_pct",
    "clog_rate_pct",
    "pressure_bar",
    "flow_rate_ml_min",
    "maintainability_pct",
    "quality_score_pct",
    "risk_text",
    "spray_width_mm",
    "recipe_name",
    "temperature_c",
    "utilization_pct",
    "cycle_time_sec"
  ]
}
```

---

## 2.2 Request 必要欄位

`ValidateRequest()` 會檢查這些必要欄位：

| 欄位名稱 | 說明 |
|---|---|
| `schema_version` | schema 版本 |
| `service_name` | service 名稱，必須是 `TimeSeriesService` |
| `mode` | 查詢模式，目前是 `time` |
| `window_type` | 時間視窗，例如 `current`、`2hour` |
| `slider_value` | UI 時間軸數值，用來判斷 past/current/future |
| `line_scope` | 查詢範圍，例如 `all`、`line_1` |

如果缺少 `slider_value`，service 會報錯，不會自動變成 current。

---

## 2.3 Request 可選欄位

| 欄位名稱 | 說明 |
|---|---|
| `request_id` | request 編號，可為 `None` |
| `requested_metrics` | UI 想看的指標列表 |
| `random_seed` | 可選；指定後隨機資料可重現 |
| `sample_count` | 可選；指定每個欄位要產生幾筆 raw data |

---

## 2.4 `slider_value` 對時間狀態的意義

```text
slider_value < 0  → past
slider_value = 0  → current
slider_value > 0  → future
```

這個判斷由：

```python
DetermineTimeType(request)
```

負責。

---

## 2.5 直接執行時的隨機 request

直接執行 `time_series_service.py` 時會呼叫：

```python
BuildRandomTimeSeriesRequest()
```

它會隨機產生：

```text
past    → slider_value = -1 ~ -5
current → slider_value = 0
future  → slider_value = 1 ~ 5
```

所以直接跑程式時，不會每次都固定 current。

---

## 2.6 Raw dataset 最外層欄位

`QueryRawDataFromDatabase()` 目前會回傳：

```json
{
  "line_1": {},
  "line_2": {},
  "line_3": {},
  "_metadata": {}
}
```

| 欄位名稱 | 說明 |
|---|---|
| `line_1` | 底漆站 raw data |
| `line_2` | 面漆站 raw data |
| `line_3` | 金漆站 raw data |
| `_metadata` | 隨機資料產生資訊 |

---

## 2.7 `_metadata` 欄位

```json
{
  "generated_at": "...",
  "data_type": "random_raw_data",
  "time_type": "current",
  "sample_count": 8,
  "seed": null
}
```

| 欄位名稱 | 說明 |
|---|---|
| `generated_at` | raw data 產生時間 |
| `data_type` | 資料型態，目前是 `random_raw_data` |
| `time_type` | 本次資料對應的 past/current/future |
| `sample_count` | 每個欄位產生幾筆資料 |
| `seed` | random seed，若無指定則為 `null` |

---

## 2.8 每條 line 收到的 raw data 名稱

每條 line 的 raw data 會放在：

```text
line_id.raw_parameters
```

例如：

```json
{
  "line_1": {
    "raw_parameters": {
      "pressure_bar": [],
      "flow_rate_ml_min": [],
      "nominal_flow_rate_ml_min": [],
      "spray_width_mm": [],
      "target_spray_width_mm": [],
      "target_min_mm": [],
      "target_max_mm": [],
      "in_flow_ml_min": [],
      "out_flow_ml_min": [],
      "nozzle_usage_time_hr": [],
      "nozzle_rul_hr": [],
      "filter_usage_time_hr": [],
      "filter_rul_hr": [],
      "temperature_c": [],
      "recipe_name": [],
      "running_time_sec": [],
      "total_window_time_sec": [],
      "available_time_sec": [],
      "planned_time_sec": [],
      "part_start_time": [],
      "part_end_time": [],
      "ok_count": [],
      "total_count": [],
      "defect": []
    }
  }
}
```

---

## 2.9 Raw data 名稱說明

### Nozzle

| Raw data 名稱 | 中文說明 |
|---|---|
| `pressure_bar` | 噴塗壓力 |
| `flow_rate_ml_min` | 實際噴塗流量 |
| `nominal_flow_rate_ml_min` | 額定流量 |
| `nozzle_usage_time_hr` | 噴嘴已使用時間 |
| `nozzle_rul_hr` | 噴嘴剩餘壽命 |

### Filter Mesh

| Raw data 名稱 | 中文說明 |
|---|---|
| `in_flow_ml_min` | 濾網入口流量 |
| `out_flow_ml_min` | 濾網出口流量 |
| `filter_usage_time_hr` | 濾網已使用時間 |
| `filter_rul_hr` | 濾網剩餘壽命 |

### Spray Width

| Raw data 名稱 | 中文說明 |
|---|---|
| `spray_width_mm` | 實際噴幅 |
| `target_spray_width_mm` | 目標噴幅 |
| `target_min_mm` | 噴幅下限 |
| `target_max_mm` | 噴幅上限 |

### Process / Quality

| Raw data 名稱 | 中文說明 |
|---|---|
| `temperature_c` | 溫度 |
| `recipe_name` | 配方名稱 |
| `running_time_sec` | 運轉時間 |
| `total_window_time_sec` | 視窗總時間 |
| `available_time_sec` | 可用時間 |
| `planned_time_sec` | 計畫時間 |
| `part_start_time` | 工件開始時間 |
| `part_end_time` | 工件結束時間 |
| `ok_count` | 合格數 |
| `total_count` | 總數 |
| `defect` | 缺陷事件布林值 |

---

# 3. 我要怎麼做計算？

整體計算分成五個階段：

```text
1. 判斷時間狀態
2. 產生或取得 raw data
3. 套用 sample_method
4. 計算 component metrics
5. 整合 line-level metrics
```

---

## 3.1 判斷時間狀態

Function：

```python
DetermineTimeType(request)
```

判斷方法：

```text
if slider_value < 0:
    time_type = "past"
elif slider_value == 0:
    time_type = "current"
else:
    time_type = "future"
```

---

## 3.2 隨機 raw data 產生方式

Function：

```python
BuildRandomRawDataset(time_type, sample_count, seed)
```

預設 sample_count：

| time_type | sample_count |
|---|---:|
| `past` | 20 |
| `current` | 8 |
| `future` | 5 |

如果 request 有傳：

```json
"sample_count": 10
```

就會使用 request 指定的值。

如果 request 有傳：

```json
"random_seed": 42
```

就可以重現同一組隨機資料。

---

## 3.3 Sample method 選擇

Function：

```python
GetSampleMethod(time_type)
```

| time_type | 數值型資料使用方法 |
|---|---|
| `past` | `mean` |
| `current` | `recent_average` |
| `future` | `latest_valid` |

---

## 3.4 Sample method 算法

Function：

```python
ApplySampleMethod(values, method, recent_n=5)
```

| method | 中文 | 算法 |
|---|---|---|
| `mean` | 平均值 | 所有有效數值相加 / 數量 |
| `recent_average` | 最近 N 筆平均 | 取最近 `recent_n=5` 筆有效數值平均 |
| `latest_valid` | 最新有效值 | 取最後一筆非空值 |
| `count` | 計數 | 若是布林值，計算 `True` 次數；否則計算有效資料筆數 |
| `majority` | 多數決 | 取出現最多的值 |
| `max` | 最大值 | 取最大數值 |
| `min` | 最小值 | 取最小數值 |

---

## 3.5 各欄位使用的 sample method

大部分數值欄位會依照 time_type 改變：

```text
past    → mean
current → recent_average
future  → latest_valid
```

這些欄位包含：

```text
pressure_bar
flow_rate_ml_min
spray_width_mm
in_flow_ml_min
out_flow_ml_min
temperature_c
```

固定使用 `latest_valid` 的欄位：

```text
nominal_flow_rate_ml_min
target_spray_width_mm
target_min_mm
target_max_mm
nozzle_usage_time_hr
nozzle_rul_hr
filter_usage_time_hr
filter_rul_hr
recipe_name
running_time_sec
total_window_time_sec
available_time_sec
planned_time_sec
part_start_time
part_end_time
ok_count
total_count
```

`defect` 使用：

```text
count
```

---

## 3.6 Nozzle 計算

Function：

```python
CalculateNozzleMetrics(parameters)
```

### 輸入

```text
pressure_bar
flow_rate_ml_min
nominal_flow_rate_ml_min
nozzle_usage_time_hr
nozzle_rul_hr
```

### 輸出

```text
pressure_bar
flow_rate_ml_min
nozzle_clog_rate_pct
nozzle_maintainability_pct
```

### 噴嘴堵塞率

Function：

```python
CalculateClogRateFromNominalFlow(actual_flow_rate, nominal_flow_rate)
```

公式：

```text
nozzle_clog_rate_pct =
max(0, (nominal_flow_rate_ml_min - flow_rate_ml_min)
        / nominal_flow_rate_ml_min * 100)
```

### 噴嘴維護性

Function：

```python
CalculateMaintainabilityPct(rul_hr, usage_time_hr)
```

公式：

```text
nozzle_maintainability_pct =
nozzle_rul_hr / (nozzle_rul_hr + nozzle_usage_time_hr) * 100
```

---

## 3.7 Filter Mesh 計算

Function：

```python
CalculateFilterMetrics(parameters)
```

### 輸入

```text
in_flow_ml_min
out_flow_ml_min
filter_usage_time_hr
filter_rul_hr
```

### 輸出

```text
flow_loss_pct
filter_clog_rate_pct
filter_maintainability_pct
```

### 流量損失率

Function：

```python
CalculateFlowLossPct(in_flow_ml_min, out_flow_ml_min)
```

公式：

```text
flow_loss_pct =
max(0, (in_flow_ml_min - out_flow_ml_min)
        / in_flow_ml_min * 100)
```

### 濾網堵塞率

公式：

```text
filter_clog_rate_pct = flow_loss_pct
```

### 濾網維護性

公式：

```text
filter_maintainability_pct =
filter_rul_hr / (filter_rul_hr + filter_usage_time_hr) * 100
```

---

## 3.8 Spray Width 計算

Function：

```python
CalculateSprayWidthMetrics(parameters)
```

### 輸入

```text
spray_width_mm
target_spray_width_mm
target_min_mm
target_max_mm
```

### 輸出

```text
spray_width_mm
width_error_mm
width_error_pct
coverage_score_pct
target_min_mm
target_max_mm
```

### 噴幅誤差

```text
width_error_mm =
spray_width_mm - target_spray_width_mm
```

### 噴幅誤差百分比

```text
width_error_pct =
abs(spray_width_mm - target_spray_width_mm)
 / target_spray_width_mm * 100
```

### 覆蓋分數

```text
coverage_score_pct =
max(0, 100 - width_error_pct)
```

---

## 3.9 Line-level metrics 計算

Function：

```python
CalculateLineMetrics(sampled_data)
```

### 總堵塞率

Function：

```python
CalculateLineClogRate(nozzle_clog_rate_pct, filter_clog_rate_pct)
```

公式：

```text
clog_rate_pct =
max(nozzle_clog_rate_pct, filter_clog_rate_pct)
```

### 總維護性

Function：

```python
CalculateLineMaintainability(nozzle_maintainability_pct, filter_maintainability_pct)
```

公式：

```text
maintainability_pct =
min(nozzle_maintainability_pct, filter_maintainability_pct)
```

### 品質分數

Function：

```python
CalculateQualityScorePct(coverage_score_pct, ok_count, total_count, defect_count)
```

優先公式：

```text
quality_score_pct =
ok_count / total_count * 100
```

若沒有 `ok_count` / `total_count`，才使用：

```text
quality_score_pct = coverage_score_pct
```

若只有 defect_count 且 defect_count > 0，回傳：

```text
quality_score_pct = 0
```

### 稼動率

Function：

```python
CalculateUtilizationPct(running_time_sec, total_window_time_sec)
```

公式：

```text
utilization_pct =
running_time_sec / total_window_time_sec * 100
```

### 可用率

Function：

```python
CalculateAvailabilityPct(available_time_sec, planned_time_sec)
```

公式：

```text
availability_pct =
available_time_sec / planned_time_sec * 100
```

### 週期時間

Function：

```python
CalculateCycleTimeSec(part_start_time, part_end_time)
```

公式：

```text
cycle_time_sec =
part_end_time - part_start_time
```

---

# 4. 計算完之後要輸出什麼？

本版會輸出四種形式：

```text
1. terminal print 的 output JSON
2. API response JSON
3. examples/time_series_latest_output.json
4. examples/processed_result_database_demo.json
```

---

## 4.1 最新一次完整 output JSON

檔案名稱：

```text
examples/time_series_latest_output.json
```

產生 function：

```python
SaveLatestOutputJson(output)
```

特性：

```text
每次執行會覆蓋更新
只保留最新一次完整 output
方便直接打開查看結果
```

---

## 4.2 Processed result database

檔案名稱：

```text
examples/processed_result_database_demo.json
```

產生 function：

```python
SaveProcessedResultToDatabase(output)
```

特性：

```text
每次執行會追加一筆
用 JSON array 模擬 processed result database
保存歷史紀錄
```

---

## 4.3 Output 最外層欄位名稱

完整 output 會包含：

```json
{
  "schema_version": "v1.0",
  "generated_at": "...",
  "service_name": "TimeSeriesService",
  "request_id": "...",
  "viewer_state": {},
  "summary": {},
  "stations": [],
  "calculation_info": {},
  "database_info": {}
}
```

---

## 4.4 `viewer_state` 輸出欄位

```json
{
  "mode": "time",
  "window_type": "current",
  "slider_value": 0,
  "display_label": "current",
  "time_type": "current",
  "is_history": false,
  "is_current": true,
  "is_future": false
}
```

| 欄位名稱 | 說明 |
|---|---|
| `mode` | 查詢模式 |
| `window_type` | 時間視窗 |
| `slider_value` | UI 時間軸數值 |
| `display_label` | 顯示用文字 |
| `time_type` | `past/current/future` |
| `is_history` | 是否為過去 |
| `is_current` | 是否為現在 |
| `is_future` | 是否為未來 |

---

## 4.5 `summary` 輸出欄位

```json
{
  "total_station_count": 3,
  "normal_count": null,
  "warning_count": null,
  "predict_risk_count": null
}
```

注意：

```text
normal_count
warning_count
predict_risk_count
```

這些需要 Rule Service 判斷後才會填入，所以目前為 `null`。

---

## 4.6 `stations[]` 輸出欄位

每一條 line 會輸出一筆 station：

```json
{
  "line_id": "line_1",
  "station_name_zh": "底漆站",
  "station_name_en": "Primer Station",
  "state": null,
  "component_overview": [],
  "metrics": {},
  "process_parameters": {},
  "component_metrics": {},
  "fault_detail": [],
  "spray_width_image": {}
}
```

---

## 4.7 `metrics` 輸出欄位

```json
{
  "availability_pct": null,
  "clog_rate_pct": null,
  "pressure_bar": null,
  "flow_rate_ml_min": null,
  "maintainability_pct": null,
  "quality_score_pct": null,
  "risk_text": null,
  "spray_width_mm": null
}
```

| 欄位名稱 | 說明 |
|---|---|
| `availability_pct` | 可用率 |
| `clog_rate_pct` | 總堵塞率 |
| `pressure_bar` | 噴塗壓力 |
| `flow_rate_ml_min` | 噴塗流量 |
| `maintainability_pct` | 總維護性 |
| `quality_score_pct` | 品質分數 |
| `risk_text` | 風險文字，由 Rule Service 補 |
| `spray_width_mm` | 噴幅 |

---

## 4.8 `process_parameters` 輸出欄位

```json
{
  "recipe_name": null,
  "temperature_c": null,
  "utilization_pct": null,
  "cycle_time_sec": null
}
```

| 欄位名稱 | 說明 |
|---|---|
| `recipe_name` | 配方名稱 |
| `temperature_c` | 溫度 |
| `utilization_pct` | 稼動率 |
| `cycle_time_sec` | 週期時間 |

---

## 4.9 `component_metrics` 輸出欄位

```json
{
  "nozzle": {
    "pressure_bar": null,
    "flow_rate_ml_min": null,
    "nozzle_clog_rate_pct": null,
    "nozzle_maintainability_pct": null
  },
  "filter_mesh": {
    "flow_loss_pct": null,
    "filter_clog_rate_pct": null,
    "filter_maintainability_pct": null
  },
  "spray_width": {
    "spray_width_mm": null,
    "width_error_mm": null,
    "width_error_pct": null,
    "coverage_score_pct": null,
    "target_min_mm": null,
    "target_max_mm": null
  }
}
```

---

## 4.10 `spray_width_image` 輸出欄位

```json
{
  "spray_width_mm": null,
  "target_min_mm": null,
  "target_max_mm": null,
  "status": null,
  "image_ref": null,
  "note": null
}
```

注意：

```text
status
image_ref
note
```

目前不由 TimeSeriesService 判斷，保留給後續 Rule Service 或 Vision Service。

---

## 4.11 `calculation_info` 輸出欄位

```json
{
  "pipeline": [],
  "raw_dataset_metadata": {},
  "rule_stage": "external",
  "note": "..."
}
```

其中 `pipeline` 會記錄本次計算流程：

```text
HandleTimeSeriesQuery
ValidateRequest
DetermineTimeType
QueryRawDataFromDatabase
ApplySampleMethods
CalculateLineMetrics
BuildOutput
SaveProcessedResultToDatabase
```

`raw_dataset_metadata` 會記錄 random raw data 的產生資訊。

---

## 4.12 `database_info` 輸出欄位

```json
{
  "save_processed_result": true,
  "save_target": "../examples/processed_result_database_demo.json",
  "saved_at": "...",
  "data_type": "processed_result",
  "note": "...",
  "latest_output_json_path": "../examples/time_series_latest_output.json"
}
```

---

# 5. 這次做了什麼更新？

## 5.1 從固定資料改成隨機 raw data

原本固定讀：

```text
raw_data_demo.json
```

所以每次 metrics 都一樣。

現在改成：

```text
src/random_data_provider.py
```

每次呼叫都會重新產生 raw data。

---

## 5.2 新增隨機時間狀態

原本直接執行 `time_series_service.py` 會固定使用：

```json
"slider_value": 0
```

所以每次都是 current。

現在改成：

```python
BuildRandomTimeSeriesRequest()
```

直接執行時會隨機：

```text
past / current / future
```

---

## 5.3 新增 random demo endpoint

新增 API：

```text
GET /api/time-series/demo/random
```

每次重新整理會隨機取得：

```text
past / current / future
```

固定 endpoint 仍保留：

```text
GET /api/time-series/demo/current
GET /api/time-series/demo/past
GET /api/time-series/demo/future
```

---

## 5.4 新增最新 output JSON 檔

新增輸出：

```text
examples/time_series_latest_output.json
```

每次執行會覆蓋更新，方便直接查看最新一次完整 output。

---

## 5.5 保留 processed result database

保留：

```text
examples/processed_result_database_demo.json
```

每次執行會追加一筆，模擬 processed result database。

---

## 5.6 移除 Excel 功能

目前版本已移除：

```text
excel_exporter.py
time_series_latest_output.xlsx
```

只保留 JSON 輸出。

---

## 5.7 Rule 仍不在本 service

這版沒有隨機產生 Rule 狀態：

```text
state
risk_text
fault_detail
component_overview
normal_count
warning_count
predict_risk_count
```

原因是前面已經確認 Rule 不由這個 service 負責。  
這些欄位仍保留為：

```text
null 或 []
```

交給後續 Rule Service / Rule Engine 補上。

---

# 報告時可以這樣講

這次 TimeSeriesService 的設計是讓 UI 或 Integration Service 傳入 request，主要入口是 `HandleTimeSeriesQuery(request)`。Service 會先驗證 request，再用 `slider_value` 判斷時間狀態是 past、current 還是 future。接著透過 `QueryRawDataFromDatabase()` 取得 raw data；目前 prototype 階段是由 `random_data_provider.py` 隨機產生資料，正式整合時只要把這個 function 改成真正 Database 查詢即可。

計算時會根據時間狀態選擇 sample method：past 使用 mean，current 使用 recent_average，future 使用 latest_valid。接著分別計算 nozzle、filter mesh、spray width 的 component metrics，再整合成 line-level metrics，例如 availability、clog rate、maintainability、quality score、utilization 和 cycle time。

計算完成後，service 會輸出完整 JSON。最新一次結果會存成 `time_series_latest_output.json`，歷史紀錄會追加到 `processed_result_database_demo.json`。Rule 判斷不在這個 service 裡，所以 `state`、`risk_text`、`fault_detail` 等欄位目前保留空值，等後續 Rule Service 補上。
