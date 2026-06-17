# Random Data Version

本版不再使用固定的 `raw_data_demo.json`。  
隨機 raw data 由：

```text
src/random_data_provider.py
```

產生。

## 為什麼這樣改？

前一版每次輸出數值都一樣，原因是讀取固定 raw data。  
本版每次呼叫都重新產生 raw data，所以：

```text
pressure_bar
flow_rate_ml_min
spray_width_mm
availability_pct
clog_rate_pct
quality_score_pct
```

等數值都會隨機變化。

## 如何讓結果固定？

在 request 加入：

```json
"random_seed": 42
```

即可重現同一組隨機資料。

## 正式整合時要改哪裡？

正式接 Database 時，修改：

```python
QueryRawDataFromDatabase()
```

將：

```python
BuildRandomRawDataset(...)
```

替換成真正的 Database 查詢即可。
