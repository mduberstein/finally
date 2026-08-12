"""Liveness check, used by Docker and the deployment platform."""

from fastapi import APIRouter

from .schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")
