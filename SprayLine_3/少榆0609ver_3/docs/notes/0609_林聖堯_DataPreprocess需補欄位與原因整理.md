# 林聖堯 DataPreprocess 需補欄位與加入原因整理

本文件整理目前噴塗產線專案中，DataPreprocess 端建議補充或確認的欄位。  
目的不是要求 DataPreprocess 負責所有 Rule / Ontology / Service，而是為了讓後續資料能順利接到：

```text
Database
API / Service
Ontology
EventRule
Dashboard
Troubleshooting / 原因對策
```

---

## 一、Batch 時間區間欄位

這類欄位用來把「時間序列感測資料」對應到「某一個批次」。

| 欄位 | 為什麼要加入 |
|---|---|
| `batch_id` | 用來識別每一個批次，讓 sensor data、品質結果、event、risk_level 可以回查到同一批產品。 |
| `station` | 用來知道該批次在哪一站生產，例如 `Station_1`、`Station_2`、`Station_3`，後續 DB、API、ontology 都需要一致。 |
| `batch_start_time` | 用來知道該批次開始生產的時間，才能抓出該批次期間的 sensor_1hz 資料。 |
| `batch_end_time` | 用來知道該批次結束生產的時間，和 `batch_start_time` 形成時間區間。 |
| `completed_at` | 用來表示批次完成時間，方便 Dashboard 顯示完工批次，也可作為 batch 查詢與排序依據。 |

### 加入原因總結

如果沒有 `batch_start_time` 和 `batch_end_time`，By Time 資料只能知道某個時間點的感測值，但無法知道這些感測異常是否發生在某一個 batch 的生產期間。  
因此後續無法準確做 batch-level diagnosis、risk_level 或品質追蹤。

---

## 二、品質 / 預測結果欄位

這類欄位用來支援 risk_level、品質診斷與 Dashboard 批次風險顯示。  
若這些不是 DataPreprocess 負責產生，也需要確認來源是 Prediction Service、QC Service 或 Dashboard Service。

| 欄位 | 為什麼要加入 |
|---|---|
| `ok_count` | 用來記錄良品數量，可用於計算良率與批次品質結果。 |
| `ng_count` | 用來記錄不良品數量，討論提到的 risk_level 規則需要使用 NG 數量。 |
| `predicted_ok_rate` | 用來表示預測良率，討論提到的 High / Medium / Low 風險判斷會用到 predicted_ok。 |
| `predicted_ng_count` | 用來表示預測 NG 數量，可輔助 manager dashboard 顯示預測風險。 |
| `quality_score` | 用來統整品質評分，方便 Dashboard 用單一指標顯示品質狀態。 |
| `defect_type` | 用來表示瑕疵種類，例如噴幅異常、膜厚不足、表面缺陷等，後續原因對策需要用。 |
| `defect_code` | 用來讓瑕疵種類有固定代碼，方便 DB 查詢、API 回傳與 ontology 對應。 |
| `risk_level` | 用來表示批次風險等級，例如 High、Medium、Low，支援討論提出的批次篩選 API。 |

### 加入原因總結

目前感測欄位可以判斷「機台或製程是否異常」，但不一定能判斷「產品最後品質是否受影響」。  
如果要做 risk_level、batch summary 或 manager dashboard，就需要品質 / 預測結果欄位。

---

## 三、Threshold / 判斷基準欄位

這類欄位用來定義每個 sensor 什麼範圍算正常、警告或異常。  
若 threshold 尚未定案，欄位仍可先保留，數值標成 pending。

| 欄位 | 為什麼要加入 |
|---|---|
| `sensor_name` | 用來指定此 threshold 對應哪一個 sensor 或訊號，例如 `filter_diff_pressure_bar`。 |
| `station` | 不同 station 可能有不同門檻，需指定適用站別。 |
| `normal_min` | 用來定義正常範圍下限。 |
| `normal_max` | 用來定義正常範圍上限。 |
| `warning_min` | 用來定義 warning 下限，支援輕度異常判斷。 |
| `warning_max` | 用來定義 warning 上限，支援輕度異常判斷。 |
| `alarm_min` | 用來定義 alarm 下限，支援嚴重異常判斷。 |
| `alarm_max` | 用來定義 alarm 上限，支援嚴重異常判斷。 |
| `unit` | 用來避免單位混亂，例如 bar、mm、%、°C。 |
| `threshold_source` | 用來記錄 threshold 來源，例如討論提供、組員設定、實驗資料、pending。 |

### 加入原因總結

Rule Service 或 EventRule 不能只知道 sensor 數值，還需要知道「超過多少算異常」。  
沒有 threshold，就只能顯示資料，不能正式判斷 warning / alarm。

---

## 四、Event / Alert 紀錄欄位

這類欄位用來支援余宇承提到的「觸發記錄 event 的 rule 規則要放在 ontology」。  
DataPreprocess 不一定要產生 event，但資料結構要能支援後續 event rule 寫入 `alert_event`。

| 欄位 | 為什麼要加入 |
|---|---|
| `event_id` | 用來唯一識別每一筆 event / alert。 |
| `event_time` | 用來記錄事件發生時間，方便回查當時 sensor data。 |
| `station` | 用來知道事件發生在哪一站。 |
| `event_type` | 用來表示事件類型，例如 filter_warning、pressure_alarm、spray_width_abnormal。 |
| `severity` | 用來表示嚴重程度，例如 info、warning、alarm、critical。 |
| `source_signal` | 用來表示是哪一個 sensor 或欄位觸發事件，例如 `air_pressure_bar`。 |
| `source_value` | 用來記錄觸發事件當下的實際數值，方便後續 diagnosis 與追蹤。 |
| `trigger_rule_id` | 用來記錄是哪一條 rule 觸發 event，方便 ontology 和 Rule Service 對應。 |
| `message` | 用來提供 Dashboard 顯示的警示文字。 |
| `acknowledged_status` | 用來記錄警示是否已被工程師確認或處理。 |

### 加入原因總結

如果只有 event 結果，卻沒有 `source_signal`、`source_value`、`trigger_rule_id`，就無法追蹤事件是由哪個感測值和哪條 rule 觸發。  
這會導致 ontology、DB、Dashboard 之間無法完整串接。

---

## 五、DataPreprocess 狀態欄位

這類欄位用來說明資料是否經過補值、去雜訊、重取樣或異常值處理。  
這對後續 Rule 判斷很重要，因為 raw data 和 cleaned data 的可信度不同。

| 欄位 | 為什麼要加入 |
|---|---|
| `data_quality_flag` | 用來表示此筆資料品質，例如 normal、missing、interpolated、outlier。 |
| `is_interpolated` | 用來標示此筆資料是否為補值資料，避免把補值結果當成真實感測值。 |
| `is_outlier` | 用來標示此筆資料是否被判斷為離群值。 |
| `preprocess_method` | 用來記錄前處理方法，例如 cleaned、resampled、aggregated、smoothed。 |
| `missing_value_flag` | 用來標示此筆資料是否有缺值，方便 Rule Service 避免誤判。 |

### 加入原因總結

如果 DataPreprocess 已經對資料做補值、平滑或去雜訊，但沒有留下標記，後續 service 會不知道資料是原始值還是處理後的值。  
這會影響異常判斷與 event trigger 的可信度。

---

## 六、Derived Features / 統計特徵欄位

這類欄位是由原始 sensor data 計算出的特徵，可用來支援更穩定的 Rule 判斷。  
例如不是只看某一秒是否超標，而是看一段時間內是否持續異常。

| 欄位 | 為什麼要加入 |
|---|---|
| `rolling_avg` | 用來表示一段時間內的移動平均，可降低瞬間雜訊造成的誤判。 |
| `rolling_std` | 用來表示一段時間內的波動程度，可判斷製程是否不穩定。 |
| `max_value` | 用來記錄時間窗內最大值，方便判斷是否曾經超標。 |
| `min_value` | 用來記錄時間窗內最小值，方便判斷是否低於下限。 |
| `change_rate` | 用來表示數值變化速度，例如壓力突然下降或溫度快速上升。 |
| `duration_over_threshold` | 用來記錄超過 threshold 的持續時間，避免短暫尖峰造成誤判。 |
| `anomaly_score` | 用來表示異常程度分數，可作為後續 risk_level 或 diagnosis 的參考。 |

### 加入原因總結

很多製程異常不是看單一時間點，而是看趨勢、持續時間或波動。  
若 DataPreprocess 能提供 derived features，Rule Service 可以更容易判斷真異常，而不是只判斷瞬間數值。

---

## 七、Station / Sensor 對應表欄位

這類欄位用來確認每個 station 有哪些 sensor，每個 sensor 對應哪個欄位與設備。  
這對 ontology 對接非常重要。

| 欄位 | 為什麼要加入 |
|---|---|
| `station` | 用來指定站別，例如 `Station_1`、`Station_2`、`Station_3`。 |
| `sensor_name` | 用來定義 sensor 名稱，避免每個檔案使用不同名稱。 |
| `field_name` | 用來指定資料表中的欄位名稱，例如 `air_pressure_bar`。 |
| `unit` | 用來確認欄位單位，避免同一欄位在不同資料中單位不一致。 |
| `asset` | 用來對應實體設備，例如 FilterMesh、AirCompressor、Nozzle、RobotArm。 |
| `sampling_rate_hz` | 用來記錄 sensor 採樣頻率，例如 1Hz，方便 TimeSeriesService 使用。 |

### 加入原因總結

若沒有 station-sensor-field 對應表，ontology 不知道哪個 sensor 屬於哪一站、哪個設備，也不知道資料欄位代表哪個實體訊號。  
這會造成 Database、Service、Ontology 命名無法對齊。

---

## 八、輸出格式確認欄位

這類欄位不是機台資料本身，而是用來確認 DataPreprocess 最後如何交付資料。  
這會影響 DB 匯入、API 測試與資料版本管理。

| 欄位 | 為什麼要加入 |
|---|---|
| `output_format` | 用來確認輸出是 CSV、JSON，還是直接寫入 DB。 |
| `file_name` | 用來確認輸出檔案命名規則，方便後續自動讀檔。 |
| `timestamp_format` | 用來統一時間格式，避免 DB / API 解析錯誤。 |
| `timezone` | 用來確認時區，避免不同來源資料時間對不上。 |
| `batch_id_format` | 用來統一 batch_id 格式，方便跨表關聯。 |
| `station_format` | 用來統一 station 格式，例如固定用 `Station_1`。 |
| `missing_value_format` | 用來確認缺值表示方式，例如空白、null、NaN、-999。 |

### 加入原因總結

即使欄位內容正確，如果輸出格式、timestamp、missing value 表示方式不一致，後續 DB 匯入與 API 串接仍然會出錯。  
因此需要先確認 DataPreprocess 的最終輸出格式。

---

## 九、塗料黏度欄位處理

| 欄位 | 處理方式 | 為什麼 |
|---|---|---|
| `paint_viscosity` | 不放入即時輸入；若要保留，標成 manual_measurement / pending。 | 林聖堯補充現場塗料黏度是人工量測，不是 sensor 自動輸入，因此不適合放入 `sensor_1hz` 或 TimeSeriesInput。 |

---

## 十、最終整理：需要林聖堯補或確認的欄位分類

```text
1. Batch 時間區間
- batch_id
- station
- batch_start_time
- batch_end_time
- completed_at

2. 品質 / 預測結果
- ok_count
- ng_count
- predicted_ok_rate
- predicted_ng_count
- quality_score
- defect_type
- defect_code
- risk_level

3. Threshold / 判斷基準
- sensor_name
- station
- normal_min
- normal_max
- warning_min
- warning_max
- alarm_min
- alarm_max
- unit
- threshold_source

4. Event / Alert 紀錄
- event_id
- event_time
- station
- event_type
- severity
- source_signal
- source_value
- trigger_rule_id
- message
- acknowledged_status

5. DataPreprocess 狀態
- data_quality_flag
- is_interpolated
- is_outlier
- preprocess_method
- missing_value_flag

6. Derived Features / 統計特徵
- rolling_avg
- rolling_std
- max_value
- min_value
- change_rate
- duration_over_threshold
- anomaly_score

7. Station / Sensor 對應表
- station
- sensor_name
- field_name
- unit
- asset
- sampling_rate_hz

8. 輸出格式確認
- output_format
- file_name
- timestamp_format
- timezone
- batch_id_format
- station_format
- missing_value_format
```

---

## 十一、簡短結論

目前林聖堯提供的欄位足以支援初步 sensor 異常判斷。  
但若要讓 DataPreprocess 後續順利接上 Database、Ontology、API、Service、EventRule 與 Dashboard，仍需要補或確認上述欄位。

其中最優先的是：

```text
batch_start_time / batch_end_time
station-sensor-field 對應表
threshold 格式
data_quality_flag
event source_signal / source_value
最終輸出格式
```
