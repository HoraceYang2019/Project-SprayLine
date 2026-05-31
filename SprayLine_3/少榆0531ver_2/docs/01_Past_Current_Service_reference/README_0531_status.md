# Past / Current Service 0531 Status

本資料夾保留早期 Past / Current Service 設計參考，但目前正式採用的 time-series 規則，已改以 `WebServices/time_series_service` 的 0531 整合版本為準。

## 目前採用規則

| time_type | sample_method |
|---|---|
| past | mean |
| current | recent_average |
| future | latest_valid |

## 狀態說明

早期文件中若出現「Past sample_method 尚未確定」或「Current sample_method 尚未確定」，現在應改讀為：

> 舊版參考階段曾未定；目前 `少榆0531ver_2` 採用 TimeSeriesService 0531 規則作為目前版本。

## 仍需確認

以下項目仍未正式定案：

1. Current window_size 的最終定義。
2. QueryData 正式 DB 連線。
3. Rule Service 如何產生 state、risk_text、fault_detail、component_overview。
4. threshold 實際數值。
5. Future Service 模型與預測資料來源。

## 相關正式參考

- `webservices/time_series_service/`
- `docs/04_WebServices_time_series_reference/`
- `knowledge/time_series_sample_method_formula.template.json`
- `docs/function_service_database_mapping.csv`
- `docs/querydata_database_mapping.csv`
