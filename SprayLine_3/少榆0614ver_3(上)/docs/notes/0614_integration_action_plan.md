# 0614 Integration Action Plan

本版修正為 `0614ver_3`，重新釐清少榆主責：  
少榆不負責正式 API Server，而是負責 Future 預測、Monitoring / Timer、EventRule、Troubleshooting 與 Ontology / Knowledge 對應。

## 正式方向

```text
DataPreprocess
→ 余宇承 DB/API
→ sensor_1min / sensor_3min
→ 少榆 MonitoringWorker / FutureService
→ alert_event / batch_station_status / future_prediction_result payload
→ 余宇承 DB/API 回寫資料庫
→ Manager UI / Engineer UI 顯示
```

## 少榆負責

1. `FutureService`  
   產生 `predicted_ok_rate`、`predicted_ng_count`、`quality_score`、`risk_level` 與 `future_prediction_result` payload。

2. `MonitoringWorker`  
   作為 Timer / EventRule 整合邏輯，讀取 `sensor_1min` / `sensor_3min`，判斷 `state`，產生 `alert_event` 與 `batch_station_status` 更新需求。

3. `TroubleshootingService`  
   根據 `state` 查詢 possible cause / countermeasure，主要供 Engineer UI 顯示完整細節。

4. Ontology / Knowledge  
   描述 `SensorSignal -> Threshold -> State -> AlertEvent -> Cause -> Countermeasure -> UI / Service` 的關係。

5. 需求文件  
   整理給余宇承的 DB/API 需求，例如 `future_prediction_result` table、sensor 查詢 API、alert_event 寫入 API。

## 少榆不負責

```text
正式 API Server
FastAPI / uvicorn 後端
Database insert / query endpoint
Manager UI / Engineer UI 前端實作
```

## 尚待余宇承更新

```text
future_prediction_result table
insert / query future_prediction_result API
query sensor_1min / sensor_3min API
insert alert_event API
upsert batch_station_status API
data_quality_flag 是否加入正式 sensor_1min / sensor_3min SQL
```

## 下次展示目標

```text
1. 林聖堯產生一筆異常資料。
2. 資料經 DB/API 寫入 sensor_1min 或 sensor_3min。
3. 少榆 MonitoringWorker 偵測到異常。
4. threshold_evaluator 判斷 state。
5. 產生 alert_event payload。
6. 透過 DB/API 回寫 alert_event。
7. Engineer UI 顯示完整 state / possible cause / countermeasure。
8. Manager UI 顯示簡潔風險摘要。
```
