import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_alert_service
from app.core.security import CurrentUser, ensure_company_access
from app.schemas.alert import AlertActionResponse, AlertActionUpdate, FinancialAlert
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


@router.put("/action", response_model=AlertActionResponse)
def update_alert_action(
    data: AlertActionUpdate,
    service: Service,
    user: CurrentUser,
) -> AlertActionResponse:
    ensure_company_access(user, data.company_id)
    return AlertActionResponse.model_validate(
        service.update_action(data, user.id), from_attributes=True
    )
