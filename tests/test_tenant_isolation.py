import uuid
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api.dependencies import get_analytics_service, get_company_service
from app.api.routes.analytics import (
    cash_flow,
    category_summary,
    monthly_summary,
    overdue_summary,
)
from app.api.routes.categories import list_categories
from app.api.routes.imports import list_imports
from app.api.routes.predictive import expense_anomalies
from app.api.routes.transactions import list_transactions
from app.core.security import get_current_user
from app.main import app
from app.schemas.category import TransactionType


def test_analytics_rejects_access_to_another_company() -> None:
    assigned_company = uuid.uuid4()
    requested_company = uuid.uuid4()
    user = SimpleNamespace(role="manager", company_id=assigned_company)
    service = Mock()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_analytics_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/analytics/executive-summary",
            params={
                "company_id": str(requested_company),
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado aos dados desta empresa."
    service.executive_summary.assert_not_called()


def test_manager_company_list_contains_only_assigned_company() -> None:
    company_id = uuid.uuid4()
    now = datetime.now(UTC)
    company = SimpleNamespace(
        id=company_id,
        name="Empresa Permitida",
        trade_name=None,
        document_number=None,
        industry=None,
        city=None,
        state=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    user = SimpleNamespace(role="manager", company_id=company_id)
    service = Mock()
    service.get.return_value = company
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_company_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/api/v1/companies")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == str(company_id)
    service.list.assert_not_called()


def test_own_company_is_forwarded_to_read_services() -> None:
    company_id = uuid.uuid4()
    user = SimpleNamespace(role="manager", company_id=company_id)
    service = Mock()
    service.monthly_summary.return_value = []
    service.category_summary.return_value = []
    service.cash_flow.return_value = []
    service.overdue_summary.return_value = SimpleNamespace()
    service.expense_anomalies.return_value = []
    service.list.return_value = SimpleNamespace()
    start = date(2026, 1, 1)
    end = date(2026, 12, 31)

    assert monthly_summary(company_id, start, end, service, user) == []
    assert (
        category_summary(
            company_id,
            start,
            end,
            service,
            user,
            TransactionType.EXPENSE,
        )
        == []
    )
    assert cash_flow(company_id, start, end, service, user) == []
    assert (
        overdue_summary(company_id, start, end, service, user)
        is service.overdue_summary.return_value
    )
    assert expense_anomalies(company_id, start, end, service, user, 20) == []
    assert list_categories(company_id, service, user) is service.list.return_value
    assert list_imports(company_id, service, user) is service.list.return_value
    assert (
        list_transactions(
            company_id,
            service,
            user,
            1,
            20,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )
        is service.list.return_value
    )
