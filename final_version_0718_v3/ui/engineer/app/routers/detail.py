from fastapi import APIRouter, HTTPException, Query

from app.dependencies import dashboard_service
from app.services.dashboard_service import COMPONENT_BY_KEY, STATIONS

router = APIRouter(prefix="/api", tags=["detail"])


@router.get("/component-detail")
def get_component_detail(
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
        return dashboard_service.component_detail(
            station_id,
            component_key,
            slider_value=slider_value,
            mode=mode,
            snapshot_seed=snapshot_seed,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/station-detail")
def get_station_detail(
    station_id: str,
    mode: str = Query("time", pattern="^(time|batch)$"),
    slider_value: float = 0,
    snapshot_seed: int | None = None,
):
    if station_id not in STATIONS:
        raise HTTPException(status_code=404, detail="unknown station_id")
    try:
        return dashboard_service.station_detail(
            station_id,
            slider_value=slider_value,
            mode=mode,
            snapshot_seed=snapshot_seed,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
