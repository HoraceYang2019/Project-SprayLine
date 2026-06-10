# 0609ver_3 Ontology 檢查報告

檢查項目：TTL 語法可解析、class 上下級關係、NamedIndividual、ObjectProperty 連結、跨檔案引用。

## 檢查結果摘要

- TTL parse：OK
- 檢查範圍：`ontology/` 底下所有 `.ttl`
- 已新增：`ontology/knowledge/SprayLine_threshold_reference_knowledge.ttl`
- 已補強：EventRule 對 sensor threshold reference 的連結。

## 各 ontology 檔案統計

| 檔案 | parse | classes | named individuals | subClassOf | object properties | object assertions |
|---|---:|---:|---:|---:|---:|---:|
| `ontology/SprayLine_ontology_index.ttl` | OK | 0 | 0 | 0 | 0 | 0 |
| `ontology/core/SprayLine_core_ontology.ttl` | OK | 63 | 35 | 62 | 11 | 0 |
| `ontology/dashboard/SprayLine_dashboard_ontology.ttl` | OK | 8 | 4 | 7 | 3 | 0 |
| `ontology/database/SprayLine_database_ontology.ttl` | OK | 22 | 16 | 21 | 5 | 0 |
| `ontology/event_rule/SprayLine_event_rule_ontology.ttl` | OK | 8 | 8 | 7 | 7 | 0 |
| `ontology/knowledge/SprayLine_threshold_reference_knowledge.ttl` | OK | 2 | 13 | 2 | 2 | 0 |
| `ontology/knowledge/SprayLine_troubleshooting_knowledge.ttl` | OK | 3 | 15 | 0 | 4 | 0 |
| `ontology/service/SprayLine_service_ontology.ttl` | OK | 41 | 33 | 38 | 5 | 0 |
| `ontology/troubleshooting/SprayLine_troubleshooting_ontology.ttl` | OK | 7 | 0 | 6 | 4 | 0 |

## 跨檔案引用檢查

以下資源被引用但在合併圖中沒有找到主體定義，需後續確認：

- `film_thickness_um`
- `gearbox_temperature_c`
- `vibration_g`

## OntoGraf 使用提醒

部分 class 是概念分類節點，本身不一定會有下一層 individual。
本版已補強主要展示路徑：

```text
SensorSignal → SensorThresholdReference → EventRule → alert_event
FaultSymptom → FaultCause → CandidateResponse
RESTEndpoint → ServiceFunction → DatabaseTable / ResponseSchema
```

若單獨開某一個模組看到引用節點較少，可改開 `SprayLine_ontology_index.ttl` 或同時載入 `ontology/` 下所有 TTL。
