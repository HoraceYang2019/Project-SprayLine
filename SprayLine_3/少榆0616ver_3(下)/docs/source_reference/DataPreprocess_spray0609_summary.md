# DataPreprocess spray0609 摘要

- 原始時間序列頻率：每 1 分鐘一筆。
- 環境溫濕度於 Database 層聚合為每 3 分鐘一筆。
- `data_quality_flag=normal`：資料未補值。
- `data_quality_flag=interpolated`：資料曾缺值並完成前值／後值補齊。
- 現行 DB Schema v5 尚未持久化 `data_quality_flag`。
- 門檻值已整理於 `docs/contracts/data_preprocess_threshold_reference.csv` 與 `rules/sensor_thresholds.json`。
