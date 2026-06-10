# 少榆0609ver_3

本版以 `0609ver_2` 為基礎，進一步補強 DataPreprocess 門檻數值、ontology 關聯與展示可讀性。

## 本版重點

1. 新增 DataPreprocess threshold reference。
2. 將林聖堯提供的門檻數值整理成 CSV、JSON template 與 ontology knowledge。
3. EventRule 與 SensorThresholdReference 建立關聯。
4. 檢查所有 ontology TTL 的語法、上下級與主要關聯。
5. 減少不必要的 空白佔位；未確認資料改用 pending 狀態。
6. 文件與狀態標籤不使用 特定來源稱呼 字樣，改用中性來源與狀態。

## 林聖堯門檻數值位置

CSV / 表格：

```text
docs/contracts/data_preprocess_threshold_reference.csv
csv_templates/sensor_threshold_template.csv
```

JSON：

```text
templates/sensor_threshold.template.json
schema/sensor_threshold.schema.json
```

Ontology：

```text
ontology/knowledge/SprayLine_threshold_reference_knowledge.ttl
ontology/event_rule/SprayLine_event_rule_ontology.ttl
ontology/database/SprayLine_database_ontology.ttl
```

## Ontology 檢查報告

```text
docs/validation/0609ver_3_ontology檢查報告.md
```
