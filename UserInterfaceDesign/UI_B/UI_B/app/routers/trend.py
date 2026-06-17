from fastapi import APIRouter, HTTPException

from app.dependencies import dashboard_service
from app.services.dashboard_service import COMPONENT_BY_KEY
from app.services.local_data_service import STATIONS

router = APIRouter(prefix="/api", tags=["trend"])


@router.get("/trend-data")
def get_trend_data(station_id: str, component_key: str):
    if station_id not in STATIONS:
        raise HTTPException(status_code=404, detail="unknown station_id")
    if component_key not in COMPONENT_BY_KEY:
        raise HTTPException(status_code=404, detail="unknown component_key")
    return dashboard_service.trend_payload(station_id, component_key)
