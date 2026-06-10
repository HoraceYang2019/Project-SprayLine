"""TroubleshootingService contract for cause-response knowledge."""
from typing import Any, Dict, Optional

class TroubleshootingService:
    def get_troubleshooting_matrix(self, asset_type: Optional[str] = None, issue_type: Optional[str] = None) -> Dict[str, Any]:
        """Return FaultSymptom/FaultCause/CandidateResponse matrix."""
        raise NotImplementedError

    def get_issue_recommendations(self, issue_type: str, station: Optional[str] = None) -> Dict[str, Any]:
        """Return possible causes and candidate responses; not official rule output."""
        raise NotImplementedError
