# UI_V6 噴塗產線監控系統（本機整合版）

## 這個版本是什麼

UI_V6 是以下內容的整合版本：

```text
原本 UI_V5 畫面與單一時間點檢視
＋ SprayLine_3／少榆0616_B版的站別、感測欄位、狀態門檻與事件 mapping
＋ 新增過去／現在／未來趨勢圖
－ 目前先不連 PostgreSQL
```

目前使用本機可重現的動態資料，每 15 秒更新一次。總覽卡片、零件 Detail、整站 Detail 與趨勢圖都使用同一份 current snapshot，因此不會再出現卡片數值與點開後數值不同的情況。

## 從少榆0616_B版使用的內容

- `Station_1 / Station_2 / Station_3` 對應底漆站、面漆站、金漆站。
- Past / Current / Future 時間軸概念。
- `sensor_thresholds.json` 的 normal / warning / fault 判斷規則。
- `sensor_event_mapping.json` 的 component、issue_state、cause_id、response_ids 對應。
- `time_series.points` 與 `current_snapshot` 的 UI 輸出概念。
- 正式感測欄位：
  - `servo_torque_load_pct`
  - `path_error_mm`
  - `paint_flow_ml_min`
  - `air_pressure_bar`
  - `spray_width_mm`
  - `filter_diff_pressure_bar`
  - `film_thickness_um`
  - `temperature_c`
  - `humidity_rh`

原始 GitHub 檔案沒有被修改；規則檔是複製到 UI_V6 自己的 `config/` 後使用。

## UI_V6 新增內容

- 保留原本單一時間點狀態卡。
- 每站新增「趨勢圖 TrendChart」按鈕。
- 可切換機械手臂、噴嘴、空壓機、噴幅、濾網、品質趨勢。
- 趨勢範圍：過去 6 小時、現在、未來 2 小時。
- 過去與現在使用實線，未來使用虛線。
- 正常、注意、異常點使用綠、橘、紅顏色。
- 正常門檻區間顯示為淡綠色背景。
- `main.py` 已拆小，功能分散到 routers、services、static 與 templates。

## 啟動方式

在 UI_V6 資料夾中開啟 PowerShell：

```powershell
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

瀏覽器開啟：

```text
http://127.0.0.1:8000
```

也可以雙擊：

```text
run_web.bat
```

## API

```text
GET /api/health
GET /api/dashboard-data?mode=time&slider_value=0
GET /api/station-detail?station_id=M2&mode=time&slider_value=0
GET /api/component-detail?station_id=M2&component_key=width&mode=time&slider_value=0
GET /api/trend-data?station_id=M2&component_key=width
```

## 未來接資料庫時怎麼改

前端、趨勢圖與 API 格式不需要重做。主要把：

```text
app/services/local_data_service.py
```

替換成讀取少榆 B版 `IntegratedSprayLineService` 或 PostgreSQL 的 DataService 即可。

## 注意

品質卡的狀態依 B版 `temperature_c` 與 `humidity_rh` 規則判斷；膜厚數值用於顯示趨勢。因 B版 threshold JSON 尚未提供膜厚門檻，UI_V6 趨勢圖使用 B版 future demo 的 15 µm 中心值建立本機參考帶，並在畫面註明來源。
