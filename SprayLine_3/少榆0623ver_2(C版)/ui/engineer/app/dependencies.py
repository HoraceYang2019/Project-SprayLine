from pathlib import Path
import os

from app.services.dashboard_service import DashboardService
from app.services.diagnosis_service import DiagnosisService
from app.services.rules_service import RulesService

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "config"

rules_service = RulesService(CONFIG_DIR)

if os.getenv("SPRAYLINE_API_BASE", ""):
    try:
        from app.services.api_data_service import ApiDataService

        local_data_service = ApiDataService()
    except Exception:
        from app.services.local_data_service import LocalDataService

        local_data_service = LocalDataService(refresh_seconds=15)
else:
    from app.services.local_data_service import LocalDataService

    local_data_service = LocalDataService(refresh_seconds=15)

diagnosis_service = DiagnosisService()
dashboard_service = DashboardService(local_data_service, rules_service, diagnosis_service)
