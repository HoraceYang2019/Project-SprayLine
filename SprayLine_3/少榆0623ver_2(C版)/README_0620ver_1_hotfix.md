# 0620ver_1 hotfix 說明

本版以 `Project-SprayLine0620.zip/final_version` 為基礎，只保留 final_version 執行需要的檔案，移除 `.git`、`__pycache__`、舊版工作檔與截圖。

## 本版修正重點

1. **不切換到 DB threshold 作為 API 直接判斷來源**
   - 為避免臨時改 rule engine 導致 UI/API 流程中斷，本版維持既有流程：API / UI 仍讀 `rules/sensor_thresholds.json` 與 `ui/engineer/config/sensor_thresholds.json`。
   - 但已將兩份 JSON threshold 調整到與最終版生成資料一致，避免正常資料被誤判。

2. **修正聖堯提出的空壓機與噴幅誤判**
   - `air_pressure_bar`：改成全域安全範圍 `normal 2.7~3.8`、`warning 2.5~2.7 / 3.8~4.0`、`fault <2.5 / >4.0`。
   - `spray_width_mm`：三站基準不同（約 120 / 100 / 82），本版先用全域安全範圍 `normal 70~130`，避免 Station_2 / Station_3 被舊的 105~125 誤判。
   - 後續若時間允許，可再改成 station-specific threshold。

3. **補 Quality 膜厚資料來源**
   - `dataprocess/dataprocess.py` 現在會產生並寫入 `film_thickness_um`。
   - 清洗 interpolated 資料時也會沿用上一筆有效膜厚，避免持續寫入 NULL。

4. **修 Quality / trend-data 資料轉換**
   - `ui/engineer/app/services/api_data_service.py` 修正 `trend_points()` 解析方式。
   - 原本 station-detail 回傳的是 `time_series.points`，不是 `time_series[metric]`；本版會正確轉成 UI trend chart 需要的 `{timestamp, value}`。
   - 若 station-detail 沒有 points，會 fallback 呼叫 component-detail。

5. **修 component-detail 接口相容性**
   - `api/time-series/ui/component-detail` 現在可接受：
     - `component_name`
     - `component_key`
     - `component_id`
   - 已建立 alias：`FILTER/filter/filter_mesh`、`QUALITY/quality/quality_module` 等。
   - 缺欄位時回 422 JSON，不直接丟 500。

6. **補 summary/station-detail 可用的六個 component 數值**
   - `api/shaoyu_ui_bridge.py` 的 station card 現在會附上六個 component 的基本 value/unit/status，讓 UI 小卡比較容易取得資料。

7. **補 DB catalog hotfix**
   - `database/setup_db.sql` 最後新增 0620ver_1 hotfix seed：
     - 缺漏 cause：`FLOW_IMBALANCE`、`NOZZLE_ANGLE_DRIFT`、`SPRAY_WIDTH_DEVIATION`、`SPRAY_WIDTH_UNSTABLE`、`FILM_THICKNESS_OOC`、`FILM_THICKNESS_VARIATION`
     - 缺漏 response：`CHECK_FILTER`、`CHECK_SERVO`、`INSPECT_NOZZLE`、`REDUCE_SPEED`、`ADJUST_FILM_THICKNESS`
     - 補 cause_response_map
     - 補 DB sensor_threshold 的 fault_lo/fault_hi

## 已驗證

- `python -m compileall api services database dataprocess ui/engineer tests` 通過。
- `pytest -q` 通過：`1 passed`。

## 還沒做的大改

1. 尚未把 API rule engine 改成直接讀 DB `sensor_threshold`，因為這會影響判斷流程，容易在期末前造成 UI/API 斷線。
2. 尚未完整補 `Threshold CSV -> TTL -> Rule -> Service`，這應放到報告或下一版正式 ontology 補強。
3. 尚未完整移除 demo fallback，只做不影響展示的 hotfix。
