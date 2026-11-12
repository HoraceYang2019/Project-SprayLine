# rules 說明（少榆0628 runtime）

正式 runtime 規則來源：

```text
ontology/runtime_threshold_reference.csv
    -> ontology/threshold_to_ttl.py
    -> ontology/sprayline_threshold.ttl
    -> ontology/rule_inference.py
```

API EventRule、Integrated Service 與 Monitoring Worker 都透過：

```text
services/event_rule_service/runtime_rule_classifier.py
```

讀取 TTL，判斷：

```text
normal / warning / fault
```

## sensor_thresholds.json

保留為 runtime fallback。只有 TTL 缺少 metric 或讀取失敗時才使用，回傳中的 `rule_engine` 會標為 `json_threshold_fallback`。

## sensor_event_mapping.json

保留作 DB 欄位與 catalog 相容 mapping：

```text
issue_state / fault_state
cause_id
response_ids
state_field
response_field
component_id
```

TTL 內的 `cause_id` / `response_ids` 已與這份 mapping 及 `database/setup_db.sql` 對齊；ID 命名仍須由余宇承做最終確認。
