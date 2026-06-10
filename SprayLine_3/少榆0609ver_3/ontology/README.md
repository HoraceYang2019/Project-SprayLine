# Ontology 模組說明

本資料夾將 ontology 拆成模組，不將所有內容放在同一個 TTL。

## 模組劃分

- `SprayLine_ontology_index.ttl`：總索引，匯入各模組。
- `core/SprayLine_core_ontology.ttl`：產線、站點、設備、感測訊號等核心概念。
- `database/SprayLine_database_ontology.ttl`：DB Schema v3 的 table / view 與資料來源關係。
- `service/SprayLine_service_ontology.ttl`：Service、API endpoint、response schema 的關係。
- `dashboard/SprayLine_dashboard_ontology.ttl`：Dashboard / UI 區塊與資料呈現關係。
- `event_rule/SprayLine_event_rule_ontology.ttl`：EventRule、TriggerRule、alert_event 與門檻參考關係。
- `troubleshooting/SprayLine_troubleshooting_ontology.ttl`：原因對策概念模型。
- `knowledge/SprayLine_troubleshooting_knowledge.ttl`：具體候選原因對策知識。
- `knowledge/SprayLine_threshold_reference_knowledge.ttl`：DataPreprocess 提供的門檻參考值。

## 注意

`rdfs:range` 是 ontology property 的值域，不是數值判斷區間。
實際數值門檻放在 `knowledge/SprayLine_threshold_reference_knowledge.ttl` 與 `docs/contracts/data_preprocess_threshold_reference.csv`。
