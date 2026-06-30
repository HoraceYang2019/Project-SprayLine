from pathlib import Path
import os

from app.services.dashboard_service import DashboardService
from app.services.diagnosis_service import DiagnosisService
from app.services.rules_service import RulesService

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "config"

rules_service = RulesService(CONFIG_DIR)

# Formal DB mode: Engineer UI must read through SPRAYLINE_API_BASE.
# Do not silently fall back to LocalDataService, otherwise old demo data can mix into UI.
if not os.getenv("SPRAYLINE_API_BASE", ""):
    raise RuntimeError("SPRAYLINE_API_BASE is required in formal DB mode; local demo fallback is disabled.")

from app.services.api_data_service import ApiDataService

local_data_service = ApiDataService()

diagnosis_service = DiagnosisService()
dashboard_service = DashboardService(local_data_service, rules_service, diagnosis_service)
