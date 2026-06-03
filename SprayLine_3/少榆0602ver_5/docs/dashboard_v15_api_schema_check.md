# Dashboard v15 API / Schema 契約檢查

基準版本：`少榆0602ver_2`

本階段完成「第 2 階段：Dashboard v15 前端 reference 與 API 契約檢查」。

## 檢查主線

```text
Dashboard v15 UI component
→ /api/v1 route
→ service function
→ response schema
→ frontend render 區塊
```

## 檢查結果摘要

| 項目 | 結果 |
|---|---|
| API route 數量 | 20 |
| route 皆有 service function | OK |
| route 皆有 response schema | OK |
| schema 檔案存在 | OK |
| UI component 皆有 route/service/schema | OK |

## 本版補強內容

`docs/api_v1_routes.csv` 已從原本的 route/function 清單，補成直接可用的 API contract table，新增欄位：

```text
response_schema
ui_component
db_tables
cache_ttl_s
note
```

## 不產生假資料

本階段只補 API contract 與 schema/template，不產生 fake DB output 或 fake frontend response。
