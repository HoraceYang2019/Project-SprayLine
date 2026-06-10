"""DashboardService contract.
Manager UI is reference/mock until API binding is implemented.
"""
from typing import Any, Dict, Optional

class DashboardService:
    def get_manager_summary(self, date: str, station: Optional[str] = None) -> Dict[str, Any]:
        """Return manager dashboard summary from batch_summary / alert_event / PDM views."""
        raise NotImplementedError
