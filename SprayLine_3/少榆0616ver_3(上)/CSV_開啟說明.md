# CSV 開啟說明（0616ver_3）

本版已將 `*.csv` 統一轉成 **UTF-8 with BOM（utf-8-sig）**，並保留第一行 `sep=,`。

## 開啟方式

- **VS Code**：可直接開啟，右下角應顯示 `UTF-8 with BOM` 或 `UTF-8`。
- **Excel**：可直接雙擊開啟；若電腦環境仍顯示亂碼，請用「資料 → 從文字/CSV」匯入，檔案原點選 `65001: Unicode (UTF-8)`。

## 檢查紀錄

- CSV 數量：20 個
- 編碼：全部已統一為 UTF-8 with BOM
- JSON / Python 檢查不受本次 CSV 編碼調整影響

## 注意

這次只處理少榆端 `少榆0616ver_3` 內的 CSV。`external/Database/versionB` 屬於余宇承端 DB 參考檔，不在本次 CSV 轉檔清單內。
