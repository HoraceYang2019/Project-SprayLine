"""EventRuleService contract.
Rule definitions are described in ontology; official thresholds/rules remain pending.
"""
from typing import Any, Dict

class EventRuleService:
    def evaluate_event_rules(self, station: str, timestamp: str, sensor_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate pending/confirmed TriggerRule and write alert_event when implemented."""
        raise NotImplementedError

    def list_unacknowledged_alert_events(self, station: str | None = None, severity: str | None = None) -> Dict[str, Any]:
        """Read v_unacknowledged_alerts / alert_event."""
        raise NotImplementedError

    def acknowledge_alert_event(self, event_id: str, operator_id: str) -> Dict[str, Any]:
        """Acknowledge alert_event."""
        raise NotImplementedError
