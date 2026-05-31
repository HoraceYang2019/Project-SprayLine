# past_current_待定

本文件整理目前 Past / Current Service 討論中尚未確定、需要與沈同學及組員確認的事項。 
目前先作為討論清單，後續確認後可再回填到 schema、field catalog、ontology 或 ipynb 報告中。

---

## 1. Past Service 的 `sample_method` 尚未確定

### 目前欄位

```json
"sample_method": "defined_by_service"
```

### 目前狀況

Past Service 查的是一段歷史資料，例如過去某段時間或過去某幾個 batch。 
但目前尚未規定 Past Service 要用哪一種方式，把多筆歷史資料整理成輸出結果。

目前的 `defined_by_service` 只是 placeholder，表示取樣或彙整方式還沒有定案，不是正式方法名稱。

### 需要討論的問題

Past Service 面對歷史資料時，要採用哪一種取樣／彙整方式？

可能選項：

```text
average
latest
max
min
median
window_summary
```

### 暫定建議

先不要在 schema 或 ontology 中把 Past Service 的 `sample_method` 寫死。 
可以先保留 `SamplingMethod` 的概念，等組員確認後再決定實際值。

---

## 2. `flow_rate_ml_min` 的實際單位需確認

### 目前欄位

```json
"flow_rate_ml_min": "<number>"
```

### 目前狀況

目前為了對齊 / UI 欄位命名，先使用 `flow_rate_ml_min`。 
但是 Past / Current Service 上游資料中的流量原始單位尚未確認。

如果原始資料不是 `ml/min`，就不能直接填入 `flow_rate_ml_min`，必須先換算。

### 需要討論的問題

1. 上游資料中的 flow rate 原始單位是什麼？
2. 是否確定可以統一成 `ml/min`？
3. 如果不能確認，是否應先改用較彈性的欄位？

可能改法：

```json
"flow_rate_value": "<number>",
"flow_rate_unit": "<string>"
```

或在 field catalog / schema 中標註：

```text
flow rate unit to be confirmed
```

### 暫定建議

若短期內無法確認單位，建議先在文件中特別標註單位待確認。 
正式資料進入 `flow_rate_ml_min` 前，必須確認或換算為 `ml/min`。

---

## 3. Current Service 的 `window_size` 尚未確定

### 目前欄位

```json
"window": {
 "mode": "current",
 "window_type": "current_window",
 "window_size": "defined_by_system"
}
```

### 目前狀況

Current Service 的 `window_size` 尚未定義清楚。 
目前不知道 Current Service 的 output 到底代表哪一種「目前資料」。

可能情況：

```text
最新一筆資料
最近 N 秒資料
最近 N 筆有效資料
短時間 rolling window
短時間 window summary
```

### 使用者提出的疑問

Current Service 裡的 `window_size`，是否其實和 Past / Future / Statistics Service 裡提到的 `2hour`、`10batch` 屬於同一套「Window」概念？

也就是說，這些可能都是在描述：

```text
資料要用多大的視窗來看
```

只是不同 service 的使用情境不同：

```text
Past Service：看歷史資料視窗，例如 2hour / 10batch
Current Service：看目前或近即時資料視窗，例如 latest / recent N 秒 / short window
Future Service：看未來預測視窗，例如 future 2hour / future 10batch
Statistics Service：依據前面資料彙整成統計輸出
```

### 使用者提出的可能方向

是否可以由 input 端統一選擇 window 設定，例如：

```json
"window": {
 "mode": "<time|batch|current|future>",
 "window_type": "<2hour|10batch|current_window|prediction_window>",
 "window_size": "<defined value>"
}
```

然後後續 Past / Current / Future / Statistics Service 都 follow input 的 window 定義。

概念類似：

```text
input 決定 window
↓
Past / Current / Future / Statistics Service follow input
```

這只是目前提出的可行方向，尚未決定一定採用。

### 實務補充

Current Service 實務上通常不會直接使用 `2hour` 或 `10batch` 這種較大的 window，因為 Current 的重點是「現在」或「近即時」。

較常見的做法會是：

```text
latest_valid
recent_N_seconds_average
recent_N_samples_average
short_window_summary
current_rolling_window
```

不同欄位可能也適合不同取法：

- `state`：通常適合用 `latest_valid`
- `pressure_bar`、`flow_rate_ml_min`、`temperature_c`：通常較適合用短時間平均或 rolling window，避免數值跳動
- `quality_score_pct`、`utilization_pct`、`cycle_time_sec`：可能要討論是用目前 batch 暫估，還是最新完成 batch

### 暫定建議

目前先採用：

```text
JSON / schema：保持彈性，不急著寫死
Ontology：統一成 StatisticsWindow 概念
實作前：再和沈同學確認 Current Service 的 current output 採用哪種 window_size
```

Ontology 可先統一成：

```text
StatisticsWindow
├─ HistoricalWindow
├─ CurrentWindow
└─ PredictionWindow
```

也就是 schema 可以保留不同 service 的 window 表述，但 ontology 上先統一為同一套 Window 概念。

---

## 4. Current Service 的 `sample_method` 尚未確定

### 目前欄位

```json
"sample_method": "defined_by_service"
```

### 目前狀況

Current Service 面對目前或近即時資料時，尚未規定要怎麼取代表值。

可能情況：

```text
latest
latest_valid
recent_average
recent_n_average
short_window_summary
```

### 需要討論的問題

Current Service 的 current output 到底代表：

1. 最新一筆資料？
2. 最新一筆有效資料？
3. 最近 N 秒平均？
4. 最近 N 筆平均？
5. 短時間 window summary？

### 暫定建議

先保留彈性，不在 schema 中寫死。 
後續與沈同學確認 Current Service 的資料來源、更新頻率與實作方式後，再決定 `sample_method` 的正式值。

---

# 目前總結

目前 Past / Current Service 的主要待確認重點有四個：

1. Past Service 的歷史資料彙整方式尚未定案。
2. `flow_rate_ml_min` 的原始單位尚未確認。
3. Current Service 的 `window_size` 尚未定義清楚，且需要確認是否與 Past / Future / Statistics Service 的 window 概念統一。
4. Current Service 的 `sample_method` 尚未定案。

目前整體暫定方向：

```text
schema / JSON 保持彈性
ontology 統一概念
實作前再與沈同學及組員確認細節
```
