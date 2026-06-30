from pathlib import Path
import os as _os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.dependencies import local_data_service, rules_service
from app.routers import dashboard, detail, trend

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_FILE = BASE_DIR / "app" / "templates" / "dashboard.html"
STATIC_DIR = BASE_DIR / "app" / "static"

app = FastAPI(
    title="SprayLine UI_V6 Local Dashboard",
    description="Engineer UI formal DB mode; local demo fallback disabled.",
    version="6.0-local",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(dashboard.router)
app.include_router(detail.router)
app.include_router(trend.router)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(TEMPLATE_FILE, media_type="text/html; charset=utf-8")


@app.get("/api/health")
def health():
    anchor = local_data_service.ensure_current()
    return {
        "status": "running",
        "version": "UI_V6_Local",
        "database_enabled": bool(_os.getenv("SPRAYLINE_API_BASE")),
        "data_source": "api-formal-db",
        "snapshot_refresh_sec": local_data_service.refresh_seconds,
        "current_anchor": anchor.isoformat(),
        "threshold_file": str(rules_service.threshold_path),
        "mapping_file": str(rules_service.mapping_path),
        "integration_source": "SprayLine_3/少榆0616_B版",
    }


@app.get("/api/config")
def get_config():
    return {
        "manager_url": _os.getenv("MANAGER_UI_URL", "http://localhost:8012"),
        "api_base": _os.getenv("SPRAYLINE_API_BASE", ""),
        "data_source": "api-formal-db",
    }
