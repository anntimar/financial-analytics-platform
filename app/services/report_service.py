import csv
import io
import uuid
from datetime import UTC, date, datetime
from typing import Any

from app.core.exceptions import NotFoundError
from app.repositories.company_repository import CompanyRepository
from app.schemas.category import TransactionType
from app.schemas.report import ExecutiveReport
from app.services.alert_service import AlertService
from app.services.analytics_service import AnalyticsService


class ReportService:
    def __init__(
        self,
        analytics: AnalyticsService,
        alerts: AlertService,
        companies: CompanyRepository,
    ) -> None:
        self.analytics = analytics
        self.alerts = alerts
        self.companies = companies

    def executive(self, company_id: uuid.UUID, start_date: date, end_date: date) -> ExecutiveReport:
        company = self.companies.get(company_id)
        if company is None:
            raise NotFoundError("Empresa")
        return ExecutiveReport(
            company_id=company_id,
            company_name=company.name,
            start_date=start_date,
            end_date=end_date,
            generated_at=datetime.now(UTC),
            summary=self.analytics.executive_summary(company_id, start_date, end_date),
            monthly=self.analytics.monthly_summary(company_id, start_date, end_date),
            expense_categories=self.analytics.category_summary(
                company_id, start_date, end_date, TransactionType.EXPENSE
            ),
            cash_flow=self.analytics.cash_flow(company_id, start_date, end_date),
            overdue=self.analytics.overdue_summary(company_id, start_date, end_date),
            budget_comparison=self.analytics.budget_comparison(company_id, start_date, end_date),
            account_balances=self.analytics.account_balances(company_id, start_date, end_date),
            alerts=self.alerts.list_alerts(company_id, start_date, end_date),
        )

    @staticmethod
    def to_csv(report: ExecutiveReport) -> bytes:
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "section",
                "metric",
                "reference_date",
                "dimension",
                "value",
                "status",
                "note",
            ],
        )
        writer.writeheader()

        def row(
            section: str,
            metric: str,
            value: Any,
            reference_date: date | None = None,
            dimension: str = "",
            status: str = "",
            note: str = "",
        ) -> None:
            writer.writerow(
                {
                    "section": section,
                    "metric": metric,
                    "reference_date": reference_date or "",
                    "dimension": dimension,
                    "value": value if value is not None else "",
                    "status": status,
                    "note": note,
                }
            )

        summary = report.summary
        for metric in (
            "realized_revenue",
            "realized_expense",
            "net_result",
            "margin_percentage",
            "pending_receivables",
            "overdue_receivables",
            "delinquency_rate_percentage",
        ):
            row("summary", metric, getattr(summary, metric))
        for monthly_item in report.monthly:
            for metric in ("total_revenue", "total_expense", "net_result"):
                row(
                    "monthly",
                    metric,
                    getattr(monthly_item, metric),
                    monthly_item.reference_month,
                )
        for category_item in report.expense_categories:
            row(
                "expense_categories",
                "total_amount",
                category_item.total_amount,
                dimension=category_item.category_name,
            )
        for cash_item in report.cash_flow:
            row(
                "cash_flow",
                "accumulated_cash_flow",
                cash_item.accumulated_cash_flow,
                cash_item.reference_month,
            )
        row("overdue", "overdue_amount", report.overdue.overdue_amount)
        row(
            "overdue",
            "delinquency_rate_percentage",
            report.overdue.delinquency_rate_percentage,
        )
        for budget_item in report.budget_comparison:
            row(
                "budget_comparison",
                "variance_amount",
                budget_item.variance_amount,
                budget_item.reference_month,
                budget_item.category_name,
            )
        for account_item in report.account_balances:
            row(
                "account_balances",
                "current_balance",
                account_item.current_balance,
                dimension=account_item.account_name,
            )
        for alert in report.alerts:
            row(
                "alerts",
                alert.code,
                "",
                alert.reference_date,
                alert.title,
                alert.workflow_status,
                alert.workflow_note or alert.message,
            )
        return ("\ufeff" + output.getvalue()).encode()
