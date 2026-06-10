# 0604 余宇承補充：event rule 與命名一致

余宇承補充兩點：

```text
1. 觸發記錄 event 的 rule 規則要放在 ontology
2. 命名規則要相同
```

## 本版處理方式

- 新增 `EventRule`、`TriggerRule`、`RuleCondition`、`RuleAction`、`AlertEvent`。
- 將 event table 對齊為 `alert_event`。
- 將 threshold table 對齊為 `sensor_threshold`。
- 將 station 命名對齊為 `Station_1 / Station_2 / Station_3`。
- 保留正式規則為 pending，不產生假 rule output。
