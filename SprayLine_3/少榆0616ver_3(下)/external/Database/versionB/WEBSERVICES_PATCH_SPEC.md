# WEBSERVICES_PATCH_SPEC（0616ver_3 reference）

本檔為 0616ver_3 隨包附上的 Database/versionB 參考說明。

0616ver_3 少榆端目前不新增正式 Web API 層，而是直接 import `Database/versionB` 的 Python function：

```text
db_sensor.py
db_alert.py
db_status.py
db_future.py
db_knowledge.py
```

若未來需要 WebServices patch，請由余宇承 / Backend 端另行確認正式服務入口。
少榆端本版只維護 Future / Monitoring / EventRule / Troubleshooting 的 Python 整合邏輯。
