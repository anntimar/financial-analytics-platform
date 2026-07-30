import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_alert_service
from app.core.exceptions import AppError, NotFoundError
from app.main import app
from app.repositories.alert_action_repository import AlertActionRepository
from app.schemas.account import AccountBalance, AccountType
from app.schemas.alert import (
    AlertActionResponse,
    AlertActionUpdate,
    AlertSeverity,
    AlertWorkflowStatus,
    FinancialAlert,
)
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


def test_alert_service_applies_and_updates_workflow() -> None:
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    analytics = Mock()
    analytics.executive_summary.return_value = summary(company_id, "-50", "0")
    analytics.budget_comparison.return_value = []
    analytics.account_balances.return_value = []
    repository = Mock()
    action = SimpleNamespace(
        alert_code="negative_net_result",
        reference_date=END_DATE,
        status=AlertWorkflowStatus.ACKNOWLEDGED,
        note="Em análise",
        updated_at=datetime.now(UTC),
    )
    repository.list_for_period.return_value = [action]
    repository.get.return_value = action
    repository.save.return_value = action
    service = AlertService(analytics, repository)

    alerts = service.list_alerts(company_id, START_DATE, END_DATE)
    assert alerts[0].workflow_status == AlertWorkflowStatus.ACKNOWLEDGED
    assert alerts[0].workflow_note == "Em análise"

    data = AlertActionUpdate(
        company_id=company_id,
        alert_code="negative_net_result",
        reference_date=END_DATE,
        period_start=START_DATE,
        period_end=END_DATE,
        status=AlertWorkflowStatus.RESOLVED,
        note="Plano executado",
    )
    assert service.update_action(data, user_id) is action
    repository.save.assert_called_once()


def test_alert_action_rejects_invalid_period_missing_alert_and_repository() -> None:
    company_id = uuid.uuid4()
    data = AlertActionUpdate(
        company_id=company_id,
        alert_code="missing",
        reference_date=END_DATE,
        period_start=END_DATE,
        period_end=START_DATE,
        status=AlertWorkflowStatus.OPEN,
    )
    service = AlertService(Mock())
    with pytest.raises(AppError, match="period_start"):
        service.update_action(data, uuid.uuid4())

    valid_data = data.model_copy(update={"period_start": START_DATE, "period_end": END_DATE})
    with pytest.raises(AppError, match="indisponível"):
        service.update_action(valid_data, uuid.uuid4())

    repository = Mock()
    repository.list_for_period.return_value = []
    analytics = Mock()
    analytics.executive_summary.return_value = summary(company_id)
    analytics.budget_comparison.return_value = []
    analytics.account_balances.return_value = []
    with pytest.raises(NotFoundError):
        AlertService(analytics, repository).update_action(valid_data, uuid.uuid4())


def test_alert_action_repository_lists_creates_and_updates() -> None:
    session = MagicMock()
    repository = AlertActionRepository(session)
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session.scalars.return_value = []
    session.scalar.return_value = None

    assert repository.list_for_period(company_id, START_DATE, END_DATE) == []
    assert repository.get(company_id, "code", END_DATE) is None
    created = repository.save(
        None,
        company_id,
        "code",
        END_DATE,
        AlertWorkflowStatus.ACKNOWLEDGED,
        "Nota",
        user_id,
    )
    assert created.status == AlertWorkflowStatus.ACKNOWLEDGED
    repository.save(
        created,
        company_id,
        "code",
        END_DATE,
        AlertWorkflowStatus.RESOLVED,
        "Resolvido",
        user_id,
    )
    assert created.status == AlertWorkflowStatus.RESOLVED
    assert session.commit.call_count == 2


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


def test_alert_action_endpoint() -> None:
    company_id = uuid.uuid4()
    action = SimpleNamespace(
        id=uuid.uuid4(),
        company_id=company_id,
        alert_code="high_delinquency",
        reference_date=END_DATE,
        status=AlertWorkflowStatus.RESOLVED,
        note="Cobrança concluída",
        updated_by=uuid.uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    service = Mock()
    service.update_action.return_value = action
    app.dependency_overrides[get_alert_service] = lambda: service
    payload = AlertActionUpdate(
        company_id=company_id,
        alert_code=action.alert_code,
        reference_date=END_DATE,
        period_start=START_DATE,
        period_end=END_DATE,
        status=AlertWorkflowStatus.RESOLVED,
        note=action.note,
    )

    with TestClient(app) as client:
        response = client.put(
            "/api/v1/alerts/action",
            json=payload.model_dump(mode="json"),
        )

    assert response.status_code == 200
    assert AlertActionResponse.model_validate(response.json()).status == "resolved"


def test_dashboard_client_requests_alerts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/alerts"
        assert request.url.params["company_id"] == str(company_id)
        return httpx.Response(200, json=[])

    company_id = uuid.uuid4()
    client = FinAnalyticsClient("http://test", transport=httpx.MockTransport(handler))

    assert client.alerts(company_id, START_DATE, END_DATE) == []


def test_dashboard_client_updates_alert_action() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/alerts/action"
        assert request.method == "PUT"
        return httpx.Response(200, json={"status": "resolved"})

    client = FinAnalyticsClient("http://test", transport=httpx.MockTransport(handler))
    response = client.update_alert_action(
        uuid.uuid4(),
        "alert-code",
        END_DATE,
        START_DATE,
        END_DATE,
        "resolved",
        "Tratado",
    )
    assert response["status"] == "resolved"
