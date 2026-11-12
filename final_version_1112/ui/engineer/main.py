from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.dependencies import rules_service, webservices_client
from app.routers import dashboard, detail, trend

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_FILE = BASE_DIR / "app" / "templates" / "dashboard.html"
STATIC_DIR = BASE_DIR / "app" / "static"

app = FastAPI(
    title="SprayLine UI_V29 Engineer Integrated",
    description=(
        "UI directly uses 少榆0620 final_version summary, station-detail and component-detail Service APIs. "
        "The source_mode is integrated; data is read through Webservices from PostgreSQL Database/versionB."
    ),
    version="29.0-engineer-ui",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(dashboard.router)
app.include_router(detail.router)
app.include_router(trend.router)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(
        TEMPLATE_FILE,
        media_type="text/html; charset=utf-8",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/api/health")
def health():
    return {
        "status": "running",
        "version": "UI_V29_EngineerIntegrated",
        "webservices_enabled": True,
        "database_required": True,
        "webservices_source_mode": webservices_client.source_mode,
        "routes": [
            "POST /api/time-series/ui/summary",
            "POST /api/time-series/ui/station-detail",
            "POST /api/time-series/ui/component-detail",
        ],
        "threshold_file": str(rules_service.threshold_path),
        "mapping_file": str(rules_service.mapping_path),
        "integration_source": "final_version_0715 with Ontology Runtime",
    }


@app.get("/api/integration-status")
def integration_status():
    return webservices_client.status()
