# Rules

Dashboard v15 的元件狀態、baseline/diff、warning/alarm、risk detail 依賴：

- `filter_threshold`
- `nozzle_threshold`
- `process_threshold`
- `diagnosis_result`
- `alert_log`

本版不手寫正式 Rule output，不產生假 warning/alarm。  
正式規則需等 threshold CSV、diagnosis engine 與 database implementation 確認。
