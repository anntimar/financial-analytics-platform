import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.account import AccountBalance
from app.schemas.alert import FinancialAlert
from app.schemas.analytics import (
    CashFlowPoint,
    CategorySummary,
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
    cash_flow: list[CashFlowPoint]
    overdue: OverdueSummary
    budget_comparison: list[BudgetComparison]
    account_balances: list[AccountBalance]
    alerts: list[FinancialAlert]
