from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import engine

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    database: Literal["connected", "unavailable"]
    version: str


class LivenessResponse(BaseModel):
    status: Literal["alive"]
    version: str


def database_is_ready() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    if not database_is_ready():
        return HealthResponse(
            status="degraded",
            database="unavailable",
            version=settings.app_version,
        )

    return HealthResponse(
        status="healthy",
        database="connected",
        version=settings.app_version,
    )


@router.get("/live", response_model=LivenessResponse)
def liveness_check() -> LivenessResponse:
    return LivenessResponse(status="alive", version=settings.app_version)


@router.get("/ready", response_model=HealthResponse)
def readiness_check(response: Response) -> HealthResponse:
    result = health_check()
    if result.status == "degraded":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
