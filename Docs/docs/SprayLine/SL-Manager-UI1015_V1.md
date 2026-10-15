# SprayLine Manager UI 技術文件

> Repository: https://github.com/HoraceYang2019/Project-SprayLine  
> Parent Path: `final_version_0718_v3/`  
> Commit: `a9550494ad27d19dbd0079349fbc1cd2660d0dc1`  
> 分析日期: 2026-10-12

## 範圍與核心結論

本文件只描述 `ui/manager/` 與其直接使用的 Manager API。主 Dashboard 使用 DB-backed payload，前端驗證會拒絕 mock、web_service 或 fallback 資料。`simulated-*.js`、`project-api.js` 與 `config-and-mock-data.js` 存在於目錄，但目前未由正式頁面載入。

## 完整資料流

`PostgreSQL → Manager API／Services → Payload 驗證 → Dashboard KPI／站別／趨勢／建議 → Manager 選擇工程師 → 建立任務與通知 → 工程師 ACK／處理／回報 → Manager 歷史查詢與審核`

1. Dashboard 載入時呼叫 `loadManagerData()`；未指定日期時由 API 決定最新可用時間。
2. 前端只在日期有效時送 hour，只在日期及 hour 都有效時送 batch_id。
3. Payload 必須包含 responseMeta、三站 telemetry、各站 24 小時趨勢與 managerView。
4. Manager 可選擇正式站別工程師、Primary 與必要參與者，再建立任務。
5. 工程師透過 Token 安全頁完成 ACK、開始、回報、附件與完成提交。
6. Manager 在通知紀錄頁追蹤、重寄、改派、審核、重開與補充期間。

## 頁面邊界

- `index.html`: Manager Dashboard。
- `notification-history.html`: Manager 通知決策與任務追蹤。
- `engineer-task.html`: 工程師 Token 安全頁；僅作為 Manager 流程的交接邊界。

## Function 清冊

使用中 108 個；目前頁面未載入 66 個。

| Function | 分類 | 來源 | 職責 | 頁面 |
| --- | --- | --- | --- | --- |
| `renderCockpit()` | 啟動與 API | `dashboard.js:3` | 轉呼叫 Manager 主畫面渲染程序，作為舊命名的相容入口。 | Dashboard |
| `renderStaticHeader()` | 啟動與 API | `dashboard.js:7` | 在尚未取得資料或錯誤狀態時，仍建立 Dashboard 標題與通知紀錄連結。 | Dashboard |
| `applyManagerDatabaseResponse()` | 啟動與 API | `dashboard.js:19` | 將通過驗證的 API payload 寫入全域狀態，取出 managerView，並同步日期、小時與批次選擇。 | Dashboard |
| `captureManagerErrorDetails()` | 啟動與 API | `dashboard.js:36` | 把任意例外正規化為畫面可顯示的標題、端點、狀態、原因與缺少欄位。 | Dashboard |
| `clearManagerSections()` | 啟動與 API | `dashboard.js:53` | 清空錯誤、總覽與建議區，避免切換狀態後殘留舊資料。 | Dashboard |
| `renderManagerErrorState()` | 啟動與 API | `dashboard.js:63` | 關閉趨勢抽屜，顯示 API／資料錯誤 Banner，並移除可能誤導的舊資料。 | Dashboard |
| `renderManagerView()` | 啟動與 API | `dashboard.js:96` | 依資料是否有效，在正式 Dashboard 與錯誤畫面之間切換。 | Dashboard |
| `parseManagerPayloadResponse()` | 啟動與 API | `dashboard.js:110` | 讀取 HTTP 回應文字，解析 JSON，並將非 2xx 或格式錯誤轉為 Manager UI 錯誤。 | Dashboard |
| `isValidDateKeyForManagerRequest()` | 啟動與 API | `dashboard.js:150` | 檢查日期是否為 YYYY-MM-DD。 | Dashboard |
| `isValidHourForManagerRequest()` | 啟動與 API | `dashboard.js:154` | 檢查小時是否為 0 至 23 的整數。 | Dashboard |
| `isValidBatchIdForManagerRequest()` | 啟動與 API | `dashboard.js:160` | 檢查批次識別是否為非空字串。 | Dashboard |
| `buildManagerDashboardRequestEndpoint()` | 啟動與 API | `dashboard.js:164` | 只在日期、小時與批次通過相依驗證時加入查詢參數，建立 Dashboard API URL。 | Dashboard |
| `fetchRealtimeDataFromDB()` | 啟動與 API | `dashboard.js:191` | 呼叫 Manager Dashboard API、解析回應、附加 requestedEndpoint，並執行嚴格 payload 驗證。 | Dashboard |
| `loadManagerData()` | 啟動與 API | `dashboard.js:234` | 協調參數清理、API 讀取、狀態更新與失敗清場；成功時記錄更新時間。 | Dashboard |
| `refreshManagerDataAndRender()` | 啟動與 API | `dashboard.js:273` | 重新載入 Dashboard、重畫畫面，並非同步更新已寄送任務的 ACK 狀態。 | Dashboard |
| `startAutoDataRefresh()` | 啟動與 API | `dashboard.js:281` | 依 DB_POLL_INTERVAL_MS 啟動週期刷新；目前設定為 20 分鐘。 | Dashboard |
| `initCockpit()` | 啟動與 API | `dashboard.js:290` | 註冊日期、時段、批次、趨勢、通知、抽屜及 Escape 鍵事件。 | Dashboard |
| `request()` | 工程師交接邊界 | `engineer-task.js:4` | 工程師安全頁的 Bearer Token API client。 | 工程師安全頁 |
| `showError()` | 工程師交接邊界 | `engineer-task.js:5` | 顯示安全連結無效、過期或 API 失敗。 | 工程師安全頁 |
| `render()` | 工程師交接邊界 | `engineer-task.js:6` | 呈現工程師任務、指派人、回報、Timeline，並依 workflowStatus 控制按鈕。 | 工程師安全頁 |
| `reload()` | 工程師交接邊界 | `engineer-task.js:7` | 重新取得 Token 所代表的任務與 Timeline。 | 工程師安全頁 |
| `action()` | 工程師交接邊界 | `engineer-task.js:8` | 以 POST 執行 ACK、開始處理或完成提交，然後重畫頁面。 | 工程師安全頁 |
| `managerApiRequest()` | 啟動與 API | `main/api-client.js:1` | 共用 JSON API client；統一 Content-Type、網路錯誤、JSON 解析與 HTTP 錯誤。 | Dashboard、通知紀錄 |
| `buildLocalApiBaseUrl()` | 啟動與 API | `main/config.js:5` | 以目前頁面的 protocol／hostname 搭配指定連接埠建立 API Base URL。 | Dashboard、通知紀錄 |
| `getManagerDashboardApiUrl()` | 啟動與 API | `main/config.js:30` | 取得設定後的 Manager Dashboard API URL。 | Dashboard、通知紀錄 |
| `getEngineerTaskApiUrl()` | 啟動與 API | `main/config.js:34` | 取得工程師任務 API URL；未覆寫時由 Base URL 與預設路徑組成。 | Dashboard、通知紀錄 |
| `buildManagerUiError()` | 啟動與 API | `main/config.js:39` | 建立含 UI 額外欄位的 Error，保留端點、狀態、資料來源與修正建議。 | Dashboard、通知紀錄 |
| `normalizeManagerUiError()` | 啟動與 API | `main/config.js:61` | 將一般 Error 或非 Error 值統一轉成 Manager UI 錯誤格式。 | Dashboard、通知紀錄 |
| `readEngineerTaskCache()` | 任務與 ACK | `main/engineer-ack.js:6` | 由 localStorage 讀取 Manager 端任務顯示快取。 | Dashboard |
| `writeEngineerTaskCache()` | 任務與 ACK | `main/engineer-ack.js:15` | 將任務顯示快取寫入 localStorage。 | Dashboard |
| `markEngineerTaskMailSent()` | 任務與 ACK | `main/engineer-ack.js:23` | 把已建立／寄送任務寫入快取。 | Dashboard |
| `cacheEngineerTask()` | 任務與 ACK | `main/engineer-ack.js:29` | 以 Task ID 更新單筆快取資料。 | Dashboard |
| `getCachedEngineerTaskForRecommendation()` | 任務與 ACK | `main/engineer-ack.js:40` | 依站別與問題比對建議先前建立的任務。 | Dashboard |
| `syncEngineerAckStatusForSentTasks()` | 任務與 ACK | `main/engineer-ack.js:54` | 對快取中 sent 任務呼叫 sync-ack，更新 acknowledged 狀態並重畫。 | Dashboard |
| `createEngineerTask()` | 任務與 ACK | `main/engineer-task-api.js:1` | POST 建立工程師任務。 | Dashboard、通知紀錄 |
| `getEngineerTasks()` | 任務與 ACK | `main/engineer-task-api.js:8` | 依寄送狀態、limit 與 offset 查詢任務清單。 | Dashboard、通知紀錄 |
| `getEngineerTask()` | 任務與 ACK | `main/engineer-task-api.js:16` | 依 Task ID 查詢單筆任務詳細資料。 | Dashboard、通知紀錄 |
| `syncEngineerTaskAck()` | 任務與 ACK | `main/engineer-task-api.js:20` | 要求後端同步指定任務的舊 Apps Script ACK。 | Dashboard、通知紀錄 |
| `getValueAtPath()` | 啟動與 API | `main/manager-api-validation.js:1` | 依點號路徑及陣列索引／lineId selector 讀取巢狀 payload。 | Dashboard |
| `requireManagerPayloadField()` | 啟動與 API | `main/manager-api-validation.js:20` | 要求欄位存在，必要時要求陣列長度，否則拋出可定位欄位的錯誤。 | Dashboard |
| `requireManagerArrayField()` | 啟動與 API | `main/manager-api-validation.js:46` | 要求指定欄位存在且為陣列。 | Dashboard |
| `validateManagerDashboardPayload()` | 啟動與 API | `main/manager-api-validation.js:59` | 檢查必要欄位、三站資料、24 小時趨勢、日期／小時一致性，並拒絕 mock 或 fallback。 | Dashboard |
| `getHourlyValuesFromDb()` | 啟動與 API | `main/manager-api-validation.js:183` | 取得指定站別與指標的 24 小時序列，並將有效值轉成 Number。 | Dashboard |
| `getProjectSchemaMockBundle()` | 未載入的舊整合模組 | `main/project-api.js:7` | 取得 project schema mock bundle；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `normalizeProjectApiBundleToManagerDb()` | 未載入的舊整合模組 | `main/project-api.js:18` | 正規化 project api bundle to manager db；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `normalizeState()` | 未載入的舊整合模組 | `main/project-api.js:197` | 正規化 state；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `normalizeSeverity()` | 未載入的舊整合模組 | `main/project-api.js:203` | 正規化 severity；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `normalizeQualityTrend()` | 未載入的舊整合模組 | `main/project-api.js:211` | 正規化 quality trend；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `normalizeSingleSeriesTrend()` | 未載入的舊整合模組 | `main/project-api.js:224` | 正規化 single series trend；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getTrendRowHour()` | 未載入的舊整合模組 | `main/project-api.js:235` | 取得 trend row hour；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getTrendRowValue()` | 未載入的舊整合模組 | `main/project-api.js:242` | 取得 trend row value；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `buildProjectApiUrl()` | 未載入的舊整合模組 | `main/project-api.js:248` | 建立 project api url；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `fetchJsonOrNull()` | 未載入的舊整合模組 | `main/project-api.js:255` | 讀取 json or null；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `fetchProjectSchemaApiBundle()` | 未載入的舊整合模組 | `main/project-api.js:261` | 讀取 project schema api bundle；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getHourlyValuesFromDb()` | 未載入的舊整合模組 | `main/project-api.js:306` | 取得指定站別與指標的 24 小時序列，並將有效值轉成 Number。 | 目前頁面未載入 |
| `setTrendDrawerOpen()` | 趨勢與診斷 | `main/render-diagnosis.js:1` | 設定趨勢抽屜開關與目前站別／指標，並同步 ARIA 狀態。 | Dashboard |
| `renderTrendDrawer()` | 趨勢與診斷 | `main/render-diagnosis.js:7` | 依目前選擇渲染或清空趨勢抽屜。 | Dashboard |
| `buildTrendDrawerMarkup()` | 趨勢與診斷 | `main/render-diagnosis.js:38` | 組合趨勢摘要、數值與 SVG 圖表標記。 | Dashboard |
| `renderTrendChartSvg()` | 趨勢與診斷 | `main/render-diagnosis.js:62` | 將 24 小時序列轉成 SVG 折線圖。 | Dashboard |
| `renderManagerHeader()` | KPI 與站別比較 | `main/render-overview.js:1` | 渲染日期、時段、批次與資料更新狀態控制列。 | Dashboard |
| `renderOverviewSection()` | KPI 與站別比較 | `main/render-overview.js:56` | 組合 KPI 與站別比較兩個總覽區塊。 | Dashboard |
| `renderKpiSection()` | KPI 與站別比較 | `main/render-overview.js:66` | 顯示估計 OK／NG 率、生產達成率與當日生產資料。 | Dashboard |
| `renderStationComparisonSection()` | KPI 與站別比較 | `main/render-overview.js:107` | 建立三站比較表。 | Dashboard |
| `renderStationComparisonRow()` | KPI 與站別比較 | `main/render-overview.js:147` | 渲染單一站別的狀態、產量、利用率與主要問題。 | Dashboard |
| `renderMetricCell()` | KPI 與站別比較 | `main/render-overview.js:168` | 渲染指標值及趨勢按鈕。 | Dashboard |
| `renderTrendIconButton()` | KPI 與站別比較 | `main/render-overview.js:181` | 建立可開啟指定站別／指標趨勢的按鈕。 | Dashboard |
| `renderRecommendationSection()` | 建議與派工 | `main/render-recommendations.js:1` | 顯示待處理建議；無建議時呈現明確空狀態。 | Dashboard |
| `renderRecommendationCard()` | 建議與派工 | `main/render-recommendations.js:37` | 渲染問題、建議、等級與通知狀態，並依快取任務停用重複送出。 | Dashboard |
| `buildEngineerWarningPayload()` | 建議與派工 | `main/render-recommendations.js:68` | 把目前日期、時段、批次與建議轉成工程師任務建立 payload。 | Dashboard |
| `showManagerToast()` | 建議與派工 | `main/render-recommendations.js:100` | 顯示短暫操作結果訊息並自動移除。 | Dashboard |
| `sendEngineerWarningEmail()` | 建議與派工 | `main/render-recommendations.js:120` | 優先查詢正式站別工程師指派並開啟多人選擇；無指派時才詢問舊 Email fallback。 | Dashboard |
| `sendLegacyEngineerWarning()` | 建議與派工 | `main/render-recommendations.js:149` | 以建議內的單一工程師 Email 建立舊式任務，更新按鈕、快取與 Toast。 | Dashboard |
| `submitAssignmentSelection()` | 建議與派工 | `main/render-recommendations.js:188` | 驗證 Primary 必須已選取，組合多人 assignees，建立正式任務並更新 UI。 | Dashboard |
| `getSimulatedDayMetricOffset()` | 未載入的模擬模組 | `main/simulated-generators.js:5` | 取得 simulated day metric offset；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `makeSimulatedStationMetric()` | 未載入的模擬模組 | `main/simulated-generators.js:26` | 產生 simulated station metric；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `makeTrendValue()` | 未載入的模擬模組 | `main/simulated-generators.js:58` | 產生 trend value；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `makeSimulatedTrend()` | 未載入的模擬模組 | `main/simulated-generators.js:89` | 產生 simulated trend；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `makeTrendApiPayload()` | 未載入的模擬模組 | `main/simulated-generators.js:93` | 產生 trend api payload；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `buildSimulatedDiagnoses()` | 未載入的模擬模組 | `main/simulated-generators.js:122` | 建立 simulated diagnoses；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getSimulatedApiStatusText()` | 未載入的模擬模組 | `main/simulated-generators.js:190` | 取得 simulated api status text；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `makeSimulatedBatchInfo()` | 未載入的模擬模組 | `main/simulated-generators.js:206` | 產生 simulated batch info；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `clampValue()` | 未載入的模擬模組 | `main/simulated-generators.js:243` | 處理 clamp value；用途依所在模組的資料流而定。 | 目前頁面未載入 |
| `getActualQualityOffset()` | 未載入的模擬模組 | `main/simulated-generators.js:248` | 取得 actual quality offset；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getActualQualityScoreFromDb()` | 未載入的模擬模組 | `main/simulated-generators.js:257` | 取得 actual quality score from db；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `actualizeQualityTrendFromDb()` | 未載入的模擬模組 | `main/simulated-generators.js:264` | 以正式資料校正 quality trend from db；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `updateBatchToActualQc()` | 未載入的模擬模組 | `main/simulated-generators.js:270` | 更新 batch to actual qc；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `actualizeDatabaseResponseFromDb()` | 未載入的模擬模組 | `main/simulated-generators.js:281` | 以正式資料校正 database response from db；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `ensureHistoricalActualQualityData()` | 未載入的模擬模組 | `main/simulated-generators.js:361` | 確保 historical actual quality data；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `buildProjectSchemaMockBundle()` | 未載入的模擬模組 | `main/simulated-generators.js:369` | 建立 project schema mock bundle；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getDateKey()` | 未載入的模擬模組 | `main/simulated-history.js:5` | 取得 date key；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `parseDateKey()` | 未載入的模擬模組 | `main/simulated-history.js:12` | 將 YYYY-MM-DD 轉成本機 Date。 | 目前頁面未載入 |
| `getDateKeyFromTimestamp()` | 未載入的模擬模組 | `main/simulated-history.js:17` | 取得 date key from timestamp；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `addDaysToDateKey()` | 未載入的模擬模組 | `main/simulated-history.js:22` | 處理 add days to date key；用途依所在模組的資料流而定。 | 目前頁面未載入 |
| `getActiveApiDateKey()` | 未載入的模擬模組 | `main/simulated-history.js:28` | 取得 active api date key；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getInitialReportDateKey()` | 未載入的模擬模組 | `main/simulated-history.js:34` | 回傳初始日期；正式版目前為 null，交由 API 決定最新資料。 | 目前頁面未載入 |
| `safeReadLocalStorageJson()` | 未載入的模擬模組 | `main/simulated-history.js:38` | 處理 safe read local storage json；用途依所在模組的資料流而定。 | 目前頁面未載入 |
| `mergeObjectStores()` | 未載入的模擬模組 | `main/simulated-history.js:49` | 處理 merge object stores；用途依所在模組的資料流而定。 | 目前頁面未載入 |
| `getSimulatedArchiveStore()` | 未載入的模擬模組 | `main/simulated-history.js:59` | 取得 simulated archive store；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `saveSimulatedArchiveStore()` | 未載入的模擬模組 | `main/simulated-history.js:76` | 儲存 simulated archive store；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getSimulatedStateStore()` | 未載入的模擬模組 | `main/simulated-history.js:85` | 取得 simulated state store；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `saveSimulatedApiState()` | 未載入的模擬模組 | `main/simulated-history.js:99` | 儲存 simulated api state；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getDateDiffDays()` | 未載入的模擬模組 | `main/simulated-history.js:120` | 取得 date diff days；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `hydrateSimulatedApiStateFromLocalStorage()` | 未載入的模擬模組 | `main/simulated-history.js:126` | 處理 hydrate simulated api state from local storage；用途依所在模組的資料流而定。 | 目前頁面未載入 |
| `getArchivedDateKeys()` | 未載入的模擬模組 | `main/simulated-history.js:156` | 取得 archived date keys；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getArchivedDatabaseResponse()` | 未載入的模擬模組 | `main/simulated-history.js:160` | 取得 archived database response；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `archiveDatabaseResponseForDate()` | 未載入的模擬模組 | `main/simulated-history.js:165` | 封存 database response for date；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getSimulatedHourlyStore()` | 未載入的模擬模組 | `main/simulated-history.js:180` | 取得 simulated hourly store；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `saveSimulatedHourlyStore()` | 未載入的模擬模組 | `main/simulated-history.js:197` | 儲存 simulated hourly store；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getResponseHourFromDb()` | 未載入的模擬模組 | `main/simulated-history.js:206` | 取得 API 選定小時並限制於 0 至 23。 | 目前頁面未載入 |
| `getResponseDateKeyFromDb()` | 未載入的模擬模組 | `main/simulated-history.js:217` | 取得 API 選定日期。 | 目前頁面未載入 |
| `createDecisionSnapshotForDb()` | 未載入的模擬模組 | `main/simulated-history.js:227` | 建立 decision snapshot for db；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `storeHourlySnapshotForDbResponse()` | 未載入的模擬模組 | `main/simulated-history.js:243` | 正式版保留的相容函式，目前為空實作，不寫入 localStorage。 | 目前頁面未載入 |
| `getHourlySnapshot()` | 未載入的模擬模組 | `main/simulated-history.js:273` | 取得 hourly snapshot；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getHourlySnapshotsForDate()` | 未載入的模擬模組 | `main/simulated-history.js:279` | 取得 hourly snapshots for date；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getProblemHourMapForDate()` | 未載入的模擬模組 | `main/simulated-history.js:284` | 取得 problem hour map for date；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getLatestAvailableHourForDate()` | 未載入的模擬模組 | `main/simulated-history.js:293` | 取得 latest available hour for date；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getSimulationDayIndexForDate()` | 未載入的模擬模組 | `main/simulated-history.js:300` | 取得 simulation day index for date；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `makeSimulatedDbResponseForDateHour()` | 未載入的模擬模組 | `main/simulated-history.js:306` | 產生 simulated db response for date hour；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getOrCreateHourlySnapshot()` | 未載入的模擬模組 | `main/simulated-history.js:322` | 取得 or create hourly snapshot；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `generateHourOptionsForSelectedDate()` | 未載入的模擬模組 | `main/simulated-history.js:342` | 依所選日期建立時段選項。 | 目前頁面未載入 |
| `getSelectedHourSelectValue()` | 未載入的模擬模組 | `main/simulated-history.js:376` | 取得目前應顯示的時段值。 | 目前頁面未載入 |
| `setDefaultTimeSelectionForDate()` | 未載入的模擬模組 | `main/simulated-history.js:380` | 設定 default time selection for date；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getTimeReviewModeLabel()` | 未載入的模擬模組 | `main/simulated-history.js:392` | 取得 time review mode label；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getSelectedDateMode()` | 未載入的模擬模組 | `main/simulated-history.js:397` | 取得 selected date mode；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getSimulatedApiCurrentHour()` | 未載入的模擬模組 | `main/simulated-history.js:404` | 取得 simulated api current hour；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getSimulatedGeneratedAt()` | 未載入的模擬模組 | `main/simulated-history.js:412` | 取得 simulated generated at；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `getSimulatedScenario()` | 未載入的模擬模組 | `main/simulated-history.js:417` | 取得 simulated scenario；此函式屬於模組內部資料或畫面處理。 | 目前頁面未載入 |
| `normalizeManagerSummary()` | 狀態與格式 | `main/summary-state.js:16` | 補齊 batchSelector、stationComparison、recommendations 與 trendDrawer 的安全預設值。 | Dashboard |
| `getManagerSummaryFromDatabase()` | 狀態與格式 | `main/summary-state.js:31` | 由 API payload 的 managerView 建立前端 Manager 摘要狀態。 | Dashboard |
| `escapeHtml()` | 狀態與格式 | `main/summary-state.js:37` | 跳脫使用者或 API 文字，降低插入 innerHTML 時的 HTML 注入風險。 | Dashboard |
| `formatPercent()` | 狀態與格式 | `main/summary-state.js:46` | 將數值格式化成百分比；空值顯示破折號。 | Dashboard |
| `formatNumber()` | 狀態與格式 | `main/summary-state.js:51` | 將數值格式化成千分位；空值顯示破折號。 | Dashboard |
| `formatPcs()` | 狀態與格式 | `main/summary-state.js:56` | 將數值格式化成 pcs 數量。 | Dashboard |
| `formatMetricValue()` | 狀態與格式 | `main/summary-state.js:61` | 依指標類型選擇百分比或件數格式。 | Dashboard |
| `levelClass()` | 狀態與格式 | `main/summary-state.js:67` | 把 alarm／critical／warning／normal 對應到 CSS 狀態類別。 | Dashboard |
| `statusClass()` | 狀態與格式 | `main/summary-state.js:74` | 沿用 levelClass，提供狀態樣式相容入口。 | Dashboard |
| `formatLevelLabel()` | 狀態與格式 | `main/summary-state.js:78` | 將英文風險等級轉成警報、警示或正常。 | Dashboard |
| `getSelectedBatchLabel()` | 狀態與格式 | `main/summary-state.js:85` | 回傳已選批次，否則顯示該小時全部批號的預設標籤。 | Dashboard |
| `getManagerKpis()` | 狀態與格式 | `main/summary-state.js:90` | 安全取得 Manager KPI 物件。 | Dashboard |
| `getStationComparisonRows()` | 狀態與格式 | `main/summary-state.js:94` | 安全取得站別比較列。 | Dashboard |
| `getRecommendationItems()` | 狀態與格式 | `main/summary-state.js:98` | 安全取得處理建議陣列。 | Dashboard |
| `getBatchOptions()` | 狀態與格式 | `main/summary-state.js:102` | 安全取得可選批次清單。 | Dashboard |
| `getComparisonRowByStationId()` | 狀態與格式 | `main/summary-state.js:108` | 依 stationId 查找站別比較資料。 | Dashboard |
| `getTrendDrawerMetricData()` | 狀態與格式 | `main/summary-state.js:112` | 取得特定站別與指標的趨勢抽屜資料。 | Dashboard |
| `getTrendDrawerStationTitle()` | 狀態與格式 | `main/summary-state.js:116` | 組合趨勢抽屜的站名與製程名稱。 | Dashboard |
| `clearNotificationResetTimer()` | 狀態與格式 | `main/summary-state.js:122` | 取消並移除通知按鈕的重設計時器。 | Dashboard |
| `parseDateKey()` | 日期與時段 | `main/time-review.js:1` | 將 YYYY-MM-DD 轉成本機 Date。 | Dashboard |
| `formatDateLabel()` | 日期與時段 | `main/time-review.js:6` | 將日期顯示為 YYYY/MM/DD。 | Dashboard |
| `getResponseHourFromDb()` | 日期與時段 | `main/time-review.js:15` | 取得 API 選定小時並限制於 0 至 23。 | Dashboard |
| `getResponseDateKeyFromDb()` | 日期與時段 | `main/time-review.js:21` | 取得 API 選定日期。 | Dashboard |
| `getInitialReportDateKey()` | 日期與時段 | `main/time-review.js:26` | 回傳初始日期；正式版目前為 null，交由 API 決定最新資料。 | Dashboard |
| `getLatestDateKeyFromDb()` | 日期與時段 | `main/time-review.js:30` | 取得資料庫最新日期。 | Dashboard |
| `getLatestHourFromDb()` | 日期與時段 | `main/time-review.js:35` | 取得資料庫最新小時。 | Dashboard |
| `getAvailableDatesFromDb()` | 日期與時段 | `main/time-review.js:41` | 取得 API 提供的可查詢日期清單。 | Dashboard |
| `getAvailableHoursByDateFromDb()` | 日期與時段 | `main/time-review.js:46` | 取得日期到可查詢小時的對照表。 | Dashboard |
| `getAvailableHoursForDate()` | 日期與時段 | `main/time-review.js:51` | 取得指定日期的有效小時並排序。 | Dashboard |
| `formatHourRangeLabel()` | 日期與時段 | `main/time-review.js:67` | 將小時顯示為 HH:00 - HH:59。 | Dashboard |
| `generateDateOptions()` | 日期與時段 | `main/time-review.js:74` | 建立日期選項，並標示資料庫最新日期。 | Dashboard |
| `generateHourOptionsForSelectedDate()` | 日期與時段 | `main/time-review.js:82` | 依所選日期建立時段選項。 | Dashboard |
| `getSelectedHourSelectValue()` | 日期與時段 | `main/time-review.js:89` | 取得目前應顯示的時段值。 | Dashboard |
| `syncSelectedDateHourFromDb()` | 日期與時段 | `main/time-review.js:94` | 以 API responseMeta 與 batchSelector 同步前端選擇狀態。 | Dashboard |
| `storeHourlySnapshotForDbResponse()` | 日期與時段 | `main/time-review.js:101` | 正式版保留的相容函式，目前為空實作，不寫入 localStorage。 | Dashboard |
| `apiBase()` | 通知紀錄 | `notification-history.js:2` | 處理 api base；用途依所在模組的資料流而定。 | 通知紀錄 |
| `managerAttachmentUrl()` | 通知紀錄 | `notification-history.js:8` | 建立 Manager 權限的附件下載 URL。 | 通知紀錄 |
| `renderAttachment()` | 通知紀錄 | `notification-history.js:12` | 依附件類型建立圖片預覽或下載連結。 | 通知紀錄 |
| `renderReports()` | 通知紀錄 | `notification-history.js:20` | 顯示任務回報內容與附件。 | 通知紀錄 |
| `query()` | 通知紀錄 | `notification-history.js:33` | 從通知紀錄篩選控制項組合 URLSearchParams。 | 通知紀錄 |
| `loadHistory()` | 通知紀錄 | `notification-history.js:40` | 依目前頁籤讀取通知決策或工程師任務，並更新表格與分頁。 | 通知紀錄 |
| `renderRows()` | 通知紀錄 | `notification-history.js:52` | 依決策／任務頁籤渲染表格列。 | 通知紀錄 |
| `renderPager()` | 通知紀錄 | `notification-history.js:63` | 更新頁碼及上一頁／下一頁可用狀態。 | 通知紀錄 |
| `openTask()` | 通知紀錄 | `notification-history.js:70` | 讀取任務詳細資料並開啟 Manager 檢視 Dialog。 | 通知紀錄 |
| `taskAction()` | 通知紀錄 | `notification-history.js:78` | 處理重寄、審核、重開及補充期間等 Manager 任務動作。 | 通知紀錄 |
| `syncLegacyAcks()` | 通知紀錄 | `notification-history.js:98` | 對畫面中的舊任務批次執行 ACK 同步。 | 通知紀錄 |
| `updatePolling()` | 通知紀錄 | `notification-history.js:103` | 只在任務頁籤可見時，每 120 秒同步舊 ACK。 | 通知紀錄 |

## API Contract

| Method | Path | 用途 | 主要輸入 | 主要輸出 |
| --- | --- | --- | --- | --- |
| GET | /api/manager/dashboard | Dashboard | date、hour、batch_id | DB-backed Manager payload；含 responseMeta、KPI、三站比較、建議與趨勢 |
| GET | /api/manager/available-dates | 可用時間 | 無 | 可用日期、小時與日期對照 |
| POST | /api/manager/engineer-tasks | 建立任務 | 問題、建議、站別、批次、工程師／assignees | 任務與寄送狀態 |
| GET | /api/manager/engineer-tasks | 任務歷史 | 篩選、limit、offset | 分頁任務清單 |
| GET | /api/manager/engineer-tasks/{task_id} | 任務詳細 | Task ID | 指派、回報、附件與 workflow |
| POST | /api/manager/engineer-tasks/{task_id}/sync-ack | 舊 ACK 同步 | Task ID | 更新後的 deliveryStatus |
| GET | /api/manager/station-engineer-assignments | 站別工程師 | station_id、active_only | 可選工程師與 assignmentId |
| GET | /api/manager/notification-decisions | 通知決策歷史 | 日期、站別、批次、決策、分頁 | 決策清單與 total |
| POST | /api/manager/notification-decisions/evaluate | 通知政策 | 異常識別、severity、fingerprint | email_task_created／dashboard_only／suppressed／cooldown_skipped |
| GET | /api/manager/engineer-tasks/{task_id}/timeline | 任務時間線 | Task ID | 完整事件序列 |
| POST | /api/manager/engineer-tasks/{task_id}/resend | 重寄通知 | Task ID | 更新後任務 |
| PATCH | /api/manager/engineer-tasks/{task_id}/assignees | 改派人員 | Task ID、assignees | 更新後任務 |
| POST | /api/manager/engineer-tasks/{task_id}/review | Manager 審核 | Task ID、審核結果 | completed 或後續狀態 |
| POST | /api/manager/engineer-tasks/{task_id}/reopen | 重開任務 | Task ID、原因 | 新 assignment round |
| POST | /api/manager/engineer-tasks/{task_id}/supplementation/open\|close | 補充期間 | Task ID | 是否允許完成後補充 |
| GET | /api/manager/engineer-task-attachments/{attachment_id} | Manager 附件 | Attachment ID | 附件串流 |
| GET/POST | /api/engineer-task-access/* | 工程師交接 | Bearer Token | 任務、ACK、開始、回報、完成與附件 |

## 任務狀態

`unacknowledged → acknowledged → in_progress → completion_submitted → completed`

寄送狀態為 `pending`、`sent`、`failed`、`acknowledged`。工作流程與寄送狀態是兩個不同維度，不應混用。

## 資料字典

| 欄位 | 型別 | 來源 | 意義／限制 |
| --- | --- | --- | --- |
| responseMeta.source | string | API | 正式資料來源識別；前端拒絕 mock/web_service 標記 |
| responseMeta.generatedAt | datetime | API | payload 產生時間，不等同感測資料發生時間 |
| responseMeta.selectedDate | date | DB/API | 目前 Dashboard 查詢日期 |
| responseMeta.selectedHour | 0-23 | DB/API | 目前查詢小時 |
| responseMeta.availableDates | string[] | DB/API | 有資料可查詢的日期 |
| managerView.kpis | object | 後端衍生 | OK／NG 估計、生產達成與當日生產摘要 |
| managerView.stationComparison | array[3] | 後端衍生 | 三站比較；前端強制要求恰為三列 |
| managerView.recommendations | array | 後端規則 | 需處理事項、主因、建議與工程師 fallback |
| managerView.trendDrawer | object | DB 聚合／後端 | 站別指標的 24 小時序列 |
| selectedBatchId | string\|null | 前端狀態 | 選定批次；null 表示該小時全部批號 |
| deliveryStatus | enum | 任務資料庫 | pending、sent、failed、acknowledged |
| workflowStatus | enum | 任務資料庫 | unacknowledged、acknowledged、in_progress、completion_submitted、completed |
| notificationFingerprint | string | 後端 | 用於通知政策、重複抑制與 cooldown 判斷 |
| taskId | UUID | 任務資料庫 | 跨 Manager、Email、安全頁與 Timeline 的追蹤鍵 |
| localStorage task cache | object | 瀏覽器 | 僅供按鈕狀態與舊 ACK 同步，不是正式狀態來源 |

## 異常與安全

- API 或 payload 失敗時清空舊資料，避免把過期值當成目前狀態。
- PostgreSQL 是通知與任務的正式狀態來源；localStorage 僅供畫面快取與舊 ACK 同步。
- 工程師安全頁使用 Bearer Token；本文件不包含 Token、帳密或資料庫連線字串。
- 無正式站別指派時，必須由 Manager 確認後才使用舊 Email fallback。
- 通知 fingerprint 與後端政策負責重複抑制與 cooldown；前端停用按鈕不是正式一致性保證。

## 驗證邊界

- 已由程式碼確認：頁面載入、function、API route、payload 驗證與狀態名稱。
- 未宣稱：API、PostgreSQL、Email 或 Apps Script 目前正在執行。
- 既有測試環境曾受缺少 httpx 與 Python/Pydantic 相容性影響，不能把未完成測試解讀為功能失敗。
