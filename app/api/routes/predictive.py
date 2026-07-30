import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_predictive_service
from app.core.security import CurrentUser, ensure_company_access
from app.schemas.analytics import ExpenseAnomaly, RevenueForecast
from app.services.predictive_service import PredictiveService

router = APIRouter(prefix="/predictive", tags=["predictive"])
Service = Annotated[PredictiveService, Depends(get_predictive_service)]
DateQuery = Annotated[date, Query()]


@router.get("/revenue-forecast", response_model=RevenueForecast)
def revenue_forecast(
    company_id: uuid.UUID,
    start_date: DateQuery,
    end_date: DateQuery,
    service: Service,
    user: CurrentUser,
    horizon: Annotated[int, Query(ge=1, le=6)] = 3,
) -> RevenueForecast:
    ensure_company_access(user, company_id)
    return service.revenue_forecast(company_id, start_date, end_date, horizon)


@router.get("/expense-anomalies", response_model=list[ExpenseAnomaly])
def expense_anomalies(
    company_id: uuid.UUID,
    start_date: DateQuery,
    end_date: DateQuery,
    service: Service,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ExpenseAnomaly]:
    ensure_company_access(user, company_id)
    return service.expense_anomalies(company_id, start_date, end_date, limit)
