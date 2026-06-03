# Ontology Visual Graph / Hardware Flow Check

本版針對 `0602ver_3` 的 Protégé / OntoGraf 顯示問題做完整修正。

## 修正原因

`0602ver_3` 已經有 class hierarchy，因此左側 Classes 樹狀階層可以看到：

```text
PhysicalAsset
├─ RobotArm
├─ Nozzle
├─ AirCompressor
├─ FilterMesh
├─ QualityModule
└─ Oven
```

但是 OntoGraf 主要會顯示「物件屬性關係」與「個體鄰近關係」。  
因此如果只有 `rdfs:subClassOf`，在 OntoGraf 中選到 `PhysicalAsset` 時，不一定能像舊版一樣展開硬體到異常、警示、資料表、Dashboard 元件的關聯。

## 本版新增的關係

### 1. 類別層的視覺化關係

新增 class-level visualization links，例如：

```text
PhysicalAsset hasAssetClass RobotArm
PhysicalAsset hasAssetClass Nozzle
PhysicalAsset hasAssetClass AirCompressor
PhysicalAsset hasAssetClass FilterMesh
PhysicalAsset hasAssetClass QualityModule
PhysicalAsset hasAssetClass Oven
PhysicalAsset monitorsMetric SprayWidth
```

並加入 component 到資料表 / 閾值 / 診斷 / 警示的關係：

```text
Nozzle usesThresholdTable NozzleThresholdTable
FilterMesh usesThresholdTable FilterThresholdTable
AirCompressor usesThresholdTable ProcessThresholdTable
SprayWidth usesThresholdTable ProcessThresholdTable
Nozzle producesDiagnosis DiagnosisResult
FilterMesh mayTriggerAlert AlertLog
```

### 2. 產線實體資產個體

每條產線都有自己的資產個體：

```text
Line1RobotArm
Line1AirCompressor
Line1FilterMesh
Line1Nozzle
Line1SprayWidth
Line1QualityModule
Line1Oven
```

`Line2` 與 `Line3` 也有同樣結構。

這些個體會連到：

```text
ProductionLine
Runtime / DB table
Threshold table
Diagnosis result
Alert log
Service function
Dashboard component
Possible issue
```

### 3. 前後製程方向

新增上游 / 下游方向：

```text
AirCompressor upstreamOf Nozzle
FilterMesh upstreamOf Nozzle
Nozzle upstreamOf SprayWidth
SprayWidth upstreamOf QualityModule
QualityModule upstreamOf Oven
```

以及單向影響：

```text
FilterMesh affectsDownstream Oven
AirCompressor affectsDownstream Oven
Nozzle affectsDownstream Oven
SprayWidth affectsDownstream Oven
Oven affectedBy FilterMesh / AirCompressor / Nozzle / SprayWidth
```

這樣可以表達你先前強調的方向：

> 濾網問題可能影響最後烤箱結果，但烤箱結果不會反過來影響濾網。

### 4. 可能異常與警示狀態

新增 `PossibleIssue` 類別與可能異常個體，例如：

```text
FilterCloggingIssue
FilterFlowLossIssue
NozzleCloggingIssue
PressureAbnormalIssue
SprayWidthOutOfRangeIssue
QualityRiskIssue
OvenResultRiskIssue
```

資產個體會透過：

```text
hasPossibleIssue
mayTriggerAlert
producesDiagnosis
```

連到可能異常、警示與診斷資料。

## Protégé 使用建議

如果要看階層：

```text
Classes → PhysicalAsset
```

如果要看關係圖：

```text
OntoGraf → 選 Line1FilterMesh / FilterMesh / Nozzle / PhysicalAsset / DashboardV15
```

展開後應能看到：

```text
硬體資產
→ Runtime / Threshold / Diagnosis / Alert
→ Service Function
→ Dashboard Component
→ 下游製程影響
```

## 本版檢查重點

- `Nozzle subClassOf PhysicalAsset`
- `FilterMesh subClassOf PhysicalAsset`
- `AirCompressor subClassOf PhysicalAsset`
- `RobotArm subClassOf PhysicalAsset`
- `Oven subClassOf PhysicalAsset`
- `SprayWidth subClassOf Metric`
- `Line1FilterMesh affectsDownstream Line1Oven`
- `Line1Oven affectedBy Line1FilterMesh`
- `Line1Nozzle hasPossibleIssue NozzleCloggingIssue`
- `Line1FilterMesh mayTriggerAlert AlertLogTable`
