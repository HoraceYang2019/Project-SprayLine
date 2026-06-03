<!--
0531 狀態註記：
此檔案屬於早期 Past / Current Service reference。
目前 sample_method 採用 TimeSeriesService 0531 規則：
past = mean、current = recent_average、future = latest_valid。
若本檔與 0531 規則衝突，以 README_0531_status.md 與 webservices/time_series_service 為準。
-->

# Past / Current Service 全一致命名規則

本版不再使用對應表，而是要求 Past / Current Service 直接使用 Statistics Service 正式命名。

## 統一命名規則

### 站別
- 使用 `stations[]`
- 使用 `line_id`
- 使用 `station_name_zh`
- 使用 `station_name_en`

### 狀態
- 使用 `state`
- 建議值：`Running`、`Standby`、`Stop`、`Maintenance`、`Alarm`

### 指標
所有站別指標放入：

```json
"metrics": {
 "pressure_bar": "<number>",
 "flow_rate_ml_min": "<number>",
 "quality_score_pct": "<number>",
 "availability_pct": "<number|null>",
 "clog_rate_pct": "<number|null>",
 "maintainability_pct": "<number|null>",
 "risk_text": "<string|null>"
}
```

### 製程參數
所有製程參數放入：

```json
"process_parameters": {
 "temperature_c": "<number>",
 "utilization_pct": "<number>",
 "cycle_time_sec": "<number>"
}
```

## 不再使用的舊命名

- `machines`
- `machine_id`
- `process_name`
- `para`
- `Qc`
- `Ut`
- `cycle_time`

## 注意

`flow_rate_ml_min` 欄位名稱與 / UI 對齊。實際資料寫入前，上游需確認或換算為 ml/min。
