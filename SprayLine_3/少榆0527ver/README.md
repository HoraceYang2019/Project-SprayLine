# SprayLine_3/service_extension

此資料夾是依據目前 `期中後0527ver.zip` 重新整理出的 service extension 架構。  
它不覆蓋老師原本的 `SprayLine_3` 架構，而是在 `SprayLine_3` 下額外建立同樣分層概念的 extension。

## 資料夾定位

```text
ontology/       ontology extension：class、property、function、UI_v3、source mapping、process relation
knowledge/      threshold / expert knowledge / rule basis，目前仍是 template / pending
runtime/        runtime TTL template；沒有放假 runtime observation
rules/          rule pending；尚未建立正式 rules
output/         inferred output pending；不手寫假資料
schema/         JSON Schema / API Contract draft
templates/      JSON template draft
csv_templates/  老師要求的 CSV template，人工作業維護用
docs/           來源參考、UI_v3 reference、field catalog、待定事項與對應表
```

## 本次已套用的確定方向

- `station_id` 改為 `line_id`。
- Pump 改為 AirCompressor / 空壓機。
- UI_v3 新增 SprayWidth / 噴幅與 SprayWidthImage / 噴幅影像。
- Past / Current / Future 以 Function / ServiceFunction 架構保留概念。
- 中英文 label 合併在同一份 TTL。
- Runtime / output 不造假資料。
- rules 暫時只保留 pending，等 Past / Current、Database、threshold 與 Future Service 進一步確認後再建立。
- `01_Past_Current_Service` 作為目前主線參考；`01-1_補強版_加入噴漆三大類` 僅作參考。
