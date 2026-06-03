# Knowledge layer 說明

此資料夾用來放 threshold、batch range、expert knowledge 與 rule 會使用的判斷依據。

目前狀態：

- `threshold_config.template.json` 是暫時模板，不是正式門檻值。
- SprayWidth / 噴幅已加入為 UI_v4 新增功能，但正式目標範圍與 threshold 尚未定案。
- AirCompressor 已作為目前空壓機元件名稱 / 空壓機。
- 正式 `SprayLine_knowledge.ttl` 尚未建立，因為 threshold values、rules、Past / Current 資料欄位與 Database functions 尚未全部定案。
