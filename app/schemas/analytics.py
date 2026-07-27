import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class ExecutiveSummary(BaseModel):
    company_id: uuid.UUID
    start_date: date
    end_date: date
    realized_revenue: Decimal
    realized_expense: Decimal
    net_result: Decimal
    margin_percentage: Decimal | None
    pending_receivables: Decimal
    overdue_receivables: Decimal
    delinquency_rate_percentage: Decimal | None


class MonthlyFinancialSummary(BaseModel):
    reference_month: date
    total_revenue: Decimal
    total_expense: Decimal
    net_result: Decimal
    margin_percentage: Decimal | None


class CategorySummary(BaseModel):
    category_id: uuid.UUID
    category_name: str
    transaction_type: str
    total_amount: Decimal
    transaction_count: int = Field(ge=0)
    share_percentage: Decimal


class CashFlowPoint(BaseModel):
    reference_month: date
    inflows: Decimal
    outflows: Decimal
    net_cash_flow: Decimal
    accumulated_cash_flow: Decimal


class OverdueSummary(BaseModel):
    overdue_amount: Decimal
    overdue_count: int = Field(ge=0)
    average_days_overdue: Decimal | None
    delinquency_rate_percentage: Decimal | None


class ForecastMetric(BaseModel):
    mae: Decimal
    rmse: Decimal
    mape_percentage: Decimal | None
    validation_months: int = Field(ge=0)


class RevenueForecastPoint(BaseModel):
    reference_month: date
    predicted_revenue: Decimal = Field(ge=0)
    lower_bound: Decimal = Field(ge=0)
    upper_bound: Decimal = Field(ge=0)


class RevenueForecast(BaseModel):
    company_id: uuid.UUID
    training_start: date
    training_end: date
    method: str
    historical_months: int = Field(ge=0)
    metrics: ForecastMetric
    forecast: list[RevenueForecastPoint]
    limitation: str


class ExpenseAnomaly(BaseModel):
    transaction_id: uuid.UUID
    competence_date: date
    description: str
    category_id: uuid.UUID
    category_name: str
    amount: Decimal
    category_median: Decimal
    upper_threshold: Decimal
    deviation_percentage: Decimal
    explanation: str
