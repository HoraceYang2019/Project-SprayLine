# 少榆0616ver_4 快速上手

這份檔案是給你打開新版後最快知道要看哪裡、怎麼實測。

## 1. 這包放在哪裡

```text
Project-SprayLine-main/
└─ SprayLine_3/
   └─ 少榆0616ver_4/
```

本版建議不要再拆成上 / 下包。

## 2. 先看哪幾個檔案

```text
README.md
README_快速上手.md
0616ver_4_修改報告.md
docs/validation/0616ver_4_AnyDesk_PostgreSQL_DB實測流程.md
docs/validation/0610老師逐字稿要求對照表.md
```

## 3. 主程式看哪幾個

```text
webservices/integration_adapter/database_versionb_adapter.py
webservices/future_service/future_service.py
webservices/monitoring_worker/monitoring_worker.py
webservices/monitoring_worker/threshold_evaluator.py
webservices/monitoring_worker/detection_mapping.py
webservices/monitoring_worker/duplicate_alert_guard.py
webservices/monitoring_worker/alert_event_writer.py
webservices/monitoring_worker/batch_station_status_writer.py
webservices/event_rule_service/event_rule_service.py
```

## 4. 規則檔

```text
rules/sensor_thresholds.json
```

用途：判斷 sensor 數值是 normal / warning / fault。

```text
rules/sensor_event_mapping.json
```

用途：把 sensor 對到 issue_state、cause_id、response_ids、batch_station_status 欄位。

## 5. 先跑不需要 DB 的檢查

```bash
python -m webservices.integration_adapter.database_versionb_adapter
python -m webservices.future_service.future_service
```

## 6. 在余宇承電腦上 DB 實測

先用 AnyDesk 連到遠端電腦，然後在遠端 PowerShell 設定：

```powershell
$env:SPRAYLINE_PROJECT_ROOT="C:\path\to\Project-SprayLine-main"
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_USER="postgres"
$env:DB_PASSWORD="請填余宇承提供的 PostgreSQL 密碼"
$env:DB_NAME="sprayline"
```

接著：

```powershell
python scripts\check_db_connection.py
python scripts\run_db_smoke_test.py
```

若可以寫測試資料：

```powershell
python scripts\run_db_smoke_test.py --write-test-data --station Station_1
```

完整步驟：

```text
docs/validation/0616ver_4_AnyDesk_PostgreSQL_DB實測流程.md
```

## 7. 0616ver_4 新增的安全機制

```text
SPRAYLINE_DUPLICATE_ALERT_SUPPRESSION_MINUTES=5
```

同一 batch / station / sensor / state / cause 在 5 分鐘內已有未確認 alert 時，不重複寫入 alert_event。

## 8. 你不用改 UI

你負責的是 Future / Monitoring / EventRule / Troubleshooting / Database 整合。UI 同學可以參考：

```text
docs/contracts/manager_engineer_ui_db_function_map.md
```

## 9. 目前不要亂動

```text
不要修改 Database/versionB schema。
不要刪 sensor_threshold table。
不要刪 data_quality_flag 的 outlier。
不要改 WebServices/time_series_service_B。
不要把遠端連線密碼寫進檔案。
```
