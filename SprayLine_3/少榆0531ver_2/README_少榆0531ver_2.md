# 少榆0531ver_2

本版本以 `少榆0531ver_1` 為基準，修正第三階段前發現的七個流程缺口，並補上相對 `少榆0528ver_4` 的更改說明。

## 版本定位

`少榆0531ver_2` 是第三階段前置修正版，目標是讓 TimeSeriesService、UI_v4、Database reference、DataPreprocess、schema、CSV 與 ontology 的連動關係更清楚。

## 本版新增重點

- `docs/querydata_database_mapping.csv`
- `docs/function_service_database_mapping.csv`
- `docs/formula_required_field_source.csv`
- `docs/ui_v4_to_time_series_output_mapping.csv`
- `docs/01_Past_Current_Service_reference/README_0531_status.md`
- `相對0528ver_4更改.md`

## 本版修正重點

- 補上 TimeSeries request template 的 `schema_version`
- 修正 Past / Current 舊 reference 與 0531 sample_method 的衝突
- 補強 ontology 的 function flow 關係
- 明確標示 QueryData 尚未正式接 DB，但已定義應對接的 database functions
- 明確標示公式所需欄位的來源與 pending 狀態

## 仍不做的事

本版不產生假資料，不建立假的 runtime observation、inferred output、Rule output、Database output。
