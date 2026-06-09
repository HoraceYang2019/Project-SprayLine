# Simulated API validation mode

This Manager UI is configured to behave as if it is connected to the Project-SprayLine API, while still generating mock API/schema-shaped responses in the frontend.

## Purpose

Use this mode to verify three things before the real backend is connected:

1. Different API uploads change the dashboard data.
2. The recommended decision changes when the abnormal station changes.
3. The 24-hour charts correctly move Past / Current / Future as the current API time advances.

## Current configuration

In `dashboard.js`:

```js
USE_MOCK_DATA: false,
SIMULATED_API_ENABLED: true,
API_BASE_URL: "http://127.0.0.1:5000",
API_USE_PROJECT_SCHEMA: true,
SIMULATED_API_START_HOUR: 10,
SIMULATED_API_UPLOAD_INTERVAL_MS: 5000
```

No real API is called while `SIMULATED_API_ENABLED` is `true`. The UI calls the same internal data-normalization path as the real Project-SprayLine schema, but the responses are generated locally.

## Simulated upload sequence

| API upload time | Simulated situation | Expected decision |
|---|---|---|
| 10:20 | Second station / color layer nozzle-clog and spray-width issue | Notify second station engineer first |
| 11:20 | Second station improves but still under observation | Continue tracking second station |
| 12:20 | Third station / protection layer filter-feed issue | Decision changes to third station engineer |
| 13:20 | Third station worsens | Escalate third station issue |
| 14:20 | First station / base layer spray width too low | Decision changes to first station engineer |
| 15:20+ | All stations return to acceptable range | Diagnosis section hides automatically |

## Past / Current / Future logic

If current API time is 10:20:

- Past = 00:00-09:00
- Current = 10:00
- Future = 11:00-24:00

If the next API upload advances to 11:20:

- Past = 00:00-10:00
- Current = 11:00
- Future = 12:00-24:00

The same logic applies to quality score, utilization, and cycle time charts.

## Switch to real API later

When the real backend is ready:

```js
SIMULATED_API_ENABLED: false,
USE_MOCK_DATA: false,
API_BASE_URL: "http://your-backend-host:port"
```

Then the UI will call the Project-SprayLine endpoints defined in `CONFIG`.

## 日期封存與跨日模擬

本版本新增日期資料生命週期：

1. 模擬 API 從 `CONFIG.SIMULATED_API_START_DATE` 的 00:00 開始，每次 upload 前進 1 小時。
2. 當 23:00 完成後，系統會把當天完整 00:00-23:00 的 Manager DB response 存到 `localStorage`。
3. 下一筆 upload 會自動切到隔天 00:00，例如 2026-06-08 完成後切到 2026-06-09 00:00。
4. 上方「資料日期」下拉選單會顯示目前模擬日與已封存日期，可用來回顧前一天的資料。
5. 若使用者選擇已封存日期，畫面會顯示該日期的歷史資料；若選擇目前模擬日，則持續顯示即時模擬資料。

未來接真實 API 時，日期會透過 API query string 傳入，例如：

```text
/api/v1/lines/{line_id}/charts/quality-trend?date=2026-06-08&timestep=hour
/api/v1/lines/{line_id}/kpi?date=2026-06-08
/api/v1/lines/{line_id}/prediction-accuracy?date=2026-06-08
```

Manager UI 的日期邏輯是：當天資料負責 current / future 預測與即時決策；已完成日期負責歷史回顧與模型驗證。
