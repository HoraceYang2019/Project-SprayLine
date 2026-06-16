# Past / Current / Future 整合說明（0616ver_5）

## 定位

本版新增 `IntegratedSprayLineService`，目標是把 past / current 的 time-series 資料取得，
接到少榆端既有的 Future / Monitoring / Alert / DB 回寫流程。

## 整合原則

```text
past/current 資料取得：Database/versionB sensor_1min / sensor_3min
time slider 概念：slider_value < 0 past，= 0 current，> 0 future
current snapshot：由最近 window 內最新 sensor_1min + sensor_3min 合併
past window：由指定 slider anchor 往前 window_minutes 查詢
UI time-series 格式：IntegratedSprayLineService.build_ui_time_series_response()
DB 回寫：仍走 Database/versionB db_alert / db_status / db_future
```

## 不做的事

```text
不把 WebServices/time_series_service_B 的 runtime JSON 當正式 persistence。
不改成 HTTP endpoint。
不改 Database/versionB schema。
不改 Manager / Engineer UI 前端。
```
