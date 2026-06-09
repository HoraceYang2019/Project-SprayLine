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
