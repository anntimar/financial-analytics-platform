import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
from fastapi.testclient import TestClient

from app.api.dependencies import get_report_service
from app.core.exceptions import NotFoundError
from app.main import app
from app.schemas.account import AccountBalance, AccountType
from app.schemas.alert import AlertSeverity, AlertWorkflowStatus, FinancialAlert
from app.schemas.analytics import (
    CashFlowPoint,
    CategorySummary,
    ExecutiveSummary,
    MonthlyFinancialSummary,
    OverdueSummary,
)
from app.schemas.budget import BudgetComparison
from app.schemas.category import TransactionType
from app.schemas.report import ExecutiveReport
from app.services.report_service import ReportService
from dashboard.api_client import FinAnalyticsClient

START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 12, 31)


def report_data(company_id: uuid.UUID) -> ExecutiveReport:
    category_id = uuid.uuid4()
    return ExecutiveReport(
        company_id=company_id,
        company_name="Empresa Demo",
        start_date=START_DATE,
        end_date=END_DATE,
        generated_at=datetime.now(UTC),
        summary=ExecutiveSummary(
            company_id=company_id,
            start_date=START_DATE,
            end_date=END_DATE,
            realized_revenue=Decimal("1000"),
            realized_expense=Decimal("600"),
            net_result=Decimal("400"),
            margin_percentage=Decimal("40"),
            pending_receivables=Decimal("100"),
            overdue_receivables=Decimal("50"),
            delinquency_rate_percentage=Decimal("5"),
        ),
        monthly=[
            MonthlyFinancialSummary(
                reference_month=START_DATE,
                total_revenue=Decimal("1000"),
                total_expense=Decimal("600"),
                net_result=Decimal("400"),
                margin_percentage=Decimal("40"),
            )
        ],
        expense_categories=[
            CategorySummary(
                category_id=category_id,
                category_name="Pessoal",
                transaction_type="expense",
                total_amount=Decimal("600"),
                transaction_count=2,
                share_percentage=Decimal("100"),
            )
        ],
        cash_flow=[
            CashFlowPoint(
                reference_month=START_DATE,
                inflows=Decimal("1000"),
                outflows=Decimal("600"),
                net_cash_flow=Decimal("400"),
                accumulated_cash_flow=Decimal("400"),
            )
        ],
        overdue=OverdueSummary(
            overdue_amount=Decimal("50"),
            overdue_count=1,
            average_days_overdue=Decimal("10"),
            delinquency_rate_percentage=Decimal("5"),
        ),
        budget_comparison=[
            BudgetComparison(
                reference_month=START_DATE,
                category_id=category_id,
                category_name="Pessoal",
                transaction_type=TransactionType.EXPENSE,
                planned_amount=Decimal("500"),
                realized_amount=Decimal("600"),
                variance_amount=Decimal("100"),
                variance_percentage=Decimal("20"),
            )
        ],
        account_balances=[
            AccountBalance(
                account_id=uuid.uuid4(),
                account_name="Conta principal",
                account_type=AccountType.CHECKING,
                opening_balance=Decimal("0"),
                inflows=Decimal("1000"),
                outflows=Decimal("600"),
                current_balance=Decimal("400"),
            )
        ],
        alerts=[
            FinancialAlert(
                code="high_delinquency",
                severity=AlertSeverity.WARNING,
                title="Inadimplência elevada",
                message="Taxa acima do esperado.",
                reference_date=END_DATE,
                context={"rate": 5},
                workflow_status=AlertWorkflowStatus.ACKNOWLEDGED,
                workflow_note="Cobrança iniciada",
            )
        ],
    )


def test_report_service_consolidates_sections_and_exports_csv() -> None:
    company_id = uuid.uuid4()
    expected = report_data(company_id)
    analytics = Mock()
    analytics.executive_summary.return_value = expected.summary
    analytics.monthly_summary.return_value = expected.monthly
    analytics.category_summary.return_value = expected.expense_categories
    analytics.cash_flow.return_value = expected.cash_flow
    analytics.overdue_summary.return_value = expected.overdue
    analytics.budget_comparison.return_value = expected.budget_comparison
    analytics.account_balances.return_value = expected.account_balances
    alerts = Mock()
    alerts.list_alerts.return_value = expected.alerts
    companies = Mock()
    companies.get.return_value = SimpleNamespace(name="Empresa Demo")
    service = ReportService(analytics, alerts, companies)

    report = service.executive(company_id, START_DATE, END_DATE)
    csv_content = service.to_csv(report).decode("utf-8-sig")

    assert report.company_name == "Empresa Demo"
    assert "summary,net_result" in csv_content
    assert "expense_categories,total_amount" in csv_content
    assert "cash_flow,accumulated_cash_flow" in csv_content
    assert "budget_comparison,variance_amount" in csv_content
    assert "account_balances,current_balance" in csv_content
    assert "alerts,high_delinquency" in csv_content


def test_report_service_requires_company() -> None:
    companies = Mock()
    companies.get.return_value = None
    service = ReportService(Mock(), Mock(), companies)

    try:
        service.executive(uuid.uuid4(), START_DATE, END_DATE)
    except NotFoundError as exc:
        assert "Empresa" in str(exc)
    else:
        raise AssertionError("NotFoundError esperado")


def test_report_routes_return_json_and_csv() -> None:
    company_id = uuid.uuid4()
    service = Mock()
    service.executive.return_value = report_data(company_id)
    app.dependency_overrides[get_report_service] = lambda: service
    params = {
        "company_id": str(company_id),
        "start_date": START_DATE.isoformat(),
        "end_date": END_DATE.isoformat(),
    }

    with TestClient(app) as client:
        json_response = client.get("/api/v1/reports/executive", params=params)
        csv_response = client.get("/api/v1/reports/executive.csv", params=params)

    assert json_response.status_code == 200
    assert json_response.json()["company_name"] == "Empresa Demo"
    assert csv_response.status_code == 200
    assert csv_response.content.startswith(b"\xef\xbb\xbf")
    assert "attachment" in csv_response.headers["content-disposition"]


def test_dashboard_client_downloads_reports() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(".csv"):
            return httpx.Response(200, content=b"csv")
        return httpx.Response(200, json={"company_name": "Empresa Demo"})

    client = FinAnalyticsClient("http://test", transport=httpx.MockTransport(handler))
    company_id = uuid.uuid4()

    assert (
        client.executive_report(company_id, START_DATE, END_DATE)["company_name"] == "Empresa Demo"
    )
    assert client.executive_report_csv(company_id, START_DATE, END_DATE) == b"csv"
