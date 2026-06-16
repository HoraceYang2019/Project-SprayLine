# TimeSeriesService UI Adapter 今日更新報告

## 一、今天這版的目的

今天這版主要是為了讓 UI 同學比較好串接 TimeSeriesService。

原本核心 service 已經可以回傳完整資料：

```text
POST /api/time-series
```

但是這份核心 output 比較偏後端整合格式，裡面包含：

```text
viewer_state
summary
stations[].metrics
stations[].process_parameters
stations[].component_metrics
stations[].spray_width_image
calculation_info
database_info
```

如果 UI 直接吃這份資料，前端需要自己轉很多欄位，例如：

```text
line_1 要轉成 M1
station_name_zh 要轉成 name
metrics.pressure_bar 要拉到 station card
process_parameters.temperature_c 要拉到 station card
component_metrics.nozzle 要在點開 nozzle 時顯示
```

所以今天新增一層 **UI Adapter**，專門把核心 output 轉成 UI 比較好用的 JSON 格式。

---

## 二、今天新增與修改的檔案

### 1. 新增 `src/ui_adapter.py`

這是今天最主要新增的檔案。

用途：

```text
把核心 TimeSeriesService output 轉成 UI 畫面需要的 output。
```

主要負責：

```text
1. 將 UI request 轉成核心 service request
2. 將核心 station output 轉成 UI station card
3. 建立 UI 初始化畫面 JSON
4. 建立 UI 單站詳細資料 JSON
5. 建立 UI 元件詳細資料 JSON
```

---

### 2. 修改 `src/api_server.py`

今天在 API server 裡新增三個 UI 專用 endpoint：

```text
POST /api/time-series/ui/summary
POST /api/time-series/ui/station-detail
POST /api/time-series/ui/component-detail
```

原本核心 endpoint 保留不動：

```text
POST /api/time-series
```

---

### 3. 新增 UI request / output 範例

新增以下範例檔：

```text
examples/ui_summary_request.json
examples/ui_summary_output_demo.json

examples/ui_station_detail_request.json
examples/ui_station_detail_output_demo.json

examples/ui_component_detail_request.json
examples/ui_component_detail_output_demo.json
```

這些檔案可以給 UI 同學參考要傳什麼，以及會收到什麼。

---

# 1. UI 要怎麼 call 我的 function？

UI 不會直接 call Python function，UI 會透過 HTTP API 呼叫。

今天新增三個 UI 可以直接使用的 API。

---

## 1.1 初始化畫面：Summary API

### UI 要 call 的 API

```text
POST /api/time-series/ui/summary
```

### 對應的 API function 名稱

```python
HandleTimeSeriesUiSummaryRequest(request)
```

### 內部會呼叫的主要 function

```python
BuildBaseRequestFromUiRequest(request)
HandleTimeSeriesQuery(core_request)
BuildUiSummaryOutput(core_output)
```

### 使用情境

UI 第一次進入 dashboard，或刷新總覽畫面時呼叫這個 API。

用途是取得：

```text
viewer_state
summary
stations card data
```

也就是 UI 首頁卡片、總覽數值、目前時間狀態會用到的資料。

---

## 1.2 點開某一站：Station Detail API

### UI 要 call 的 API

```text
POST /api/time-series/ui/station-detail
```

### 對應的 API function 名稱

```python
HandleTimeSeriesUiStationDetailRequest(request)
```

### 內部會呼叫的主要 function

```python
BuildBaseRequestFromUiRequest(request)
HandleTimeSeriesQuery(core_request)
BuildUiStationDetailOutput(core_output, line_id)
```

### 使用情境

UI 使用者點開某一站，例如底漆站、面漆站或金漆站時呼叫。

用途是取得某一站比較完整的資料，例如：

```text
metrics
process_parameters
component_metrics
spray_width_image
fault_detail
component_overview
```

---

## 1.3 點開某個元件：Component Detail API

### UI 要 call 的 API

```text
POST /api/time-series/ui/component-detail
```

### 對應的 API function 名稱

```python
HandleTimeSeriesUiComponentDetailRequest(request)
```

### 內部會呼叫的主要 function

```python
BuildBaseRequestFromUiRequest(request)
HandleTimeSeriesQuery(core_request)
BuildUiComponentDetailOutput(core_output, line_id, component_name)
```

### 使用情境

UI 使用者點開某一站裡面的元件細節時呼叫，例如：

```text
nozzle
filter_mesh
spray_width
```

用途是只回傳該元件的詳細數值。

---

## 1.4 核心 API 仍然保留

除了 UI Adapter API，原本核心 API 還是保留：

```text
POST /api/time-series
```

對應 function：

```python
HandleTimeSeriesRequest(request)
```

內部主 function：

```python
HandleTimeSeriesQuery(request)
```

這份核心 API 比較適合給：

```text
Rule Service
Database
Integration Service
其他後端模組
```

使用。

---

## 1.5 今日版 function / API 對照表

| UI 使用情境 | UI 呼叫 API | API function | 主要轉換 function |
|---|---|---|---|
| 初始化 dashboard | `POST /api/time-series/ui/summary` | `HandleTimeSeriesUiSummaryRequest()` | `BuildUiSummaryOutput()` |
| 點開某一站 | `POST /api/time-series/ui/station-detail` | `HandleTimeSeriesUiStationDetailRequest()` | `BuildUiStationDetailOutput()` |
| 點開某個元件 | `POST /api/time-series/ui/component-detail` | `HandleTimeSeriesUiComponentDetailRequest()` | `BuildUiComponentDetailOutput()` |
| 核心 service | `POST /api/time-series` | `HandleTimeSeriesRequest()` | `HandleTimeSeriesQuery()` |

---

# 2. 我要收到什麼資料？

今天新增的 UI Adapter API 會接收三種 request。

---

## 2.1 Summary API 收到的資料

### Endpoint

```text
POST /api/time-series/ui/summary
```

### Request JSON

```json
{
  "schema_version": "v1.0",
  "request_id": "ui_summary_001",
  "mode": "time",
  "window_type": "current",
  "slider_value": 0,
  "line_scope": "all"
}
```

### 欄位名稱與中文說明

| 欄位名稱 | 中文名稱 | 說明 |
|---|---|---|
| `schema_version` | 架構版本 | request 格式版本 |
| `request_id` | 請求編號 | UI 這次呼叫的追蹤 ID |
| `mode` | 模式 | 目前使用時間軸模式，值為 `time` |
| `window_type` | 時間視窗 | 例如 `current`、`2hour` |
| `slider_value` | 時間軸滑桿值 | 判斷 past/current/future |
| `line_scope` | 產線範圍 | `all` 代表全部產線 |

---

## 2.2 Station Detail API 收到的資料

### Endpoint

```text
POST /api/time-series/ui/station-detail
```

### Request JSON

```json
{
  "schema_version": "v1.0",
  "request_id": "ui_station_detail_001",
  "mode": "time",
  "window_type": "current",
  "slider_value": 0,
  "line_id": "line_1"
}
```

### 欄位名稱與中文說明

| 欄位名稱 | 中文名稱 | 說明 |
|---|---|---|
| `schema_version` | 架構版本 | request 格式版本 |
| `request_id` | 請求編號 | UI 這次呼叫的追蹤 ID |
| `mode` | 模式 | 目前使用時間軸模式 |
| `window_type` | 時間視窗 | 例如 `current`、`2hour` |
| `slider_value` | 時間軸滑桿值 | 判斷 past/current/future |
| `line_id` | 產線 ID | 指定要查哪一站，例如 `line_1` |

### `line_id` 對應

| line_id | UI 顯示 ID | 中文站名 |
|---|---|---|
| `line_1` | `M1` | 底漆站 |
| `line_2` | `M2` | 面漆站 |
| `line_3` | `M3` | 金漆站 |

---

## 2.3 Component Detail API 收到的資料

### Endpoint

```text
POST /api/time-series/ui/component-detail
```

### Request JSON

```json
{
  "schema_version": "v1.0",
  "request_id": "ui_component_detail_001",
  "mode": "time",
  "window_type": "current",
  "slider_value": 0,
  "line_id": "line_1",
  "component_name": "nozzle"
}
```

### 欄位名稱與中文說明

| 欄位名稱 | 中文名稱 | 說明 |
|---|---|---|
| `schema_version` | 架構版本 | request 格式版本 |
| `request_id` | 請求編號 | UI 這次呼叫的追蹤 ID |
| `mode` | 模式 | 目前使用時間軸模式 |
| `window_type` | 時間視窗 | 例如 `current`、`2hour` |
| `slider_value` | 時間軸滑桿值 | 判斷 past/current/future |
| `line_id` | 產線 ID | 指定要查哪一站 |
| `component_name` | 元件名稱 | 指定要查哪個元件 |

### `component_name` 可用值

| component_name | 中文 |
|---|---|
| `nozzle` | 噴嘴 |
| `filter_mesh` | 濾網 |
| `spray_width` | 噴幅 |

---

## 2.4 UI request 會被轉成 core request

今天新增：

```python
BuildBaseRequestFromUiRequest(ui_request)
```

作用是把 UI request 轉成核心 service request。

核心 service 需要的格式是：

```json
{
  "schema_version": "v1.0",
  "service_name": "TimeSeriesService",
  "request_id": "ui_summary_001",
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

其中 `service_name` 和 `requested_metrics` 會由 adapter 幫 UI 補上，所以 UI request 可以比較簡化。

---

# 3. 我要怎麼做計算？

今天新增的 UI Adapter **不重新計算公式**。

它的做法是：

```text
UI request
    ↓
BuildBaseRequestFromUiRequest()
    ↓
HandleTimeSeriesQuery()
    ↓
核心 TimeSeriesService 完成計算
    ↓
UI Adapter 轉換 output 格式
```

所以所有實際數值仍由核心 service 計算，UI Adapter 只負責轉格式。

---

## 3.1 時間狀態判斷

核心 function：

```python
DetermineTimeType(request)
```

判斷方法：

```text
slider_value < 0  → past
slider_value = 0  → current
slider_value > 0  → future
```

---

## 3.2 Sample method

核心 function：

```python
GetSampleMethod(time_type)
```

不同時間狀態使用不同代表值方法：

| time_type | 方法 | 說明 |
|---|---|---|
| `past` | `mean` | 過去資料取平均 |
| `current` | `recent_average` | 目前資料取最近 5 筆平均 |
| `future` | `latest_valid` | 未來資料取最後一筆有效值 |

---

## 3.3 Sample method 算法

核心 function：

```python
ApplySampleMethod(values, method, recent_n=5)
```

| 方法 | 中文 | 算法 |
|---|---|---|
| `mean` | 平均值 | 所有有效數值加總 / 筆數 |
| `recent_average` | 最近 N 筆平均 | 取最近 5 筆有效數值平均 |
| `latest_valid` | 最新有效值 | 取最後一筆有效資料 |
| `count` | 計數 | 若是布林值，計算 `True` 次數 |
| `majority` | 多數決 | 取出現最多的值 |
| `max` | 最大值 | 取最大數值 |
| `min` | 最小值 | 取最小數值 |

---

## 3.4 Nozzle 計算

核心 function：

```python
CalculateNozzleMetrics(parameters)
```

### 輸入欄位

```text
pressure_bar
flow_rate_ml_min
nominal_flow_rate_ml_min
nozzle_usage_time_hr
nozzle_rul_hr
```

### 輸出欄位

```text
pressure_bar
flow_rate_ml_min
nozzle_clog_rate_pct
nozzle_maintainability_pct
```

### 噴嘴堵塞率公式

```text
nozzle_clog_rate_pct =
max(0, (nominal_flow_rate_ml_min - flow_rate_ml_min)
        / nominal_flow_rate_ml_min * 100)
```

說明：

```text
如果實際流量低於額定流量，代表噴嘴可能堵塞。
差距越大，堵塞率越高。
max(0, ...) 是避免堵塞率出現負值。
```

### 噴嘴維護性公式

```text
nozzle_maintainability_pct =
nozzle_rul_hr / (nozzle_rul_hr + nozzle_usage_time_hr) * 100
```

補充：

```text
目前 prototype 直接產生 nozzle_rul_hr。
正式資料若拿不到 nozzle_rul_hr，可以改成由 nozzle_expected_life_hr - nozzle_usage_time_hr 算出。
```

---

## 3.5 Filter Mesh 計算

核心 function：

```python
CalculateFilterMetrics(parameters)
```

### 輸入欄位

```text
in_flow_ml_min
out_flow_ml_min
filter_usage_time_hr
filter_rul_hr
```

### 輸出欄位

```text
flow_loss_pct
filter_clog_rate_pct
filter_maintainability_pct
```

### 流量損失率公式

```text
flow_loss_pct =
max(0, (in_flow_ml_min - out_flow_ml_min)
        / in_flow_ml_min * 100)
```

### 濾網堵塞率公式

```text
filter_clog_rate_pct = flow_loss_pct
```

### 濾網維護性公式

```text
filter_maintainability_pct =
filter_rul_hr / (filter_rul_hr + filter_usage_time_hr) * 100
```

---

## 3.6 Spray Width 計算

核心 function：

```python
CalculateSprayWidthMetrics(parameters)
```

### 輸入欄位

```text
spray_width_mm
target_spray_width_mm
target_min_mm
target_max_mm
```

### 輸出欄位

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

## 3.7 Line-level metrics 計算

核心 function：

```python
CalculateLineMetrics(sampled_data)
```

### 總堵塞率

```text
clog_rate_pct =
max(nozzle_clog_rate_pct, filter_clog_rate_pct)
```

### 總維護性

```text
maintainability_pct =
min(nozzle_maintainability_pct, filter_maintainability_pct)
```

### 品質分數

```text
quality_score_pct =
ok_count / total_count * 100
```

若沒有 `ok_count` 與 `total_count`：

```text
quality_score_pct = coverage_score_pct
```

### 稼動率

```text
utilization_pct =
running_time_sec / total_window_time_sec * 100
```

### 可用率

```text
availability_pct =
available_time_sec / planned_time_sec * 100
```

### 週期時間

```text
cycle_time_sec =
part_end_time - part_start_time
```

---

## 3.8 UI Adapter 做的轉換

UI Adapter 的計算主要是「欄位轉換」，不是公式計算。

### line_id 轉 UI ID

```text
line_1 → M1
line_2 → M2
line_3 → M3
```

### station card 欄位攤平

核心資料：

```text
station.metrics.pressure_bar
station.metrics.flow_rate_ml_min
station.process_parameters.temperature_c
station.process_parameters.utilization_pct
station.spray_width_image.target_min_mm
```

轉成 UI summary：

```text
station.pressure_bar
station.flow_rate_ml_min
station.temperature_c
station.utilization_pct
station.target_min_mm
```

這樣 UI 同學不用在前端做太多巢狀資料解析。

---

# 4. 計算完之後要輸出什麼？

今天新增三種 UI output。

---

## 4.1 UI Summary Output

### Endpoint

```text
POST /api/time-series/ui/summary
```

### 用途

```text
給 UI 初始化 dashboard 畫面使用。
```

### Output 欄位名稱

```json
{
  "schema_version": "v1.0",
  "service_name": "TimeSeriesService",
  "output_type": "ui_summary",
  "generated_at": "...",
  "request_id": "ui_summary_001",
  "viewer_state": {},
  "summary": {},
  "stations": [],
  "source": {}
}
```

### `stations[]` 欄位名稱

```json
{
  "id": "M1",
  "line_id": "line_1",
  "name": "底漆站",
  "english_name": "Primer Station",
  "recipe": "Primer_A",
  "pressure_bar": 2.5,
  "flow_rate_ml_min": 118.6,
  "spray_width_mm": 52.3,
  "target_min_mm": 48,
  "target_max_mm": 56,
  "temperature_c": 27.8,
  "availability_pct": 86.2,
  "maintainability_pct": 72.4,
  "clog_rate_pct": 9.5,
  "quality_score_pct": 94.3,
  "utilization_pct": 78.6,
  "cycle_time_sec": 52,
  "state": null,
  "risk_text": null
}
```

這份是 UI 首頁卡片最容易使用的格式。

---

## 4.2 UI Station Detail Output

### Endpoint

```text
POST /api/time-series/ui/station-detail
```

### 用途

```text
給 UI 點開某一站詳細資料時使用。
```

### Output 欄位名稱

```json
{
  "schema_version": "v1.0",
  "service_name": "TimeSeriesService",
  "output_type": "ui_station_detail",
  "generated_at": "...",
  "request_id": "ui_station_detail_001",
  "viewer_state": {},
  "line_id": "line_1",
  "ui_id": "M1",
  "name": "底漆站",
  "english_name": "Primer Station",
  "state": null,
  "risk_text": null,
  "metrics": {},
  "process_parameters": {},
  "component_metrics": {},
  "spray_width_image": {},
  "fault_detail": [],
  "component_overview": [],
  "source": {}
}
```

其中：

```text
metrics
```

包含：

```text
availability_pct
clog_rate_pct
pressure_bar
flow_rate_ml_min
maintainability_pct
quality_score_pct
risk_text
spray_width_mm
```

```text
process_parameters
```

包含：

```text
recipe_name
temperature_c
utilization_pct
cycle_time_sec
```

```text
component_metrics
```

包含：

```text
nozzle
filter_mesh
spray_width
```

---

## 4.3 UI Component Detail Output

### Endpoint

```text
POST /api/time-series/ui/component-detail
```

### 用途

```text
給 UI 點開 nozzle / filter_mesh / spray_width 元件詳細資料時使用。
```

### Output 欄位名稱

```json
{
  "schema_version": "v1.0",
  "service_name": "TimeSeriesService",
  "output_type": "ui_component_detail",
  "generated_at": "...",
  "request_id": "ui_component_detail_001",
  "viewer_state": {},
  "line_id": "line_1",
  "ui_id": "M1",
  "station_name": "底漆站",
  "component_name": "nozzle",
  "component_name_zh": "噴嘴",
  "data": {},
  "source": {}
}
```

---

## 4.4 如果 component_name = nozzle

`data` 會包含：

```json
{
  "pressure_bar": 2.5,
  "flow_rate_ml_min": 118.6,
  "nozzle_clog_rate_pct": 1.2,
  "nozzle_maintainability_pct": 76.0
}
```

---

## 4.5 如果 component_name = filter_mesh

`data` 會包含：

```json
{
  "flow_loss_pct": 8.2,
  "filter_clog_rate_pct": 8.2,
  "filter_maintainability_pct": 70.5
}
```

---

## 4.6 如果 component_name = spray_width

`data` 會包含：

```json
{
  "spray_width_mm": 52.1,
  "width_error_mm": 0.1,
  "width_error_pct": 0.19,
  "coverage_score_pct": 99.81,
  "target_min_mm": 48,
  "target_max_mm": 56
}
```

---

## 4.7 核心 output 仍保留

核心 endpoint：

```text
POST /api/time-series
```

仍會輸出：

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

這份不是今天 UI Adapter 的重點，但保留給後續整合使用。

---

# 5. 今天做了什麼更新？

## 5.1 新增 UI Adapter 層

新增：

```text
src/ui_adapter.py
```

作用：

```text
把核心 TimeSeriesService output 轉成 UI 好接的 JSON 格式。
```

---

## 5.2 新增 UI 初始化畫面 API

新增：

```text
POST /api/time-series/ui/summary
```

用途：

```text
UI 初始化 dashboard 或刷新總覽時呼叫。
```

---

## 5.3 新增 UI 單站詳細 API

新增：

```text
POST /api/time-series/ui/station-detail
```

用途：

```text
UI 點開某一站時呼叫。
```

---

## 5.4 新增 UI 元件詳細 API

新增：

```text
POST /api/time-series/ui/component-detail
```

用途：

```text
UI 點開 nozzle / filter_mesh / spray_width 時呼叫。
```

---

## 5.5 新增 UI request / output 範例

新增：

```text
examples/ui_summary_request.json
examples/ui_summary_output_demo.json
examples/ui_station_detail_request.json
examples/ui_station_detail_output_demo.json
examples/ui_component_detail_request.json
examples/ui_component_detail_output_demo.json
```

這些檔案是給 UI 同學參考用。

---

## 5.6 保留核心 service，不把 UI 格式混進核心計算

核心 API：

```text
POST /api/time-series
```

核心 function：

```python
HandleTimeSeriesQuery()
```

都保留。

今天新增的 UI Adapter 只是外層格式轉換，不影響原本計算流程。

---

## 5.7 Rule 還是不在這個 service

今天沒有新增 Rule 判斷。

以下欄位仍然保留為 `null` 或空陣列：

```text
state
risk_text
fault_detail
component_overview
normal_count
warning_count
predict_risk_count
```

這些之後交給 Rule Service / Rule Engine 補。

---

# 六、給 UI 同學的串接建議

## 初始化 dashboard

呼叫：

```text
POST /api/time-series/ui/summary
```

收到：

```text
viewer_state
summary
stations[]
```

UI 首頁卡片直接吃 `stations[]`。

---

## 點開某一站

呼叫：

```text
POST /api/time-series/ui/station-detail
```

request 裡帶：

```text
line_id
```

例如：

```json
{
  "line_id": "line_1",
  "slider_value": 0,
  "window_type": "current"
}
```

---

## 點開某個元件

呼叫：

```text
POST /api/time-series/ui/component-detail
```

request 裡帶：

```text
line_id
component_name
```

例如：

```json
{
  "line_id": "line_1",
  "component_name": "nozzle",
  "slider_value": 0,
  "window_type": "current"
}
```

---

# 七、報告時可以這樣講

今天主要是為了讓 UI 更容易串接，所以在核心 TimeSeriesService 外面新增一層 UI Adapter。核心 API `POST /api/time-series` 仍保留，主要給後端整合使用；UI 端則可以呼叫 `/api/time-series/ui/summary`、`/api/time-series/ui/station-detail` 和 `/api/time-series/ui/component-detail`。

UI 初始化畫面時呼叫 summary API，可以取得 station cards 和總覽資訊；點開某一站時呼叫 station-detail API，可以取得該站完整 metrics、process parameters 和 component metrics；點開 nozzle、filter 或 spray width 時呼叫 component-detail API，可以取得單一元件的詳細資料。

這樣的設計把核心計算邏輯和 UI 顯示格式分開，避免把 UI 專用欄位直接混進核心 service output，也讓 UI 同學可以依照畫面功能分別呼叫對應 API。
