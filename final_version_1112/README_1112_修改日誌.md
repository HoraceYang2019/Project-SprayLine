# final_version_1112 修改日誌

修改日期：2026-11-12
基底版本：`final_version_0718_v3`，即 Project-SprayLine GitHub commit `65fbd43` 時的內容
API 版本：`1112.1`

本版本以 0718_v3 為基底，只新增少榆負責的告警歷程查詢 API。資料庫 schema 與 migration、Knowledge 規則、Future、Monitoring、Manager UI、Engineer UI 與 DataProcess 都沒有修改。0718_v3 保持原樣，作為修改前版本的紀錄。

## 新增：告警歷程查詢 API

依 2026-11-11 會議需求，新增三個唯讀端點。外部 AI 代理與工程師畫面可依時間範圍、問題類型查詢過去的異常。

| 端點 | 用途 |
| --- | --- |
| `GET /api/alerts/history` | 逐筆列出時間範圍內的告警，可依站點、原因、指標、元件、嚴重度、是否確認篩選，附原因說明與建議處置，可分頁 |
| `GET /api/alerts/summary` | 依原因、站點、指標、嚴重度或日期分組計數，回答「某段時間出現哪幾類問題、各幾次」 |
| `GET /api/alerts/episodes` | 把同站點、同指標、同原因且間隔不超過 `gap_minutes` 的告警合併成一段異常，回報開始時間、最後一次告警、持續時間與確認情況 |

- 新增檔案：`services/alert_history_service/`、`api/alert_history_adapter.py`、`tests/test_alert_history_service.py`。
- 修改檔案：`api/api_server.py` 新增上述路由；`openapi_current.json` 已同步。既有的 `/api/alerts` 與 `database/db_alert.py` 沒有修改。
- 時間基準：告警時間是感測資料的時間。沒有給 `start`、`end` 時，預設以資料庫最新一筆告警的時間為終點，往前 `days` 天（`anchor=latest_data`），避免查歷史或模擬資料時用系統時間查不到。時區預設 `Asia/Taipei`。
- 資料庫連線以唯讀模式開啟。參數錯誤回 `422`，資料庫不可用回 `503`。
- 參數說明、完整請求與回應範例，以及給 AI 代理的呼叫指引，見 `Docs/docs/SprayLine/SL-KM_1027_v2.md` 第 7.4、7.5 節。

## 版本名稱變更

| 項目 | 0718_v3 | 1112 |
| --- | --- | --- |
| API 標題與版本 | `SprayLine API final_version_0718_v3`、`0718.3` | `SprayLine API final_version_1112`、`1112.1` |
| 回應中的 `service_name` | `SprayLine_API_0718_v3` | `SprayLine_API_1112` |
| 啟動、停止、驗證腳本 | `START_0718_v3.bat`、`STOP_0718_v3.bat`、`VERIFY_0718_v3.ps1` | `START_1112.bat`、`STOP_1112.bat`、`VERIFY_1112.ps1` |

以下名稱刻意不改：

- **migration 檔名與內容**，例如 `database/migrate_0718_v3_backend.sql`。`db-migrate` 會比對已套用檔案的檢核碼，改了會讓 API 無法啟動。
- **Docker 容器名稱**（`sprayline_api`、`sprayline_db` 等）與外部資料庫 volume `final_version_0717_sprayline_pgdata`。新版本沿用同一個資料庫。

`VERIFY_1112.ps1` 另外會檢查 API 版本與 `/api/alerts/summary` 是否有回應。

## 沒有從 0718_v3 複製的檔案

這些檔案都還留在 `final_version_0718_v3`：

| 檔案 | 原因 |
| --- | --- |
| `.env` | 內含實際連線設定與通知網址，不應再提交一份到公開的 GitHub。部署時在主機上從 0718_v3 複製；本資料夾的 `.gitignore` 已排除 `.env`。 |
| `backups/*.dump` | 兩個資料庫備份檔，合計約 45 MB |
| `api_backup_before_v16/`、`backup_before_data_anchor_patch/`、`backup_monitoring_worker_20260716_213933/`、`*.before_0718_v2` | 舊版程式備份 |
| `monitoring_*.json`、`monitoring_*.txt`、`compose_check*.txt`、`alert_code_search.txt`、`api_alert_error.txt`、`manager_dashboard_after_future_commit.json` | 先前測試的輸出紀錄 |
| `-Uri`、`python`、`sh` | 0 位元組的空檔 |
| `0718_v3_DataProcess啟停教學.ipynb` | 內容寫的是 0718_v3 的路徑與腳本名稱；1112 的操作方式相同，把路徑換成 `final_version_1112` 即可 |

## 部署步驟（在 API 主機上）

1. 在 `final_version_0718_v3` 執行 `STOP_0718_v3.bat`。這只會停止容器（`docker compose down`），不會刪除資料庫 volume。
2. 把 `final_version_0718_v3\.env` 複製到 `final_version_1112\.env`。這個檔案不要提交到 GitHub。
3. 在 `final_version_1112` 執行 `START_1112.bat`。
4. 執行 `VERIFY_1112.ps1`，確認 `/` 回傳的版本是 `1112.1`，且 `/api/alerts/summary` 有回應。

要回到 0718_v3 時，先執行 `STOP_1112.bat`，再於 0718_v3 執行 `START_0718_v3.bat`。

- **新舊兩版不能同時啟動**：兩版的容器名稱相同，請先停止一版再啟動另一版。
- **不要清空或重建資料庫**：不要執行 `docker compose down -v`、`database/setup_db.sql`，也不要刪除 `final_version_0717_sprayline_pgdata`。
- **DataProcess 只能有一套**：啟動前請確認主機上只有一套 DataProcess 在執行。

## 驗證結果

- **完整 pytest**：在本資料夾執行，61 項通過，包含 0718_v3 原有的 43 項與新增的 18 項。
- **PostgreSQL 實測**：新增測試裡的 PostgreSQL 整合測試，只在設定 `SPRAYLINE_TEST_PG_DSN` 時執行。本次用本機 PGlite（PostgreSQL 18）載入 `setup_db.sql`，再以 `db_alert.py` 既有的寫入函式建立測試告警，實測三個端點都正常。
- **還沒驗證的部分**：
  - 部署主機上的 PostgreSQL 16 與實際資料。
  - Docker 映像建置與容器啟動，因為製作這版的電腦沒有安裝 Docker。

## 跨模組待辦

- **SQL 放的位置**：查詢 SQL 放在少榆負責的 `alert_history_service`，沒有加進資料庫負責人的 `db_alert.py`。如果他希望集中管理 SQL，可以再討論搬過去。
- **Engineer UI**：異常歷程入口可以改用 `/api/alerts/episodes` 與 `/api/alerts/history`，需要 Engineer UI 負責人配合。
- **「有沒有人處理」的判斷**：目前依 `acknowledged_at` 與 `alert_response_link.executed_at`，還沒有連到 engineer task 工單狀態。
- **第七、八項**：Threshold 統一與 Future 回測尚未合併；之後合併時以本資料夾為基底。

## 2026-11-17：API 對外開放前的安全處理

API 版本號維持 `1112.1`。可用 `GET /api/routes` 回應中新增的 `api_mode` 欄位，判斷是否包含本次修改。

### 修正：`write_back` 與 `commit` 的判斷

- 原本 `POST /api/service-orchestration/integrated/query` 用 `bool()` 轉換 `write_back`，字串 `"false"` 會被當成要回寫。`POST /api/service-orchestration/future/save` 的 `commit` 也有同樣問題。
- 現在兩者只接受布林值 `true`／`false`，或字串 `"true"`／`"false"`、`"1"`／`"0"`、`"yes"`／`"no"`（不分大小寫），也接受數字 `1`／`0`。其他值回 `422`（`error_code` 為 `invalid_request`），不會執行查詢或寫入。
- 預設值不變：`write_back` 預設不回寫，`commit` 預設提交。`run-once` 仍固定回寫。

### 新增：對外唯讀入口

- 內部入口（埠 `8011`）維持原樣，給 Manager UI 與 Engineer UI 使用。Manager UI 是由瀏覽器直接呼叫 8011，其中包含工單、確認告警等寫入類端點，所以 8011 只能在內網或 VPN 內使用，不可對外開放。
- 同一份映像以 `SPRAYLINE_API_MODE=public_readonly` 啟動時，會成為對外唯讀入口。`docker-compose.yml` 新增 `api_public` 服務，對應主機埠 `8014`，放在 `public` profile。`START_1112.bat` 不會啟動它。
- 唯讀模式只保留白名單內的端點，其他端點全部移除，回 `404`，也不會出現在 `/openapi.json` 與 `/api/routes`。白名單在 `api/public_readonly.py` 的 `PUBLIC_ROUTE_ALLOWLIST`，與 `SL-KM_1027_v2.md` 第 7.5 節第 4 點一致：
  - 告警歷程三個端點、單筆告警、原因對應處置
  - 兩個 troubleshooting 查詢
  - `POST /api/time-series/ui/summary`、`station-detail`、`component-detail`，這三個在程式中固定不回寫
- `integrated/query` 雖然可以只查詢，但能回寫，所以不放進白名單。人員、工單、通知、資料庫狀態等管理端點也不放進白名單。
- 資料端點要帶 `X-API-Key` 標頭，金鑰設在主機 `.env` 的 `SPRAYLINE_PUBLIC_API_KEYS`，可用逗號設定多組。沒有設定金鑰時，唯讀模式拒絕啟動。`/`、`/health`、`/api/health`、`/api/routes`、`/openapi.json`、`/docs` 不需要金鑰。
- 修改檔案：
  - 新增 `api/public_readonly.py`、`tests/test_public_readonly.py`
  - 修改 `api/api_server.py`、`docker-compose.yml`、`.env.example`
  - 內部入口的 `openapi_current.json` 沒有變動，已重新產生後比對確認。

### 啟動與停止（在 API 主機上）

1. 在 `final_version_1112\.env` 加上 `SPRAYLINE_PUBLIC_API_KEYS=<金鑰>`。金鑰可用 `python -c "import secrets; print(secrets.token_urlsafe(32))"` 產生，不要提交到 GitHub。
2. 啟動：`docker compose --profile public up -d --build api_public`
3. 停止：`docker compose --profile public stop api_public`。`STOP_1112.bat` 執行的 `docker compose down` 沒有指定 `public` profile，可能不會停止這個容器，切換版本前請先手動停止。
4. 對外開放時，只轉發主機的 8014，不要轉發 8011、8012、8013、5433。

### 驗證結果

- **完整 pytest**：在本資料夾執行，114 項通過、1 項略過。新增 54 項，原有 60 項全部通過；略過的是需要 `SPRAYLINE_TEST_PG_DSN` 的 PostgreSQL 整合測試，本次修改不涉及。
- **本機 uvicorn 實測**（沒有資料庫）：
  - 沒有設定金鑰時，唯讀模式拒絕啟動。
  - `/health`、`/openapi.json`、`/api/routes` 回 `200`，`api_mode` 為 `public_readonly`，路由數 12。
  - 資料端點沒帶金鑰或金鑰錯誤回 `401`；金鑰正確時通過檢查，因為沒有資料庫回 `503`。
  - `run-once`、`integrated/query`、`acknowledge`、工單端點都回 `404`。
- **還沒驗證的部分**：
  - Docker 映像建置與 `api_public` 容器啟動，因為這台電腦沒有安裝 Docker。
  - 部署主機上的實際資料。
  - 對外網路轉發、HTTPS、限流都還沒有設定。

### 待辦

- 部署主機目前是 0718_v3，還沒有這次的修改，需依交接說明另外套用。
- 工程師從外網開啟工單連結（`/api/engineer-task-access/*`，會寫入）這次沒有處理，目前仍只能在內網使用。需要和 Manager UI 負責人討論。
- 對外入口目前直接使用 `postgres` 帳號。之後可以改成資料庫唯讀帳號，需要和資料庫負責人討論。

## 2026-11-17：資料庫 volume 名稱更正

- 部署主機的 `sprayline_db` 實際掛載 `final_version_0717_sprayline_pgdata`（2026-11-17 以 `docker inspect sprayline_db` 確認）。1112 原本沿用 GitHub 上 0718_v3 的設定，寫成 `final_version_0627_sprayline_pgdata`，在主機上啟動 1112 會接錯資料庫或啟動失敗。
- 已把 `docker-compose.yml`、`start.ps1`、`START_1112.bat`、`VERSION.txt` 與本日誌中的 volume 名稱改為 `final_version_0717_sprayline_pgdata`。
- 沒有修改的部分：
  - GitHub 上的 `final_version_0718_v3` 仍寫 0627，和主機上的 0718_v3 不同。0718_v3 資料夾保持原樣，作為修改前版本的紀錄。
  - 本資料夾內從舊版本帶過來的紀錄檔（`README_0718_v3_修改日誌.md`、`README_0718_v2.md`、`CHANGELOG_0718_v2.md`）記載的是當時的狀況，不修改。
- 跨模組待辦：資料庫文件 `SL-DB_*.md`、Web Service 文件 `SL-WS*.md` 仍寫 0627，需要通知各文件負責人確認。

## 2026-11-18：對外唯讀入口的網頁加上金鑰輸入

- 唯讀模式的 `/openapi.json` 宣告 `X-API-Key` 標頭金鑰（`ApiKeyHeader`）。`/docs` 網頁因此出現 **Authorize** 按鈕，輸入金鑰後按 **Try it out**／**Execute** 會自動帶上標頭。
- 只有資料端點標示需要金鑰；`/`、`/health`、`/api/health`、`/api/routes` 不需要。實際的金鑰檢查仍由原本的中介層負責，行為不變。
- 內部入口（8011）的規格不變，已重新產生後與 `openapi_current.json` 比對確認。
- 修改檔案：`api/public_readonly.py`、`tests/test_public_readonly.py`（新增 2 項測試）。完整 pytest 116 項通過、1 項略過。
- 網頁操作方式見 `SL-KM_1027_v2.md` 第 7.7 節。
- 部署主機的 8014 需要重新建置 `api_public` 才會出現這個按鈕；套用前要依當時主機狀況另外安排。
