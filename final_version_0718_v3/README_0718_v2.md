# final_version_0718_v2

這一包以使用者上傳的 `final_version_0715(3).zip` 內層最新專案為基底，
複製成新的整合區後修改；原始 0715 檔案沒有被覆寫。

## 固定資料庫

`docker-compose.yml` 已固定使用：

```text
final_version_0627_sprayline_pgdata
```

正常啟動不會執行 `db-setup`，也不會啟動 `dataprocess`，
避免重建或持續改寫同學的既有資料庫。

## 啟動

在本資料夾開啟 CMD 或 PowerShell：

```cmd
powershell -ExecutionPolicy Bypass -File ".\start.ps1" -Mode start
```

工程師 UI：

```text
http://localhost:8013
```

啟動後瀏覽器按 `Ctrl + F5`。

## 停止（保留資料）

```cmd
powershell -ExecutionPolicy Bypass -File ".\start.ps1" -Mode down
```

不要使用 `-Mode reset`、`docker compose down -v` 或 `docker volume rm`。

## 0718_v2 修正內容

1. TimeMode 的 UI 格數正確轉換成 Service API 分鐘：
   - `-6` = 過去 360 分鐘
   - `+4` = 未來 120 分鐘
2. UI 選取時間、站卡 Timestamp、趨勢圖時間改用 Service API／PostgreSQL 時間。
3. BatchMode 不再由 UI 假設每批 18 分鐘。
4. 首頁更新只呼叫 Summary + 3 個 Station Detail；Component Detail 改為點擊零件或開趨勢時才呼叫。
5. 滑桿拖動時只更新文字，放開後才查詢。
6. 趨勢缺欄位時顯示「尚無資料」，不再讓整張圖回傳 502。
7. 趨勢只顯示 Service API 原始值，不再用目前值補點、不做移動平均或平移。
8. BatchMode 查詢會先限縮最近的感測資料，再 JOIN `batch_run`，降低共享記憶體壓力。
9. PostgreSQL 容器加入 `shm_size: 512mb`。
10. 批次溫濕度若 batch_id 對不到，會讀取同站前後 3 分鐘內最近的真實 `sensor_3min`。
11. 空值顯示為 `--`，不再把 `null` 顯示成 `0`。

## 原檔備份

所有被修改的檔案旁都保留 `.before_0718_v2` 備份。

> `-Mode reset` 已在 0718_v2 中停用，避免誤刪或重建外部資料庫。

## Simple Future Prediction Service v1

This package includes a first history-based Future Service implementation.
It uses the latest 60 minutes of `sensor_1min` / `sensor_3min` data to predict
raw sensor values with `linear_trend_v1`, then reuses the existing Integrated
Service formulas and ontology rules. See `FUTURE_PREDICTION_SERVICE_V1.md`.
