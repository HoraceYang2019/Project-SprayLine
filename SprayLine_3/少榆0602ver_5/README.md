# 少榆0602ver_5

本版以 `少榆0602ver_4` 為基準，修正 Protégé Classes 左側無法展開到具體 line_1 / line_2 / line_3 節點的問題。

## 本版修正重點

`0602ver_4` 已經能在 OntoGraf 看到前後關係，但具體資產只作為 individual 存在，因此在 Protégé 左側 Classes 不會出現在 `FilterMesh`、`Nozzle`、`Oven` 等 class 底下。

本版將具體資產同時宣告為 class 與 individual：

```text
Line1FilterMesh
Line2FilterMesh
Line3FilterMesh
```

因此可以在 Classes 中看到：

```text
實體資產
└─ 濾網
   ├─ line_1／濾網
   ├─ line_2／濾網
   └─ line_3／濾網
```

## 同步處理

除了實體資產，也同步讓以下 ontology 節點可在 Classes 中展開：

- `ProductionLine`
- `UIComponent`
- `ServiceFunction`
- `DatabaseTable`
- `ThresholdTable`
- `Hypertable`
- `RESTEndpoint`
- `ResponseSchema`
- `PossibleIssue`
- `DatabaseZone`

## 保留 0602ver_4 的關係

本版保留硬體資產到以下項目的連結：

- runtime tables
- threshold tables
- diagnosis result
- alert log
- service function
- dashboard component
- possible issues
- upstream / downstream process relation

## 檢查報告

```text
docs/0602ver_5完整檢查報告.txt
docs/ontology_class_expansion_fix.md
```
