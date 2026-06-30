from fastapi import APIRouter, Query

from app.dependencies import dashboard_service

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard-data")
def get_dashboard_data(
    mode: str = Query("time", pattern="^(time|batch)$"),
    slider_value: float = Query(0),
    anchor_batch_id: str | None = Query(None),
):
    return dashboard_service.dashboard_payload(slider_value=slider_value, mode=mode, anchor_batch_id=anchor_batch_id)
