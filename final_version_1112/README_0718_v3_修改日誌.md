# final_version_0718_v3 修改日誌

修改日期：2026-07-18  
基底檔案：`final_version_0718_v2.zip`  
基底 SHA256：`85DD47455CBD6A524A242812DE343900848B4CB765F2983065AC242ED0206CB4`

本版本只修改少榆負責的 Future、Integrated Service、Ontology Runtime 接續、DB 回寫與 API 橋接。Manager UI、Engineer UI 畫面與 DataProcess 邏輯未修改；Engineer UI 仍保留組員提供的 `UI_0718_v2` 標示。

## 啟動方式

在本資料夾執行：

```powershell
.\START_0718_v3.bat
```

或：

```powershell
powershell -ExecutionPolicy Bypass -File ".\start.ps1" -Mode start
```

啟動順序為 PostgreSQL → 非破壞性 migration → API → Manager UI／Engineer UI。正常啟動不執行會 DROP TABLE 的 `database/setup_db.sql`，也不啟動 DataProcess。

## 六項主要修改

### 1. 自動套用 DB migration

- 新增 `database/migrate_schema.py`：以 advisory lock、檔名與 SHA256 紀錄 migration，重啟時已套用的檔案會跳過。
- 新增 `database/migrate_0718_v3_backend.sql`：加入 Future 的 Ontology、語意與冪等欄位。
- `docker-compose.yml` 新增 `db-migrate`，API 只會在 migration 成功後啟動。
- 保留外部 volume `final_version_0627_sprayline_pgdata`，不重建現有資料庫。

### 2. 錯誤時回傳正確 HTTP 狀態

- `api/service_orchestration_adapter.py` 將輸入、DB 連線、資料衝突與 schema 錯誤分類。
- `api/api_server.py` 依分類回傳 `422`、`409`、`503`、`504` 或 `500`，不再以 HTTP 200 包裝失敗結果。
- traceback 只留在 API container log，不放入瀏覽器 JSON。

### 3. Future 加入 Cause／Response

- `services/integrated_service/sprayline_integrated_service.py` 對預測後的 metric 再呼叫 TTL Ontology Runtime。
- Future payload 新增 `rule_evaluations`、`cause_ids`、`response_ids`、`rule_sources`、`ontology_runtime`。
- `database/db_future.py` 將上述判斷結果寫入 `future_prediction_result` JSONB 欄位。
- 正式規則來源仍是 `ontology/sprayline_threshold.ttl`；只有 TTL 無該 metric 或載入失敗才使用 JSON fallback。

### 4. 更新舊版本名稱

- API title、health、routes 與 UI bridge 輸出的 service name 改為 `final_version_0718_v3`／`SprayLine_API_0718_v3`。
- API version 改為 `0718.3`。
- 啟動、停止與驗證入口改為 `START_0718_v3.bat`、`STOP_0718_v3.bat`、`VERIFY_0718_v3.ps1`。
- 歷史 V2 說明檔保留作版本來源追溯，不代表目前 runtime 名稱。
- `requirements.txt` 補上 `tzdata`，確保 Windows／精簡容器可載入 `Asia/Taipei`。

### 5. 修正品質分數語意

- `quality_score`／`quality_score_pct` 明確定義為「製程品質分數」，不是實際量測良品率。
- `predicted_ok_rate` 僅保留為舊 UI/API 相容欄位，新增 `predicted_ok_rate_semantics` 說明它是 proxy。
- `estimated_defect_rate_pct` 定義為估計製程異常風險，不宣稱為實際產品不良率。
- Future risk 判斷以製程品質分數及估計異常數計算。

### 6. 防止重複寫入

- `database/db_future.py` 以 batch、station、prediction_time、prediction_method 產生穩定 `idempotency_key`。
- `future_prediction_result` 對 `idempotency_key` 建立唯一索引，重送相同預測時改為 UPDATE 並回傳原本的 `prediction_id`。
- migration 若發現舊資料已有相同預測，只保留最新一筆後建立唯一索引。
- `batch_station_status` 原本已有 `(batch_id, station_id)` upsert；Monitoring 告警原本已有近期未確認告警抑制，因此未重複改寫這兩條流程。

## 主要驗證位置

- 健康狀態：`http://localhost:8011/`
- Swagger：`http://localhost:8011/docs`
- DB 狀態：`http://localhost:8011/api/database/status`
- Service 狀態：`http://localhost:8011/api/service-orchestration/status`
- 寫回測試：Swagger 的 `POST /api/service-orchestration/integrated/run-once`
- Migration／欄位檢查：執行 `VERIFY_0718_v3.ps1`

## 本次封裝驗證結果

- `python -m compileall`：通過。
- 完整 pytest：`43 passed`。
- V3 專屬測試已涵蓋 TTL Future Cause／Response、品質語意、冪等鍵、HTTP `422`／`503` 與 migration 契約。
- `docker-compose.yml` 已以 YAML parser 驗證，API 的 `db-migrate: service_completed_successfully` 相依關係成立，外部 DB volume 名稱未改。
- 本次製作電腦沒有 Docker CLI，因此未在本機 PostgreSQL 實際執行 migration；部署到 API 電腦後，必須執行 `START_0718_v3.bat` 與 `VERIFY_0718_v3.ps1` 完成最後驗證。

## 安全事項

- 本版本預設連接既有 `sprayline` 資料庫；若資料庫根本不存在，migration 會失敗並阻止 API 啟動，不會自動建立或清空資料庫。
- 不要在現有資料庫執行 `database/setup_db.sql`、`docker compose down -v` 或刪除 `final_version_0627_sprayline_pgdata`。
- `linear_trend_v1` 保留不變；本版本沒有更換成 ML 模型。
