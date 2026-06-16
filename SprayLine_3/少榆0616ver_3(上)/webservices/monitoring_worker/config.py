import os

MONITOR_INTERVAL_SECONDS = int(os.getenv("SPRAYLINE_MONITOR_INTERVAL_SECONDS", "60"))
DEFAULT_LOOKBACK_MINUTES = int(os.getenv("SPRAYLINE_MONITOR_LOOKBACK_MINUTES", "10"))
CHECKPOINT_FILE = os.getenv("SPRAYLINE_MONITOR_CHECKPOINT_FILE", "runtime/monitoring_checkpoint.json")

DEFAULT_STATIONS = [
    s.strip() for s in os.getenv("SPRAYLINE_MONITOR_STATIONS", "Station_1,Station_2,Station_3").split(",")
    if s.strip()
]
