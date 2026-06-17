# GitHub 0616 20:00 WebServices 更新檢查（少榆0616ver_4）

## 檢查結論

0616 20:00 GitHub 包新增 / 更新的重點主要在：

```text
WebServices/time_series_service_B/
```

該資料夾比較像 TimeSeries / UI demo service，內含 FastAPI endpoint、runtime JSON demo、payload demo。它不是少榆0616ver_4 的正式 DB 寫回路線。

## 與少榆端是否衝突

少榆0616ver_4 正式路線：

```text
直接 import Database/versionB Python function
不走 HTTP endpoint
不新增 FastAPI / api_server.py
alert_event / batch_station_status / future_prediction_result 寫回 DB
```

`WebServices/time_series_service_B` 目前仍可能包含：

```text
api_server.py
HTTP endpoint
persistence_status
pending_db_api
runtime json demo
```

這些屬於另一位同學的 WebServices / UI demo 線，不應直接套用到少榆正式 service。

## 少榆端處理方式

```text
1. 不修改 WebServices/time_series_service_B。
2. 不把該資料夾的 pending_db_api / demo json 狀態搬回少榆0616ver_4。
3. 若 UI 同學要接少榆資料，請參考 docs/contracts/manager_engineer_ui_db_function_map.md。
4. 若 time_series_service_B 需要少榆 alert / future 結果，應從 Database/versionB 查詢，而不是讀少榆 runtime demo json。
```
