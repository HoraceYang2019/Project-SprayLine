# UI_v4 Schema Alignment Notes

UI_v4 已取代原本的 UI_v4 reference。此資料夾的 UI_v4 仍為模擬資料版本，但命名與資料結構已往本專案 schema 對齊。

## 已修正

- `line_1 / line_2 / line_3` 改為 `line_1 / line_2 / line_3`
- `lineId` 改為 `lineId`
- station data 內補入 schema-aligned 欄位：
  - `line_id`
  - `metrics`
  - `process_parameters`
  - `component_metrics`
  - `spray_width_image`

## 尚未完成

- UI_v4 尚未實際串接 schema / service output。
- 目前仍是模擬資料，但資料欄位已與 TimeSeriesService / schema 方向對齊。
