# Service Extension Ontology

本資料夾放 service_extension 的 ontology extension，不覆蓋老師原本的：

```text
SprayLine_3/ontology/SprayLine_ontology.ttl
```

目前主要檔案：

```text
SprayLine_service_extension.ttl
```

設計原則：

1. 中英文 label 放在同一份 TTL 中。
2. `line_id` 作為 Database / Function 對接識別欄位。
3. Past / Current / Future 以 Function 架構保留概念。
4. AirCompressor 已作為目前空壓機元件名稱 / 空壓機。
5. UI_v3 新增 SprayWidth / 噴幅與 SprayWidthImage / 噴幅影像。
6. 新增 Baking / Oven 製程後段概念與前後製程單向影響關係。
7. Runtime observation 與 inferred output 不手寫假資料。
