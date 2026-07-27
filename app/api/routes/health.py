from typing import Literal

from fastapi import APIRouter
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


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
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
