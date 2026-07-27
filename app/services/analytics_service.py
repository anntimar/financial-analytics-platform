import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.core.exceptions import AppError, NotFoundError
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.company_repository import CompanyRepository
from app.schemas.analytics import (
    CashFlowPoint,
    CategorySummary,
    ExecutiveSummary,
    MonthlyFinancialSummary,
    OverdueSummary,
)
from app.schemas.budget import BudgetComparison
from app.schemas.category import TransactionType

HUNDRED = Decimal("100")
TWO_PLACES = Decimal("0.01")


def percentage(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator == 0:
        return None
    return ((numerator / denominator) * HUNDRED).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class AnalyticsService:
    def __init__(
        self,
        repository: AnalyticsRepository,
        company_repository: CompanyRepository,
    ) -> None:
        self.repository = repository
        self.company_repository = company_repository

    def _validate(self, company_id: uuid.UUID, start_date: date, end_date: date) -> None:
        if start_date > end_date:
            raise AppError("start_date não pode ser posterior a end_date.")
        if self.company_repository.get(company_id) is None:
            raise NotFoundError("Empresa")

    def executive_summary(
        self, company_id: uuid.UUID, start_date: date, end_date: date
    ) -> ExecutiveSummary:
        self._validate(company_id, start_date, end_date)
        row = self.repository.executive_summary(company_id, start_date, end_date)
        revenue = Decimal(row["realized_revenue"])
        expense = Decimal(row["realized_expense"])
        overdue = Decimal(row["overdue_receivables"])
        total_receivables = Decimal(row["total_receivables"])
        net_result = revenue - expense
        return ExecutiveSummary(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
            realized_revenue=revenue,
            realized_expense=expense,
            net_result=net_result,
            margin_percentage=percentage(net_result, revenue),
            pending_receivables=Decimal(row["pending_receivables"]),
            overdue_receivables=overdue,
            delinquency_rate_percentage=percentage(overdue, total_receivables),
        )

    def monthly_summary(
        self, company_id: uuid.UUID, start_date: date, end_date: date
    ) -> list[MonthlyFinancialSummary]:
        self._validate(company_id, start_date, end_date)
        result = []
        for row in self.repository.monthly_summary(company_id, start_date, end_date):
            revenue = Decimal(row["total_revenue"])
            expense = Decimal(row["total_expense"])
            net_result = revenue - expense
            result.append(
                MonthlyFinancialSummary(
                    reference_month=row["reference_month"],
                    total_revenue=revenue,
                    total_expense=expense,
                    net_result=net_result,
                    margin_percentage=percentage(net_result, revenue),
                )
            )
        return result

    def category_summary(
        self,
        company_id: uuid.UUID,
        start_date: date,
        end_date: date,
        transaction_type: TransactionType,
    ) -> list[CategorySummary]:
        self._validate(company_id, start_date, end_date)
        rows = self.repository.category_summary(company_id, start_date, end_date, transaction_type)
        grand_total = sum((Decimal(row["total_amount"]) for row in rows), start=Decimal(0))
        return [
            CategorySummary(
                category_id=row["category_id"],
                category_name=row["category_name"],
                transaction_type=row["transaction_type"],
                total_amount=Decimal(row["total_amount"]),
                transaction_count=row["transaction_count"],
                share_percentage=percentage(Decimal(row["total_amount"]), grand_total)
                or Decimal(0),
            )
            for row in rows
        ]

    def cash_flow(
        self, company_id: uuid.UUID, start_date: date, end_date: date
    ) -> list[CashFlowPoint]:
        self._validate(company_id, start_date, end_date)
        accumulated = Decimal(0)
        result = []
        for row in self.repository.cash_flow(company_id, start_date, end_date):
            inflows = Decimal(row["inflows"])
            outflows = Decimal(row["outflows"])
            net_cash_flow = inflows - outflows
            accumulated += net_cash_flow
            result.append(
                CashFlowPoint(
                    reference_month=row["reference_month"],
                    inflows=inflows,
                    outflows=outflows,
                    net_cash_flow=net_cash_flow,
                    accumulated_cash_flow=accumulated,
                )
            )
        return result

    def overdue_summary(
        self, company_id: uuid.UUID, start_date: date, end_date: date
    ) -> OverdueSummary:
        self._validate(company_id, start_date, end_date)
        row = self.repository.overdue_summary(company_id, start_date, end_date)
        overdue = Decimal(row["overdue_amount"])
        total = Decimal(row["total_receivables"])
        average = row["average_days_overdue"]
        return OverdueSummary(
            overdue_amount=overdue,
            overdue_count=row["overdue_count"],
            average_days_overdue=Decimal(str(average)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            if average is not None
            else None,
            delinquency_rate_percentage=percentage(overdue, total),
        )

    def budget_comparison(
        self, company_id: uuid.UUID, start_date: date, end_date: date
    ) -> list[BudgetComparison]:
        self._validate(company_id, start_date, end_date)
        result = []
        for row in self.repository.budget_comparison(company_id, start_date, end_date):
            planned = Decimal(row["planned_amount"])
            realized = Decimal(row["realized_amount"])
            variance = realized - planned
            result.append(
                BudgetComparison(
                    reference_month=row["reference_month"],
                    category_id=row["category_id"],
                    category_name=row["category_name"],
                    transaction_type=row["transaction_type"],
                    planned_amount=planned,
                    realized_amount=realized,
                    variance_amount=variance,
                    variance_percentage=percentage(variance, planned),
                )
            )
        return result
