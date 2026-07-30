import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import httpx
from fastapi.testclient import TestClient

from app.api.dependencies import get_alert_service
from app.main import app
from app.schemas.account import AccountBalance, AccountType
from app.schemas.alert import AlertSeverity, FinancialAlert
from app.schemas.analytics import ExecutiveSummary
from app.schemas.budget import BudgetComparison
from app.schemas.category import TransactionType
from app.services.alert_service import AlertService
from dashboard.api_client import FinAnalyticsClient

START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 12, 31)


def summary(
    company_id: uuid.UUID,
    net_result: str = "100",
    delinquency: str | None = "0",
) -> ExecutiveSummary:
    return ExecutiveSummary(
        company_id=company_id,
        start_date=START_DATE,
        end_date=END_DATE,
        realized_revenue=Decimal("1000"),
        realized_expense=Decimal("900"),
        net_result=Decimal(net_result),
        margin_percentage=Decimal("10"),
        pending_receivables=Decimal("0"),
        overdue_receivables=Decimal("0"),
        delinquency_rate_percentage=Decimal(delinquency) if delinquency else None,
    )


def comparison(
    transaction_type: TransactionType,
    variance: str | None,
    name: str = "Categoria",
) -> BudgetComparison:
    return BudgetComparison(
        reference_month=START_DATE,
        category_id=uuid.uuid4(),
        category_name=name,
        transaction_type=transaction_type,
        planned_amount=Decimal("100"),
        realized_amount=Decimal("120"),
        variance_amount=Decimal("20"),
        variance_percentage=Decimal(variance) if variance else None,
    )


def balance(value: str) -> AccountBalance:
    return AccountBalance(
        account_id=uuid.uuid4(),
        account_name="Conta principal",
        account_type=AccountType.CHECKING,
        opening_balance=Decimal("0"),
        inflows=Decimal("0"),
        outflows=Decimal("0"),
        current_balance=Decimal(value),
    )


def test_alert_service_consolidates_and_sorts_risks() -> None:
    company_id = uuid.uuid4()
    analytics = Mock()
    analytics.executive_summary.return_value = summary(company_id, "-50", "7")
    analytics.budget_comparison.return_value = [
        comparison(TransactionType.EXPENSE, "25", "Marketing"),
        comparison(TransactionType.REVENUE, "-15", "Vendas"),
    ]
    analytics.account_balances.return_value = [balance("-10"), balance("20")]

    alerts = AlertService(analytics).list_alerts(company_id, START_DATE, END_DATE)

    assert len(alerts) == 5
    assert [alert.severity for alert in alerts] == [
        AlertSeverity.CRITICAL,
        AlertSeverity.CRITICAL,
        AlertSeverity.CRITICAL,
        AlertSeverity.WARNING,
        AlertSeverity.WARNING,
    ]
    assert {alert.code.split(":")[0] for alert in alerts} == {
        "negative_net_result",
        "high_delinquency",
        "budget_deviation",
        "negative_account_balance",
    }


def test_alert_service_handles_limits_and_healthy_values() -> None:
    company_id = uuid.uuid4()
    analytics = Mock()
    analytics.executive_summary.return_value = summary(company_id, "0", "10")
    analytics.budget_comparison.return_value = [
        comparison(TransactionType.EXPENSE, "10"),
        comparison(TransactionType.REVENUE, "-20"),
        comparison(TransactionType.EXPENSE, "-50"),
        comparison(TransactionType.REVENUE, "50"),
        comparison(TransactionType.EXPENSE, None),
    ]
    analytics.account_balances.return_value = [balance("0")]

    alerts = AlertService(analytics).list_alerts(company_id, START_DATE, END_DATE)

    assert [alert.severity for alert in alerts].count(AlertSeverity.CRITICAL) == 2
    assert [alert.severity for alert in alerts].count(AlertSeverity.WARNING) == 1
    assert all(alert.context for alert in alerts)


def test_alert_service_returns_empty_for_healthy_period() -> None:
    company_id = uuid.uuid4()
    analytics = Mock()
    analytics.executive_summary.return_value = summary(company_id, "100", None)
    analytics.budget_comparison.return_value = []
    analytics.account_balances.return_value = []

    assert AlertService(analytics).list_alerts(company_id, START_DATE, END_DATE) == []


def test_alerts_endpoint() -> None:
    company_id = uuid.uuid4()
    service = Mock()
    service.list_alerts.return_value = [
        FinancialAlert(
            code="high_delinquency",
            severity=AlertSeverity.WARNING,
            title="Inadimplência elevada",
            message="A taxa atingiu 7%.",
            reference_date=END_DATE,
            context={"rate": Decimal("7")},
        )
    ]
    app.dependency_overrides[get_alert_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/alerts",
            params={
                "company_id": str(company_id),
                "start_date": START_DATE.isoformat(),
                "end_date": END_DATE.isoformat(),
            },
        )

    assert response.status_code == 200
    assert response.json()[0]["severity"] == "warning"
    service.list_alerts.assert_called_once_with(company_id, START_DATE, END_DATE)


def test_dashboard_client_requests_alerts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/alerts"
        assert request.url.params["company_id"] == str(company_id)
        return httpx.Response(200, json=[])

    company_id = uuid.uuid4()
    client = FinAnalyticsClient("http://test", transport=httpx.MockTransport(handler))

    assert client.alerts(company_id, START_DATE, END_DATE) == []
