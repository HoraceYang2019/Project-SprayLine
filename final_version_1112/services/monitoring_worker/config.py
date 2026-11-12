import os

MONITOR_INTERVAL_SECONDS = int(os.getenv("SPRAYLINE_MONITOR_INTERVAL_SECONDS", "60"))
DEFAULT_LOOKBACK_MINUTES = int(os.getenv("SPRAYLINE_MONITOR_LOOKBACK_MINUTES", "10"))
CHECKPOINT_FILE = os.getenv("SPRAYLINE_MONITOR_CHECKPOINT_FILE", "runtime/monitoring_checkpoint.json")

DEFAULT_STATIONS = [
    s.strip() for s in os.getenv("SPRAYLINE_MONITOR_STATIONS", "Station_1,Station_2,Station_3").split(",")
    if s.strip()
]

# 同一異常在此分鐘數內若仍未確認，MonitoringWorker 不重複寫入 alert_event。
DUPLICATE_ALERT_SUPPRESSION_MINUTES = int(os.getenv("SPRAYLINE_DUPLICATE_ALERT_SUPPRESSION_MINUTES", "5"))
# MonitoringWorker 的時間基準：
# data_anchor = 使用 DB 最新資料時間，適合快轉模擬資料
# wall_clock  = 使用電腦目前時間，適合未來真實產線
MONITOR_TIME_MODE = os.getenv(
    "SPRAYLINE_MONITOR_TIME_MODE",
    "data_anchor",
).strip().lower()

if MONITOR_TIME_MODE not in {"data_anchor", "wall_clock"}:
    raise ValueError(
        "SPRAYLINE_MONITOR_TIME_MODE must be "
        "'data_anchor' or 'wall_clock'."
    )


# MonitoringWorker 執行模式：
# once    = 執行一次後結束，供測試使用
# forever = 依設定間隔持續執行
MONITOR_RUN_MODE = os.getenv(
    "SPRAYLINE_MONITOR_RUN_MODE",
    "once",
).strip().lower()

if MONITOR_RUN_MODE not in {"once", "forever"}:
    raise ValueError(
        "SPRAYLINE_MONITOR_RUN_MODE must be "
        "'once' or 'forever'."
    )
