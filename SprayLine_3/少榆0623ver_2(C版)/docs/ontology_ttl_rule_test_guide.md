# 0623ver_2 Ontology / TTL / Rule 推論與 Protégé 展示教學

## 一、檔案位置

```text
ontology/threshold_reference.csv       # threshold 來源檔
ontology/threshold_to_ttl.py           # CSV 轉 TTL
ontology/sprayline_threshold.ttl       # rule_inference.py 使用的 TTL
ontology/rule_inference.py             # 讀 TTL 做 normal / warning / fault 推論
ontology/sprayline_full_ontology.ttl   # Protégé 展示用完整 ontology
docs/sequence_diagram.md               # Mermaid 時序圖
```

## 二、測試 Rule 推論

在 `0623ver_2` 根目錄執行：

```powershell
python ontology\threshold_to_ttl.py --csv ontology\threshold_reference.csv --ttl ontology\sprayline_threshold.ttl
python ontology\rule_inference.py --run-smoke-test
```

重點確認：

```text
air_pressure_bar 3.2  → normal
air_pressure_bar 4.1  → fault
spray_width_mm 99     → normal
spray_width_mm 145    → fault
film_thickness_um 14.8 → normal
film_thickness_um 17.8 → fault
```

## 三、Protégé 開哪個

用 Protégé 開：

```text
ontology/sprayline_full_ontology.ttl
```

這份比較適合展示，因為它包含：

```text
SprayLineSystem
Station
Component
SensorMetric
SensorThreshold
State
Cause
ResponseAction
InferenceRule
```

架構可以講：

```text
SprayLineSystem → Station → Component → SensorMetric → SensorThreshold → State / Cause / ResponseAction
```
