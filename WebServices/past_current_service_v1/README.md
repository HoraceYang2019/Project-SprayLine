# Past Service / Current Service Prototype v1.1

本版本在原本 Past / Current Service Prototype v1 的基礎上，加入：

```text
alarm_count
defect_count
```

用來解決：

```text
Past state 用 majority 時，短暫 Alarm / Defect 可能被主要狀態蓋掉
```

因此目前設計是：

```text
Past state → majority
alarm_count → count
defect_count → count
```

也就是：

```text
主要狀態用 majority 表示，
異常事件用 count 保留發生次數。
```

---

# 1. 本版本完成內容

本版本完成：

```text
1. past_service.py 加入 alarm_count / defect_count
2. current_service.py 加入 alarm_count / defect_count
3. PAST_SAMPLE_METHOD 加入 count 規則
4. CURRENT_SAMPLE_METHOD 加入 count 規則
5. output template 加入 alarm_count / defect_count
6. count 方法支援 bool event 計數
7. README 更新說明
```

---

# 2. 為什麼需要 alarm_count / defect_count

原本 Past Service 的 state 使用：

```text
majority
```

例如歷史區間狀態：

```text
Running
Running
Running
Alarm
Running
Running
```

如果只用 majority，結果會是：

```text
past_state = Running
```

這樣代表「主要狀態」沒有錯。

但是問題是：

```text
中間發生過一次 Alarm 會被蓋掉
```

所以新增：

```text
alarm_count
defect_count
```

來保留異常資訊。

最後可以輸出：

```text
state = Running
alarm_count = 1
defect_count = 0
```

這樣就比較合理。

---

# 3. sample_method 更新

目前支援：

| sample_method | 中文意思 | 適合用在哪 |
|---|---|---|
| latest_valid | 最新有效值 | current state、目前 KPI |
| mean | 平均值 | past 數值型資料 |
| recent_average | 最近 N 筆平均 | current pressure、flow、temperature |
| majority | 多數決 | past state |
| max | 最大值 | clog_rate、risk 等 |
| count | 計數 | alarm_count、defect_count |

---

# 4. Past Service sample_method

目前 Past Service 使用：

```text
state → majority

pressure_bar → mean
flow_rate_ml_min → mean
quality_score_pct → mean
availability_pct → mean
clog_rate_pct → mean
maintainability_pct → mean

alarm_count → count
defect_count → count

temperature_c → mean
utilization_pct → mean
cycle_time_sec → mean

risk_text → latest_valid
```

---

# 5. Current Service sample_method

目前 Current Service 使用：

```text
state → latest_valid

pressure_bar → recent_average
flow_rate_ml_min → recent_average
temperature_c → recent_average

quality_score_pct → latest_valid
availability_pct → latest_valid
clog_rate_pct → latest_valid
maintainability_pct → latest_valid

alarm_count → count
defect_count → count

utilization_pct → latest_valid
cycle_time_sec → latest_valid
risk_text → latest_valid
```

---

# 6. count 的計算方式

目前 `count` 的邏輯：

## 情況一：布林值

```python
[False, True, False, True]
```

代表兩次事件發生。

結果：

```text
count = 2
```

## 情況二：一般事件

```python
["Alarm", None, "Alarm"]
```

結果：

```text
count = 2
```

---

# 7. raw_dataset 範例

```python
raw_dataset = {
    "M1": {
        "state": ["Running", "Running", "Alarm", "Running"],
        "metrics": {
            "pressure_bar": [2.1, 2.2, 2.0, 2.1],
            "alarm_count": [False, False, True, False],
            "defect_count": [False, True, False, False]
        },
        "process_parameters": {
            "temperature_c": [26.1, 26.2, 26.5, 26.3]
        }
    }
}
```

Past Service 結果會類似：

```text
state = Running
alarm_count = 1
defect_count = 1
```

---

# 8. 目前尚未完成

目前還沒完成：

```text
1. 真實 DB / SQL Search 串接
2. MQTT / OPC UA / API 串接
3. KPI 原始公式正式定案
4. station state 判斷邏輯
5. Future Service 串接
6. Statistics Service 串接
7. UI(M) / UI(E) mapping
8. TTL 補上 SamplingMethod individuals
```

---

# 9. 接下來建議

下一步建議先做：

```text
1. 定義 state logic
2. 定義 KPI 公式
3. 確認 alarm_count / defect_count 來源欄位
4. 確認 Current window 是最近幾筆或幾秒
```

尤其是：

```text
alarm_count / defect_count 要從哪裡來
```

需要跟資料來源對齊。

可能來源：

```text
alarm_count → controller alarm / machine state alarm
defect_count → ProductPart 的 Defect 欄位
```
