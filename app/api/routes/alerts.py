import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_alert_service
from app.core.security import CurrentUser, ensure_company_access
from app.schemas.alert import FinancialAlert
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])
Service = Annotated[AlertService, Depends(get_alert_service)]
DateQuery = Annotated[date, Query()]


@router.get("", response_model=list[FinancialAlert])
def list_alerts(
    company_id: uuid.UUID,
    start_date: DateQuery,
    end_date: DateQuery,
    service: Service,
    user: CurrentUser,
) -> list[FinancialAlert]:
    ensure_company_access(user, company_id)
    return service.list_alerts(company_id, start_date, end_date)
