# CSV 在 Excel 開啟說明

本版已將所有 `.csv` 檔案改成 Windows Excel 較穩定辨識的格式：

```text
編碼：CP950 / Big5（繁體中文 Windows Excel 友善）
第一列：sep=,
分隔符號：逗號 ,
換行：CRLF
```

## 為什麼改成 CP950 / Big5？

前一版使用 UTF-8 BOM + `sep=,`，雖然可以讓 Excel 自動分欄，但在部分繁體中文 Excel 環境仍可能把中文註解顯示成亂碼。

因此本版改用繁體中文 Windows Excel 較容易直接開啟的 CP950 / Big5。

## 使用方式

直接用 Excel 開啟 `.csv` 檔即可。
欄位應會自動分開，中文也不應再變成亂碼。

## 注意

Excel 開啟 CSV 時可能仍會出現「可能發生資料遺失」提示，這是 Excel 對 CSV 格式的正常提醒，不代表檔案壞掉。
若需要保留 Excel 樣式，請另存為 `.xlsx`。
