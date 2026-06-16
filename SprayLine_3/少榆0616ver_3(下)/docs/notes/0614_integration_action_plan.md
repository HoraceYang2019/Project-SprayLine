# 0614 Integration Action Plan（歷史參考）

此檔案只保留作為 0614 版本歷史脈絡。  
0616ver_3 的正式承接請改看：

```text
docs/notes/0616_integration_action_plan.md
README_快速上手.md
0616ver_3_修改報告.md
```

0616ver_3 目前方向：

```text
少榆端直接 import Database/versionB function
不走 HTTP 對外路由
不新增 API server 檔案
future_prediction_result 已由 Database/versionB 提供
threshold 先用 rules/sensor_thresholds.json
alert / status 透過 db_alert.py 與 db_status.py 寫入
```
