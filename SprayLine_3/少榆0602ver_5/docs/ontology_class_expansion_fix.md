# Ontology Class Expansion Fix

本版修正 `0602ver_4` 中「OntoGraf 已有關聯，但 Protégé Classes 左側無法再展開到具體 line_1 / line_2 / line_3 節點」的問題。

## 問題說明

`0602ver_4` 已經建立了：

```text
Line1FilterMesh
Line2FilterMesh
Line3FilterMesh
```

這些是具體資產個體，因此在 OntoGraf 裡可以看到關聯。  
但是 Protégé 左側 `Classes` 只會顯示 `owl:Class` 階層，不會把個體放到類別下面。  
所以你會看到：

```text
PhysicalAsset
└─ FilterMesh
```

但 `FilterMesh` 左邊沒有 + 可以展開成 `line_1／濾網`、`line_2／濾網`、`line_3／濾網`。

## 修正方式

本版將所有需要在 Classes 左側展開的具體節點，同時宣告為：

```text
owl:Class
rdfs:subClassOf 上層類別
owl:NamedIndividual
```

也就是 OWL punning 的方式。

這樣同一個節點可以同時：

1. 在 Protégé Classes 中作為 class/subclass 顯示。
2. 在 OntoGraf 中保留個體關聯與 object-property neighborhood。

## 實體資產展開結果

本版新增 / 補強：

```text
RobotArm
├─ line_1／機械手臂
├─ line_2／機械手臂
└─ line_3／機械手臂

AirCompressor
├─ line_1／空壓機
├─ line_2／空壓機
└─ line_3／空壓機

FilterMesh
├─ line_1／濾網
├─ line_2／濾網
└─ line_3／濾網

Nozzle
├─ line_1／噴嘴
├─ line_2／噴嘴
└─ line_3／噴嘴

SprayWidth
├─ line_1／噴幅
├─ line_2／噴幅
└─ line_3／噴幅

QualityModule
├─ line_1／品質模組
├─ line_2／品質模組
└─ line_3／品質模組

Oven
├─ line_1／烤箱
├─ line_2／烤箱
└─ line_3／烤箱
```

## 其他同步修正

不只實體資產，本版也讓下列類別能在 Classes 左側繼續展開：

```text
ProductionLine → line_1 / line_2 / line_3
UIComponent → 具體 UI 元件
ServiceFunction → 具體 service function
DatabaseTable → 具體資料表
ThresholdTable → filter_threshold / nozzle_threshold / process_threshold
Hypertable → runtime_window / arm_telemetry_raw
RESTEndpoint → 具體 /api/v1 endpoint
ResponseSchema → 具體 schema
PossibleIssue → 具體異常
DatabaseZone → 具體 DB zone
```

## 檢查方式

在 Protégé 左側 Classes 中可檢查：

```text
實體資產 → 濾網 → line_1／濾網
實體資產 → 噴嘴 → line_1／噴嘴
實體資產 → 烤箱 → line_1／烤箱
服務功能 → DiagnosisService → get_latest_diagnosis
資料庫概念 → DatabaseTable → diagnosis_result
資料資源 → ResponseSchema → diagnosis_latest.schema.json
```

在 OntoGraf 中可點：

```text
line_1／濾網
line_1／噴嘴
line_1／烤箱
```

應仍可看到：

```text
runtime / threshold / diagnosis / alert / service / dashboard / downstream effect
```
