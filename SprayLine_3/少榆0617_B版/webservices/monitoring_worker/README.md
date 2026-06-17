# Monitoring Worker

這是少榆端的 Timer / Monitoring 邏輯，不是正式 API Server。

## 角色定位

```text
sensor_1min / sensor_3min
→ threshold_evaluator
→ state
→ alert_event payload / batch_station_status update payload
→ 透過余宇承提供的 DB/API 回寫資料庫
```

目前程式保留本機 DB adapter，方便在沒有正式 API endpoint 前做整合測試。
正式整合時，DB 寫入部分可改成呼叫余宇承提供的 API。

## 手動執行一次

```bash
python -m webservices.monitoring_worker.monitoring_worker
```

## 注意

- 本服務不處理 DataPreprocess raw data。
- 本服務不負責建立正式 API Server。
- 本服務讀取已進入 DB 的 `sensor_1min` / `sensor_3min`。
- `data_quality_flag = interpolated` 的資料預設不觸發 alert。

## 0616ver_4 duplicate alert suppression

本版新增：

```text
webservices/monitoring_worker/duplicate_alert_guard.py
```

用途：Timer 每分鐘檢查 DB 時，若同一異常尚未被確認，避免重複寫入 `alert_event`。

判斷鍵：

```text
batch_id + station_id + sensor_name + state + cause_id
```

環境變數：

```text
SPRAYLINE_DUPLICATE_ALERT_SUPPRESSION_MINUTES=5
```

設為 `0` 可停用 suppression。
