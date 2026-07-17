from pathlib import Path

from app.services.dashboard_service import DashboardService
from app.services.diagnosis_service import DiagnosisService
from app.services.rules_service import RulesService
from app.services.webservices_client import WebservicesClient

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "config"

rules_service = RulesService(CONFIG_DIR)
diagnosis_service = DiagnosisService()
webservices_client = WebservicesClient()
dashboard_service = DashboardService(rules_service, diagnosis_service, webservices_client)
