# JSON Output File

本版會產生兩種 JSON 檔。

## 1. 最新一次完整 output

```text
examples/time_series_latest_output.json
```

每次執行會覆蓋更新，方便直接打開查看最新結果。

## 2. Processed Result Database

```text
examples/processed_result_database_demo.json
```

每次執行會追加一筆資料，用來模擬 processed result database。

## 使用方式

```bash
cd src
python time_series_service.py
```

執行後會看到：

```text
Latest JSON output saved to: ../examples/time_series_latest_output.json
Processed result database saved to: ../examples/processed_result_database_demo.json
```
