import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_analytics_service
from app.core.security import CurrentUser, ensure_company_access
from app.schemas.analytics import (
    CashFlowPoint,
    CategorySummary,
    ExecutiveSummary,
    MonthlyFinancialSummary,
    OverdueSummary,
)
from app.schemas.budget import BudgetComparison
from app.schemas.category import TransactionType
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])
Service = Annotated[AnalyticsService, Depends(get_analytics_service)]
DateQuery = Annotated[date, Query()]


@router.get("/executive-summary", response_model=ExecutiveSummary)
def executive_summary(
    company_id: uuid.UUID,
    start_date: DateQuery,
    end_date: DateQuery,
    service: Service,
    user: CurrentUser,
) -> ExecutiveSummary:
    ensure_company_access(user, company_id)
    return service.executive_summary(company_id, start_date, end_date)


@router.get("/monthly", response_model=list[MonthlyFinancialSummary])
def monthly_summary(
    company_id: uuid.UUID,
    start_date: DateQuery,
    end_date: DateQuery,
    service: Service,
    user: CurrentUser,
) -> list[MonthlyFinancialSummary]:
    ensure_company_access(user, company_id)
    return service.monthly_summary(company_id, start_date, end_date)


@router.get("/categories", response_model=list[CategorySummary])
def category_summary(
    company_id: uuid.UUID,
    start_date: DateQuery,
    end_date: DateQuery,
    service: Service,
    user: CurrentUser,
    transaction_type: TransactionType = TransactionType.EXPENSE,
) -> list[CategorySummary]:
    ensure_company_access(user, company_id)
    return service.category_summary(company_id, start_date, end_date, transaction_type)


@router.get("/cash-flow", response_model=list[CashFlowPoint])
def cash_flow(
    company_id: uuid.UUID,
    start_date: DateQuery,
    end_date: DateQuery,
    service: Service,
    user: CurrentUser,
) -> list[CashFlowPoint]:
    ensure_company_access(user, company_id)
    return service.cash_flow(company_id, start_date, end_date)


@router.get("/overdue", response_model=OverdueSummary)
def overdue_summary(
    company_id: uuid.UUID,
    start_date: DateQuery,
    end_date: DateQuery,
    service: Service,
    user: CurrentUser,
) -> OverdueSummary:
    ensure_company_access(user, company_id)
    return service.overdue_summary(company_id, start_date, end_date)


@router.get("/budget-comparison", response_model=list[BudgetComparison])
def budget_comparison(
    company_id: uuid.UUID,
    start_date: DateQuery,
    end_date: DateQuery,
    service: Service,
    user: CurrentUser,
) -> list[BudgetComparison]:
    ensure_company_access(user, company_id)
    return service.budget_comparison(company_id, start_date, end_date)
