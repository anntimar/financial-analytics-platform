import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.account import AccountBalance
from app.schemas.alert import FinancialAlert
from app.schemas.analytics import (
    CashFlowPoint,
    CategorySummary,
    CostCenterSummary,
    ExecutiveSummary,
    MonthlyFinancialSummary,
    OverdueSummary,
)
from app.schemas.budget import BudgetComparison


class ExecutiveReport(BaseModel):
    company_id: uuid.UUID
    company_name: str
    start_date: date
    end_date: date
    generated_at: datetime
    summary: ExecutiveSummary
    monthly: list[MonthlyFinancialSummary]
    expense_categories: list[CategorySummary]
    cost_centers: list[CostCenterSummary] = Field(default_factory=list)
    cash_flow: list[CashFlowPoint]
    overdue: OverdueSummary
    budget_comparison: list[BudgetComparison]
    account_balances: list[AccountBalance]
    alerts: list[FinancialAlert]
