# 少榆0528ver_4 README

本壓縮包為目前 `service_extension` 專案整理後的工作版本。  
此版本以 `少榆0527ver` 為基礎，完成 ontology 命名清理、CSV templates 正式化、schema / JSON template 對齊、threshold template 整理與檢查報告補強。

---

## 一、版本定位

`少榆0528ver_4` 目前定位為：

> 噴塗產線 service_extension 的整理版，用於後續與老師、Database 同學、Past / Current 同學、Future Service / Rule 設計進一步對齊。

本版本已處理：

- ontology / Protégé 顯示命名
- line 命名規則
- 中文 / 英文 TTL 分離
- Controller / 控制器移除
- CSV templates 可維護化
- schema / template 對齊 CSV
- threshold template pending 化
- runtime / rules / output pending 化

---

## 二、資料夾結構

```text
少榆0528ver_4/
├─ csv_templates/
├─ docs/
├─ knowledge/
├─ ontology/
├─ output/
├─ rules/
├─ runtime/
├─ schema/
├─ templates/
├─ README_少榆0528ver_4.md
└─ README / 版本說明文件
```

---

## 三、各資料夾用途

### `ontology/`

放 service_extension ontology。

主要檔案：

```text
SprayLine_service_extension.ttl
SprayLine_service_extension_chinese.ttl
SprayLine_service_extension_english.ttl
```

用途：

- 定義 service / function / UI / database / source mapping / process relation 相關 ontology。
- 供 Protégé / OntoGraf 查看 class、individual、object property 關係。
- 中文與英文分開，避免顯示混雜。

目前規則：

- line 欄位值使用 `line_1`、`line_2`、`line_3`
- ontology IRI local name 使用 `Line1`、`Line2`、`Line3`
- 不再使用 `M1`、`M2`、`M3`
- 不再建立獨立 `Controller / 控制器` 節點

---

### `csv_templates/`

放人工維護主檔。

主要檔案：

```text
dashboard_snapshot_template.csv
function_io_template.csv
template_2hour.csv
template_10batch.csv
threshold_config_template.csv
time_series_output_template.csv
time_series_query_template.csv
```

用途：

- 作為 schema / JSON template 的欄位維護主檔。
- 比 JSON 更適合人工檢查、討論與對照。
- 後續若老師或組員要調欄位，建議優先討論 CSV。

---

### `schema/`

放 JSON Schema / API contract。

主要檔案：

```text
dashboard_snapshot.schema.json
stat_service.schema.json
time_series_query.schema.json
time_series_output.schema.json
```

用途：

- 定義 service input / output 的資料契約。
- 與 `csv_templates/` 對齊。
- 後續若要做程式驗證，可用 schema 檢查 JSON output。

---

### `templates/`

放 JSON template。

主要檔案：

```text
dashboard_snapshot.template.json
time_series_query.template.json
time_series_output.template.json
template_2hour.json
template_10batch.json
```

用途：

- 作為 service output / UI data structure 的範本。
- 目前全部是 placeholder，不是真實資料。
- 不可直接視為 runtime observation。

---

### `knowledge/`

放 threshold / expert knowledge / rule basis 的暫時模板。

主要檔案：

```text
threshold_config.template.json
threshold_config_notes.md
README_knowledge_pending.md
```

用途：

- 紀錄 threshold 設計方向。
- 保留 pending 狀態。
- 不填正式門檻假數值。

目前狀態：

- `normal_rule`：`<to_be_confirmed>`
- `warning_rule`：`<to_be_confirmed>`
- `alarm_rule`：`<to_be_confirmed>`
- `is_finalized`：`false`

---

### `runtime/`

放 runtime TTL template。

主要檔案：

```text
statistics_service_output.template.ttl
statistics_service_output_chinese.template.ttl
statistics_service_output_english.template.ttl
README_runtime_pending.md
```

用途：

- 保留 runtime layer 的結構。
- 未來由 service output / database output 轉成 runtime observation TTL。

目前狀態：

- 仍是 template。
- 不含真實 runtime observation。
- 不含假資料。

---

### `rules/`

放 rule pending 說明。

目前狀態：

- 不建立正式 `.rq` rules。
- 不寫死 warning / alarm rule。
- 待 Past / Current、Database、Future Service 與 threshold 全部確認後再補。

---

### `output/`

放 inferred output pending 說明。

目前狀態：

- 不建立假 inferred output。
- 不手寫 `SprayLine_runtime_inferred_sparql.ttl`。
- 未來應由 runtime observation + rules 實際推論產生。

---

### `docs/`

放參考文件、修改紀錄與檢查報告。

重要檔案包含：

```text
少榆0528ver_4對齊修正檢查報告.txt
少榆正式打包檢查報告.txt
line_1_line_2_line_3修改清單.txt
完整檢查報告_0528.txt
```

---

## 四、目前已完成的重點

### 1. line 命名統一

| 用途 | 命名 |
|---|---|
| JSON / Database 欄位名稱 | `line_id` |
| 欄位值 | `line_1`、`line_2`、`line_3` |
| ontology IRI local name | `Line1`、`Line2`、`Line3` |
| 中文顯示 | `line_1／濾網`、`line_2／濾網`、`line_3／濾網` |

---

### 2. AirCompressor / SprayWidth 納入

已納入 UI_v3 相關概念：

- `AirCompressor`
- `SprayWidth`
- `SprayWidthImage`
- `FaultDetail`
- `ProcessParameters`

---

### 3. CSV / Schema / Template 對齊

已對齊：

- `dashboard_snapshot`
- `time_series_query`
- `time_series_output`
- `threshold_config`
- `template_2hour`
- `template_10batch`

---

## 五、使用建議

### 若要看 ontology

使用 Protégé 開啟：

```text
ontology/SprayLine_service_extension_chinese.ttl
```

或英文版：

```text
ontology/SprayLine_service_extension_english.ttl
```

建議先看中文版，確認：

- 是否還看到舊代號
- 是否還看到 Controller / 控制器
- line 命名是否一致
- Class / Individual / Object Property 是否正常

---

### 若要檢查欄位

優先看：

```text
csv_templates/
```

其中最重要的是：

```text
function_io_template.csv
dashboard_snapshot_template.csv
time_series_query_template.csv
time_series_output_template.csv
threshold_config_template.csv
```

---

### 若要檢查資料契約

看：

```text
schema/
```

若要看範例結構，看：

```text
templates/
```

---

## 六、目前不可直接定案的項目

以下內容目前仍為 pending，不要自行寫死：

1. Future Service 預測公式或模型。
2. threshold 實際數值。
3. warning_rule / alarm_rule。
4. Past / Current Service 實際欄位。
5. Current Service 的 window_size。
6. Past / Current sample_method。
7. `flow_rate_ml_min` 實際單位。
8. quality / availability / utilization 正式公式。
9. Rule 與 Database function 的正式對接。
10. Runtime observation / inferred output 的正式產生流程。

---

## 七、目前檢查結果

本版本已檢查：

- JSON parse：OK
- CSV parse：OK
- TTL parse：OK
- 舊代號殘留：0
- 舊 AirCompressor 前身詞殘留：0
- 獨立 Controller / 控制器殘留：0

完整報告請見：

```text
docs/少榆0528ver_4對齊修正檢查報告.txt
```

---

## 八、下一階段建議

下一階段建議進入：

```text
Function / Service Flow / Database 對接規劃
```

建議從以下檔案開始：

```text
csv_templates/function_io_template.csv
```

要補強的方向包括：

- input_schema
- output_schema
- database_table_or_collection
- called_by_ui_region
- returns_to_ui_region
- uses_threshold
- uses_rule
- uses_future_model
- pending reason
