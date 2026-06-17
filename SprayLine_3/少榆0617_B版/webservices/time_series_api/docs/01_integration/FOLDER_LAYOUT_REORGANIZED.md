# 資料夾排版整理說明

本次整理的目的，是把「程式碼」、「設定檔」、「runtime 輸出」、「測試範例」、「文件」分開，避免所有 JSON 與文件都塞在同一層。

## 整理前主要問題

1. `examples/` 同時放 request、response、runtime database。
2. `docs/` 同時放今日更新、舊版文件、驗證文件。
3. `rules/` 雖然可用，但未來若加入 DB、Monitoring、Future 設定，會缺少統一設定區。
4. `src/__pycache__/` 被打包進 zip，正式交付不需要。

## 整理後原則

- 程式只放 `src/`。
- 設定只放 `config/`。
- API 執行後產生的資料放 `data/runtime/`。
- 測試 request 與 response 分開放。
- 整合文件與驗證文件分開。
- 舊文件保留，但移到 `docs/archive/`。

## 已同步修改的路徑

| 項目 | 舊路徑 | 新路徑 |
|---|---|---|
| EventRule threshold | `rules/sensor_thresholds.json` | `config/rules/sensor_thresholds.json` |
| Processed result DB | `examples/processed_result_database_demo.json` | `data/runtime/processed_result_database_demo.json` |
| Latest output | `examples/time_series_latest_output.json` | `data/runtime/time_series_latest_output.json` |

## 啟動位置

仍然從 `src/` 啟動：

```bash
cd time_series_service_v3_B_integrated_clean_layout/src
uvicorn api_server:app --reload --port 8001
```
