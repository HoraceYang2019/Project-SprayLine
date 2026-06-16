# Database/versionB SETUP GUIDE（少榆0616ver_3 對齊版）

本檔是少榆0616ver_3 隨包附上的 `Database/versionB` reference copy 使用說明。
正式整合時，建議優先使用 GitHub 專案根目錄的：

```text
Project-SprayLine-main/Database/versionB/
```

本版文件路徑統一使用 `Database/versionB`。

## 1. 本資料夾定位

`Database/versionB` 目前提供少榆端可直接 import 的 DB function：

```text
db_connection.py
db_sensor.py
db_alert.py
db_status.py
db_future.py
db_knowledge.py
db_batch.py
db_composite.py
sprayline_db_queries.py
```

少榆端 0616ver_3 的主流程預設分別 import：

```text
db_sensor.query_sensor_1min / query_sensor_3min
db_alert.insert_alert_event / link_alert_cause / link_alert_response
db_status.get_batch_station_status / upsert_batch_station_status
db_future.insert_future_prediction_result / get_future_prediction_summary
```

`sprayline_db_queries.py` 目前視為可確認的整合入口候選；是否改成唯一入口，待余宇承確認。

## 2. 安裝與 DB 連線環境變數

需要 PostgreSQL 可連線，並設定：

```text
DB_HOST
DB_PORT
DB_USER
DB_PASSWORD
DB_NAME
```

PowerShell 範例：

```powershell
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_USER="postgres"
$env:DB_PASSWORD="你的密碼"
$env:DB_NAME="sprayline"
```

## 3. 建立資料表

在 `Project-SprayLine-main/Database/versionB` 執行：

```bash
python setup_db.py
```

或手動用 psql：

```bash
psql -U postgres -d sprayline -f setup_db.sql
```

## 4. 少榆端 import path 設定

如果從 `SprayLine_3/少榆0616ver_3` 執行，adapter 會依序尋找：

```text
1. SPRAYLINE_DB_FUNCTION_PATH
2. SPRAYLINE_PROJECT_ROOT/Database/versionB
3. 少榆0616ver_3/external/Database/versionB
4. 從目前檔案往上找 Database/versionB
```

建議設定 GitHub 專案根目錄：

```powershell
$env:SPRAYLINE_PROJECT_ROOT="C:\path\to\Project-SprayLine-main"
```

或直接指定：

```powershell
$env:SPRAYLINE_DB_FUNCTION_PATH="C:\path\to\Project-SprayLine-main\Database\versionB"
```

## 5. 重要待確認

```text
1. data_quality_flag 是否最終只保留 normal / interpolated，或保留 outlier。
2. sensor_threshold table 是 DB 端保留備用，還是未來移除。
3. alert_event.cause 最終正式語意是否固定為 cause_catalog.cause_id。
4. 少榆端是否改以 sprayline_db_queries.py 作為唯一整合入口。
```

0616ver_3 不新增 HTTP 對外路由，不新增 FastAPI / API server。
