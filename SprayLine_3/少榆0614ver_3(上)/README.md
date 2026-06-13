# 少榆0614ver_3

本版修正 `0614ver_2` 中容易造成分工誤解的部分：移除正式 `api_server.py` 與相關 API Server 啟動說明。  
少榆端主軸改回：

```text
Future 預測 Service
Timer / Monitoring Worker
EventRule 判斷
Alert / Prediction payload
Troubleshooting 原因對策
Ontology / Knowledge 對應
與余宇承 DB/API 的介面需求整理
```

## 本版重點

```text
1. sensor_1hz 已取消，只使用 sensor_1min / sensor_3min。
2. 移除正式 api_server.py，不再把完整 API Server 放在少榆主責內。
3. 保留 FutureService：產生 predicted_ok_rate / predicted_ng_count / quality_score / risk_level payload。
4. 保留 MonitoringWorker：作為 Timer / EventRule 整合邏輯。
5. 原因對策對外使用 state，不再以 issue_type 作為主要介面名稱。
6. Manager UI 看摘要；Engineer UI 看完整 state / cause / countermeasure。
7. Future prediction result 採方案 A：請 DB/API 端補 future_prediction_result table。
8. 新增使用說明與開啟檔案執行流程。
```

## 建議先看檔案

```text
docs/使用說明_開啟檔案與執行流程.md
docs/notes/0614_integration_action_plan.md
docs/contracts/api_requirements_for_yucheng_0614.csv
docs/contracts/database_requested_changes_0614.sql
docs/contracts/future_prediction_table_request.csv
webservices/future_service/future_service.py
webservices/monitoring_worker/monitoring_worker.py
webservices/troubleshooting_service/troubleshooting_service.py
ontology/SprayLine_ontology_index.ttl
```

## 執行方式摘要

```bash
cd 少榆0614ver_3
pip install -r webservices/requirements.txt
python -m webservices.future_service.future_service
python -m webservices.monitoring_worker.monitoring_worker
```

## Pending

```text
1. future_prediction_result table 尚待 DB/API 端正式加入。
2. data_quality_flag 是否加入 sensor_1min / sensor_3min 正式 SQL 尚待 DB/API 端確認。
3. 正式 DB query / insert API 由余宇承端提供後，再把少榆端 worker 的本機 DB adapter 改成 API client。
```
