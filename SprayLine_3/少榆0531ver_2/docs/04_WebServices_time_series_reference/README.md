# WebServices TimeSeriesService Reference

本資料夾納入 `Project-SprayLine-main_0531/WebServices/time_series_service` 的新 TimeSeriesService 內容，並已套用本專案命名規則。

## 已套用命名規則

- 舊產線代號改為 `line_1`、`line_2`、`line_3`
- `flow_rate_ml_min` / `flow_rate_ml_min` 統一為 `flow_rate_ml_min`
- `pressure_bar` / `pressure_bar` 統一為 `pressure_bar`
- `service_name` / `request_id` 統一為 `service_name` / `request_id`
- `line_scope` 統一為 `line_scope`

## sample_method 規則

- `past`：數值欄位採 `mean`
- `current`：數值欄位採 `recent_average`
- `future`：數值欄位採 `latest_valid`

## 計算公式狀態

本資料夾中的公式已納入 service / schema / ontology 註記，作為 0531 版 TimeSeriesService 的計算規則。  
Rule Service、threshold、warning / alarm 判定仍保持 pending，不在此 service 中寫死。
