# 0623ver_2 Runtime 與 Reference 資料夾分工

## Runtime 主流程會用到

```text
api/
database/
dataprocess/
rules/
services/
ui/
config/knowledge/troubleshooting_matrix_reference.csv
ontology/threshold_reference.csv
ontology/threshold_to_ttl.py
ontology/rule_inference.py
```

## Reference / 報告 / 溯源使用

```text
csv_templates/
knowledge/
docs/0617_B_reference/
schema/
templates/
service_reference_0617_B/
database_versionB_reference_0617_B/
ontology/0617_B_modular_reference/
```

## 為什麼不把所有歷史 CSV 都塞進來？

前一版「含全部CSV」是為了救回全部資料，但會造成最後版本太混亂。  
0623ver_2 改成保留 0617_B 之後少榆端必要的核心資料，包含 API/DB/service contract、future prediction、integrated service、monitoring、troubleshooting、knowledge 與 schema。
