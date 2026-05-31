# Past / Current Service 正式命名版

這一版不是用 mapping table 轉接，而是直接把沈同學 Past / Current Service 的 input/output 欄位改成 統一命名。

## 檔案

- `past_current_service_io__full_naming.ipynb`
- `_full_naming_rules.md`

## 主要改動

1. `machines` 改為 `stations`
2. `machine_id` 改為 `line_id`
3. `process_name` 改為 `station_name_zh`
4. 新增 `station_name_en`
5. `Qc` 改為 `metrics.quality_score_pct`
6. `Ut` 改為 `process_parameters.utilization_pct`
7. `para` 拆進 `metrics` 與 `process_parameters`
8. `cycle_time` 改為 `process_parameters.cycle_time_sec`
9. `色漆` 統一改為 `面漆站 / Topcoat Station`
10. 狀態命名改成 UI / 使用的 `Running`、`Maintenance` 等

## 定位

Past / Current Service 現在可以直接作為 Statistics Service 的上游輸入，不再需要額外對應表。
