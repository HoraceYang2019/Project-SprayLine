"""BatchService contract for manager dashboard and risk filtering."""
from typing import Any, Dict, Optional

class BatchService:
    def list_batches_filtered(self, date: str, risk: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None, station: Optional[str] = None) -> Dict[str, Any]:
        """GET /batches?date=today&risk=High,Medium&start=09:00&end=15:00."""
        raise NotImplementedError

    def get_batch_detail(self, batch_id: str) -> Dict[str, Any]:
        """Return batch summary and optional linked sensor window."""
        raise NotImplementedError
