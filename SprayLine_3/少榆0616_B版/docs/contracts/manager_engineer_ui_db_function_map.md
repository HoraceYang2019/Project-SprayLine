# Manager / Engineer UI 可用 DB Function 對照表（少榆0616ver_4）

本文件不是要求少榆修改 UI。少榆負責 Future / Monitoring / EventRule / Troubleshooting 與 Database/versionB 的整合；Manager UI、Engineer UI 由 UI 同學處理。

本文件目的：讓老師與 UI 同學知道少榆端產生的資料要由哪些 Database/versionB function 查詢，避免 UI 寫死 demo JSON。

## 少榆端負責寫回 DB 的資料

```text
MonitoringWorker -> alert_event
MonitoringWorker -> alert_cause_link
MonitoringWorker -> alert_response_link
MonitoringWorker -> batch_station_status
FutureService    -> future_prediction_result
```

## Manager UI 建議查詢

| UI 需求 | 建議 DB function | 來源模組 | 備註 |
|---|---|---|---|
| 今日/指定日期總覽 | `get_manager_summary(conn, target_date, station_id=None)` | `db_composite.py` | 取得批次數、alert 數、station breakdown、future summary |
| 最新 future 風險摘要 | `get_future_prediction_summary(conn, station_id=None)` | `db_future.py` | 回傳 available、latest_risk_level、latest_predicted_ok_rate、latest_predicted_ng_count |
| 指定批次細節 | `get_batch_detail(conn, batch_id)` | `db_composite.py` | 回傳 batch、stations、alerts |
| 最近批次清單 | `get_latest_batches(conn, limit=10)` | `db_batch.py` | Manager 首頁 / 批次列表 |

## Engineer UI 建議查詢

| UI 需求 | 建議 DB function | 來源模組 | 備註 |
|---|---|---|---|
| 單筆 alert 詳細資料 | `get_alert_detail(conn, event_id)` | `db_alert.py` | 含 causes / responses |
| alert 卡片摘要 | `get_alert_ui_card(conn, event_id)` | `db_alert.py` | 給工程師頁面快速顯示用 |
| alert 對應原因 | `get_alert_causes(conn, event_id)` | `db_alert.py` | 查 alert_cause_link + cause_catalog |
| alert 對應應對措施 | `get_alert_responses(conn, event_id)` | `db_alert.py` | 查 alert_response_link + response_catalog |
| 指定原因的建議措施 | `get_responses_for_cause(conn, cause_id)` | `db_alert.py` | 例如 FILTER_CLOG -> REPLACE_FILTER / BACKWASH_FILTER |
| 批次站點狀態 | `get_batch_station_status(conn, batch_id, station_id)` | `db_status.py` | 6 個 component state + 6 個 response FK |

## 少榆端與 UI 的分工

```text
少榆端：產生並寫回 alert / future / station status。
UI 同學：透過 Database/versionB function 查詢並顯示。
余宇承端：維護 DB schema 與 DB function。
```

少榆端不在 0616ver_4 內修改 Manager UI / Engineer UI 前端。
