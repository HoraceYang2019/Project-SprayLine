# Database VersionB 摘要

目前採用 `sensor_1min` 與 `sensor_3min`。`舊秒級資料表` 與 `舊小時資料表` 不納入本版本。

實際可用函式包括：`get_time_series`、`get_latest_sensor_snapshot`、`get_sensor_feature_window`、`list_batches_filtered`、`get_batch_detail`、`get_manager_summary`、`evaluate_event_rules`、`get_troubleshooting_matrix`、`get_state_recommendations`。
