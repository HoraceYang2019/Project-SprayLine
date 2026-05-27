# 本次 service_extension 整理摘要

## 來源

使用新上傳的：

```text
期中後0527ver.zip
```

## 主要建立內容

建立：

```text
SprayLine_3/service_extension/
```

並依老師 SprayLine_3 pipeline 分為：

```text
ontology/
knowledge/
runtime/
rules/
output/
schema/
templates/
csv_templates/
docs/
```

## 主要轉換

1. `station_id` 改為 `line_id`。
2. `Pump` / `pump_status` / `幫浦` 改為 `AirCompressor` / `air_compressor_status` / `空壓機`。
3. 新增 UI_v3 的 `SprayWidth` / `SprayWidthImage` 對應欄位。
4. 中英文 ontology 合併為單一 TTL：`ontology/SprayLine_service_extension.ttl`。
5. 新增 Function / ServiceFunction / PastFunction / CurrentFunction / FutureFunction 結構。
6. 新增 Baking / Oven / BakingResult 與前後製程單向影響關係。
7. 修正 runtime TTL template，使其可被 Turtle parser 解析。
8. 建立 CSV templates，作為未來人工維護主檔的雛形。
9. rules 與 inferred output 不造假，只建立 pending README。
10. `01_Past_Current_Service` 作為主線參考，`01-1` 僅作參考資料。
