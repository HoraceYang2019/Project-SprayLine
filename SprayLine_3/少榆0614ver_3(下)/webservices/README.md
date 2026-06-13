# WebServices

本資料夾放「少榆端」的 service logic，不包含正式 API Server。

## 少榆主責範圍

```text
future_service
→ 產生 Future prediction payload 與 risk_level

monitoring_worker
→ Timer / Monitoring 邏輯，讀 sensor_1min / sensor_3min 並產生 alert_event / batch_station_status 更新需求

event_rule_service
→ 根據 sensor_threshold 判斷 state，建立 alert_event payload / 本機測試寫入

troubleshooting_service
→ 根據 state 查 possible cause / countermeasure，供 Engineer UI 顯示詳細內容
```

## 不在少榆主責範圍

```text
正式 API Server
FastAPI / uvicorn 後端
Database insert / query endpoint
Manager / Engineer UI 實作
```

正式 API / DB function 由 Database / DB API 負責人提供。少榆端只整理需求與 payload 格式。

## 安裝本機測試套件

```bash
pip install -r webservices/requirements.txt
```

## 執行 Future payload demo

```bash
python -m webservices.future_service.future_service
```

## 手動執行一次 Monitoring Worker

```bash
python -m webservices.monitoring_worker.monitoring_worker
```

> Monitoring Worker 需要可連線的本機 DB 或整合測試 DB；正式整合時可改接余宇承提供的 API client。
