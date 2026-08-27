from __future__ import annotations

from fastapi import APIRouter, Depends

from app.app_state import AppState, get_app_state
from app.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health(state: AppState = Depends(get_app_state)) -> HealthResponse:
    return HealthResponse(data_initialized=True)
