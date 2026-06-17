# data_quality_flag 使用方式

`data_quality_flag` 由 DataPreprocess 產生，不負責修復資料。資料補值完成後，該欄位用於標示資料品質。

使用端：
- FutureService：避免將補值資料當成原始實測值。
- EventRuleService：`interpolated` 資料預設不觸發事件。
- Dashboard：顯示資料是否經過補值。

目前 DB Schema v5 的 `sensor_1min`、`sensor_3min` 尚未包含此欄位，因此本版本將其保留在 DataPreprocess、API 與 Ontology contract，並明確標示 `not_persisted_in_schema_v5`。
