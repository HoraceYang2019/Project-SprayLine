SprayLine V16 Service Data Anchor Patch

問題：
資料庫 sensor_1min 有資料，欄位也有值，但 UI 顯示「API 無資料」。
原因通常是 integrated service 用 Windows 目前時間查資料，但資料庫資料時間軸是 2029，
導致 current window 查不到任何 sensor_1min。

修正：
把 services/integrated_service/sprayline_integrated_service.py 改成：
1. 先查 Station_1~3 的 MAX/latest sensor_1min ts
2. 用資料庫最新 ts 當 UI 的 current anchor_time
3. 再回查最近 window_minutes

使用方式：
1. 將本資料夾內的 services_v16、database_v16、PATCH_SERVICE_DATA_ANCHOR_V16.bat 複製到 final_version 根目錄。
   final_version 根目錄就是有 docker-compose.yml、start.ps1、api、ui、services、database 的那一層。
2. 雙擊 PATCH_SERVICE_DATA_ANCHOR_V16.bat。
3. 開 http://localhost:8013，按 Ctrl+F5。

安全性：
- 不會刪除 PostgreSQL volume。
- 不會執行 setup_db.py。
- 不會重建資料表。
- 只替換 service 查詢邏輯相關 Python 檔案。
