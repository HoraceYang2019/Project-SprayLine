<!--
檔案備註：
Threshold 設計說明：說明 threshold 屬於 rule service、expert knowledge 或系統設定，而不是每筆 output 的固定欄位。

資料夾流程定位：流程 Step 5：將 threshold 獨立成設定模板，不混入每筆 output。
-->

# Threshold Config Notes

threshold 不放在每一筆 statistics service output 裡。

threshold 屬於：
- expert knowledge
- rule service config
- system configuration
- future service / risk model setting

statistics service 可以引用 threshold，但不應把 threshold 視為固定 output 欄位。

threshold_config.template.json 目前僅定義門檻設定的欄位結構，不填入實際門檻值；實際 threshold value、warning rule、alarm rule 需由 expert knowledge、system configuration、rule service 或 future risk model 後續確認。