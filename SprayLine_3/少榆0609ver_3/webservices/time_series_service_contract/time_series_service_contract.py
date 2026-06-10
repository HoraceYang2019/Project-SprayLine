"""TimeSeriesService contract for DB Schema v3 / DataPreprocess 0609ver_2.
No fake data should be returned here. Bind implementation to sensor_1hz or confirmed derived-feature storage.
"""
from typing import Any, Dict, List, Optional

class TimeSeriesService:
    def get_time_series(self, station: str, start_time: str, end_time: str, sensor_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Read sensor_1hz by station/time window, including DataPreprocess quality flags."""
        raise NotImplementedError

    def get_latest_sensor_snapshot(self, station: str) -> Dict[str, Any]:
        """Read latest sensor_1hz row for a station."""
        raise NotImplementedError

    def get_sensor_feature_window(self, station: str, sensor_name: str, start_time: str, end_time: str, aggregation_window: str) -> Dict[str, Any]:
        """Read or calculate rolling_avg / rolling_std / duration_over_threshold and other derived features.

        This is a proposed contract. Whether these values are stored in DB or computed on demand is pending Database/DataPreprocess confirmation.
        """
        raise NotImplementedError
