# 少榆0616ver_3 快速上手

這份檔案是給你承接新版時先看的。看完這份，再去看 `0616ver_3_修改報告.md`。

## 1. 這包放在哪裡

```text
Project-SprayLine-main/
└─ SprayLine_3/
   └─ 少榆0616ver_3/
```

`少榆0616ver_3` 是由 GitHub 1400pm 版當 base，新版不覆蓋舊的 `少榆0614ver_3(上)` / `少榆0614ver_3(下)`。

## 2. 先看哪幾個檔案

```text
README.md
README_快速上手.md
0616ver_3_修改報告.md
docs/使用說明_開啟檔案與執行流程.md
docs/notes/0616_integration_action_plan.md
```

## 3. 主流程要看哪幾個程式

```text
webservices/integration_adapter/database_versionb_adapter.py
webservices/future_service/future_service.py
webservices/monitoring_worker/monitoring_worker.py
webservices/monitoring_worker/threshold_evaluator.py
webservices/monitoring_worker/detection_mapping.py
webservices/monitoring_worker/alert_event_writer.py
webservices/monitoring_worker/batch_station_status_writer.py
webservices/event_rule_service/event_rule_service.py
```

## 4. 兩個 JSON 規則檔

```text
rules/sensor_thresholds.json
```

用途：判斷 sensor 數值是 normal / warning / fault。

```text
rules/sensor_event_mapping.json
```

用途：把 sensor 對到：

```text
issue_state / fault_state
cause_id
response_ids
batch_station_status 的 state 欄位
batch_station_status 的 response_id 欄位
```

注意：`sensor_event_mapping.json` 是 0616ver_3 的安全整合草案，cause_id / response_id 最終仍要等余宇承確認。

## 5. Database/versionB 在哪裡

正式專案根目錄有：

```text
Project-SprayLine-main/Database/versionB/
```

少榆0616ver_3 內也附一份 reference copy：

```text
少榆0616ver_3/external/Database/versionB/
```

adapter 尋找順序：

```text
1. SPRAYLINE_DB_FUNCTION_PATH
2. SPRAYLINE_PROJECT_ROOT/Database/versionB
3. 少榆0616ver_3/external/Database/versionB
4. 從目前檔案往上找 Database/versionB
```

## 6. 最小測試

不需要 DB 的測試：

```bash
python -m webservices.integration_adapter.database_versionb_adapter
python -m webservices.future_service.future_service
```

需要 PostgreSQL DB 的測試：

```bash
python -m webservices.monitoring_worker.monitoring_worker
```

DB 測試前要設定：

```text
DB_HOST
DB_PORT
DB_USER
DB_PASSWORD
DB_NAME
```

## 7. 目前不要擅自定案的地方

```text
data_quality_flag 是否保留 outlier
sensor_threshold table 是否保留備用
alert_event.cause 是否固定放 cause_id
是否改用 sprayline_db_queries.py 當唯一入口
duplicate alert suppression 是否要做
```

你現在可以先交 0616ver_3 給老師或給余宇承看整合方向；等余宇承回覆後，再針對上面幾點補 0616ver_3_final 或 0616ver_3。


## CSV 編碼提醒

本版所有 CSV 已統一為 UTF-8 with BOM（utf-8-sig），VS Code 與 Excel 直接開啟較不容易出現中文亂碼。若 Excel 仍異常，請用「資料 → 從文字/CSV」並選 `65001: Unicode (UTF-8)`。
