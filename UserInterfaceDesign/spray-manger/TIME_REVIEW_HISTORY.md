# Time Review / Problem Hour Marker

This UI version adds an hour selector for manager review.

## Purpose

When an abnormal condition appears in one hour and disappears in the next hour, the manager still needs to go back to the problem hour, identify what happened, and ask the station owner to inspect it.

## Behavior

- The date selector controls which production date is being viewed.
- The time selector controls which hour of that date is being viewed.
- `跟隨最新 Current` keeps the dashboard following the newest simulated API upload.
- Selecting a fixed hour switches the dashboard into review mode.
- Hours with detected problems are marked with `!` in the time dropdown.
- When an hour is selected, Past / Current / Future is recalculated using that selected hour as Current.
- Diagnosis and responsibility assignment are recalculated from that hour's saved API-shaped data.

## Current mock / simulated API mode

Hourly snapshots are stored in browser `localStorage` under:

- `spray_manager_hourly_snapshots_v1`

Daily archives are stored under:

- `spray_manager_daily_archive_v1`

When connected to the real backend later, replace this frontend history store with DB queries by date and hour.

Recommended API shape later:

```text
GET /api/v1/lines/{line_id}/stations/latest?date=YYYY-MM-DD&hour=HH
GET /api/v1/lines/{line_id}/diagnosis/latest?date=YYYY-MM-DD&hour=HH
GET /api/v1/lines/{line_id}/charts/quality-trend?date=YYYY-MM-DD
GET /api/v1/lines/{line_id}/charts/utilization-trend?date=YYYY-MM-DD
GET /api/v1/lines/{line_id}/charts/cycle-time-trend?date=YYYY-MM-DD
```

## 2026-06-09 update: problem-hour dropdown display

- Removed the `Past` text from each hour option to keep the dropdown cleaner.
- Problem hours are now displayed with a light red blinking background instead of a text exclamation marker.
- The selected problem hour also blinks in the closed dropdown state, so the manager can immediately see that the reviewed hour had an issue.

## 2026-06-09 修正：目前模擬日不再固定跳回 6/9

前一版只有每日 archive 與 hourly snapshots 存在 localStorage，但 `SIMULATED_API_DAY_INDEX` / `SIMULATED_API_UPLOAD_INDEX` 是 JavaScript 記憶體變數。重新整理頁面後，這兩個變數會回到初始值，所以畫面可能出現「6/10、6/11 已封存，但目前模擬日仍停在 6/9」的不一致。

本版新增 `spray_manager_simulated_api_state_v1`，會保存 activeDate、dayIndex、uploadIndex、currentHour。頁面重新載入時會先讀取這個狀態；若 daily archive 中已有比目前模擬日更新的日期，系統會自動從最新封存日的下一天繼續跑。

## 品質分數顯示規則補充

時間回顧模式中，若選的是目前模擬日，該小時品質分數仍是預測值，標示為「預測品質分數」。若選的是已封存並完成 QC 的日期，則標示為「實際品質分數」。每一小時品質分數代表該小時所有 batch 的平均值。

## 2026-06-09 修正：隔天實際品質不可沿用當天預測

當天畫面上的品質分數是 `ml_prediction_result` 或模型輸出的預測品質分數。日期完成後，隔天回顧品質時，UI 不應直接使用前一天封存的預測品質分數。

本版改成：

- 當天 / 目前模擬日：顯示「預測品質分數」，來源視為 prediction API。
- 已封存 / 隔天回顧日：顯示「實際品質分數」，來源視為 DB 的 `qc_result`。
- 每小時品質分數仍代表該小時所有 batch 的平均值。
- daily archive 與 hourly snapshot 在回顧模式會轉成 actual QC data mode，避免主管誤把預測結果當成實績。

未來接真 DB 時，回顧日期應使用類似：

```text
GET /api/v1/lines/{line_id}/charts/quality-trend?date=YYYY-MM-DD&quality_type=actual
GET /api/v1/lines/{line_id}/qc/hourly-quality?date=YYYY-MM-DD&hour=HH
```

也就是從 `qc_result` 查實際品質，而不是讀取當天 prediction snapshot。

## 2026-06-09 修正：已封存日期回顧不再因版本升級消失

前一版把 localStorage key 從 v2 升到 v3，導致舊的已封存日期仍在瀏覽器裡，但新程式只讀 v3，所以日期下拉選單只剩目前模擬日。

本版會同時讀取並遷移以下舊資料：

- `spray_manager_daily_archive_v2` / `v1`
- `spray_manager_hourly_snapshots_v2` / `v1`
- `spray_manager_simulated_api_state_v2` / `v1`

新資料仍寫入 v3，但舊封存日會重新出現在「資料日期」下拉選單中。
