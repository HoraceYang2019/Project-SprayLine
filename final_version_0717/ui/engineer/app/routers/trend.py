from fastapi import APIRouter, HTTPException, Query

from app.dependencies import dashboard_service
from app.services.dashboard_service import COMPONENT_BY_KEY, STATIONS

router = APIRouter(prefix="/api", tags=["trend"])


@router.get("/trend-data")
def get_trend_data(
    station_id: str,
    component_key: str,
    mode: str = Query("time", pattern="^(time|batch)$"),
    slider_value: float = 0,
    snapshot_seed: int | None = None,
):
    if station_id not in STATIONS:
        raise HTTPException(status_code=404, detail="unknown station_id")
    if component_key not in COMPONENT_BY_KEY:
        raise HTTPException(status_code=404, detail="unknown component_key")
    try:
        return dashboard_service.trend_payload(
            station_id,
            component_key,
            slider_value=slider_value,
            mode=mode,
            snapshot_seed=snapshot_seed,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
