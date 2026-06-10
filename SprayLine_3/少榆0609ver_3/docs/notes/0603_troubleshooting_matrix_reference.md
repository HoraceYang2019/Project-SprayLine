# 0603 Troubleshooting Matrix 參考方向

本文件整理前期討論中提到的 troubleshooting matrix 方向。

本專案不直接採用 CNC 內容，而是將其「故障現象、可能原因、觀測訊號、受影響設備、候選處置」的矩陣概念轉換為噴塗產線使用。

目前定位：

```text
Troubleshooting matrix = 原因對策候選知識來源
TroubleshootingService = 查詢原因對策的服務
EventRuleService = 判斷是否觸發 alert_event
Ontology = 描述設備、訊號、事件、原因、對策之間的語意關係
```

所有原因對策目前皆維持 `candidate_pending_confirmation`，不視為正式規則輸出。
