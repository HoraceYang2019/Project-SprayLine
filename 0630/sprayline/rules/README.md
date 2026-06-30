# rules 說明（少榆0616ver_4）

本資料夾有兩個主要 JSON：

```text
sensor_thresholds.json
sensor_event_mapping.json
```

## sensor_thresholds.json

用途：判斷感測值屬於：

```text
normal / warning / fault
```

0616ver_4 仍以這份 JSON 作為少榆端 Monitoring / EventRule 的 threshold 來源。`Database/versionB` 雖然目前有 `sensor_threshold` table/function，但少榆端先不使用 DB threshold。

## sensor_event_mapping.json

用途：把 threshold 判斷結果補成可以寫入 DB 與 troubleshooting 的欄位：

```text
issue_state / fault_state
cause_id
response_ids
state_field
response_field
component_id
```

注意：這份 mapping 是 0616ver_4 安全整合草案，`cause_id` / `response_id` 的正式欄位語意仍待余宇承確認。
