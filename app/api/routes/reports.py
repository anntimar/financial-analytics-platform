import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.api.dependencies import get_report_service
from app.core.security import CurrentUser, ensure_company_access
from app.schemas.report import ExecutiveReport
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])
Service = Annotated[ReportService, Depends(get_report_service)]
DateQuery = Annotated[date, Query()]


@router.get("/executive", response_model=ExecutiveReport)
def executive_report(
    company_id: uuid.UUID,
    start_date: DateQuery,
    end_date: DateQuery,
    service: Service,
    user: CurrentUser,
) -> ExecutiveReport:
    ensure_company_access(user, company_id)
    return service.executive(company_id, start_date, end_date)


@router.get("/executive.csv")
def executive_report_csv(
    company_id: uuid.UUID,
    start_date: DateQuery,
    end_date: DateQuery,
    service: Service,
    user: CurrentUser,
) -> Response:
    ensure_company_access(user, company_id)
    report = service.executive(company_id, start_date, end_date)
    filename = f"relatorio-executivo-{company_id}-{start_date}-{end_date}.csv"
    return Response(
        ReportService.to_csv(report),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
