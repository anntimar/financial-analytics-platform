import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_account_service, get_analytics_service
from app.core.exceptions import ConflictError, NotFoundError
from app.main import app
from app.repositories.account_repository import AccountRepository
from app.schemas.account import (
    AccountBalance,
    AccountCreate,
    AccountResponse,
    AccountType,
    AccountUpdate,
)
from app.services.account_service import AccountService
from dashboard.api_client import FinAnalyticsClient


def account_data() -> AccountCreate:
    return AccountCreate(
        company_id=uuid.uuid4(),
        name="Conta principal",
        account_type=AccountType.CHECKING,
        institution="Banco Demo",
        opening_balance=Decimal("1000"),
    )


def account_object(data: AccountCreate) -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid.uuid4(),
        **data.model_dump(),
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def test_account_service_full_lifecycle() -> None:
    data = account_data()
    account = account_object(data)
    repository = Mock()
    repository.find_by_name.return_value = None
    repository.create.return_value = account
    repository.get.return_value = account
    repository.list.return_value = ([account], 1)
    repository.update.return_value = account
    companies = Mock()
    companies.get.return_value = SimpleNamespace(id=data.company_id)
    service = AccountService(repository, companies)

    assert service.create(data) is account
    assert service.get(account.id) is account
    assert service.list(data.company_id, 1, 20, True).total == 1
    assert service.update(account.id, AccountUpdate(name="Nova conta")) is account
    assert service.deactivate(account.id) is account


def test_account_service_validation_failures() -> None:
    data = account_data()
    repository = Mock()
    companies = Mock()
    service = AccountService(repository, companies)

    companies.get.return_value = None
    with pytest.raises(NotFoundError):
        service.create(data)
    companies.get.return_value = SimpleNamespace(id=data.company_id)
    repository.find_by_name.return_value = SimpleNamespace(id=uuid.uuid4())
    with pytest.raises(ConflictError):
        service.create(data)
    repository.get.return_value = None
    with pytest.raises(NotFoundError):
        service.get(uuid.uuid4())
    companies.get.return_value = None
    with pytest.raises(NotFoundError):
        service.list(uuid.uuid4(), 1, 20, True)


def test_account_service_rejects_duplicate_rename() -> None:
    data = account_data()
    account = account_object(data)
    repository = Mock()
    repository.get.return_value = account
    repository.find_by_name.return_value = SimpleNamespace(id=uuid.uuid4())
    service = AccountService(repository, Mock())

    with pytest.raises(ConflictError):
        service.update(account.id, AccountUpdate(name="Duplicada"))


def test_account_repository_queries_and_updates() -> None:
    data = account_data()
    session = MagicMock()
    session.scalar.side_effect = [None, 1]
    session.scalars.return_value = []
    repository = AccountRepository(session)

    created = repository.create(data)
    repository.get(created.id)
    assert repository.find_by_name(data.company_id, data.name) is None
    assert repository.list(data.company_id, 1, 20, True) == ([], 1)
    repository.update(created, AccountUpdate(institution="Outro banco"))
    assert created.institution == "Outro banco"


def test_account_routes_full_lifecycle() -> None:
    data = account_data()
    account = account_object(data)
    service = Mock()
    service.create.return_value = account
    service.get.return_value = account
    service.update.return_value = account
    service.deactivate.return_value = account
    service.list.return_value = {
        "items": [AccountResponse.model_validate(account)],
        "total": 1,
        "page": 1,
        "page_size": 20,
    }
    app.dependency_overrides[get_account_service] = lambda: service

    with TestClient(app) as client:
        created = client.post("/api/v1/accounts", json=data.model_dump(mode="json"))
        listed = client.get("/api/v1/accounts", params={"company_id": str(data.company_id)})
        fetched = client.get(f"/api/v1/accounts/{account.id}")
        updated = client.patch(f"/api/v1/accounts/{account.id}", json={"name": "Conta atualizada"})
        deleted = client.delete(f"/api/v1/accounts/{account.id}")

    assert [created.status_code, listed.status_code, fetched.status_code] == [201, 200, 200]
    assert updated.status_code == 200
    assert deleted.status_code == 200


def test_account_balances_endpoint() -> None:
    company_id = uuid.uuid4()
    service = Mock()
    service.account_balances.return_value = [
        AccountBalance(
            account_id=uuid.uuid4(),
            account_name="Conta",
            account_type=AccountType.CHECKING,
            opening_balance=Decimal("100"),
            inflows=Decimal("50"),
            outflows=Decimal("20"),
            current_balance=Decimal("130"),
        )
    ]
    app.dependency_overrides[get_analytics_service] = lambda: service
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/analytics/account-balances",
            params={
                "company_id": str(company_id),
                "start_date": date(2026, 1, 1).isoformat(),
                "end_date": date(2026, 12, 31).isoformat(),
            },
        )
    assert response.status_code == 200
    assert response.json()[0]["current_balance"] == "130"


def test_dashboard_client_requests_account_balances() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/analytics/account-balances"
        return httpx.Response(200, json=[])

    client = FinAnalyticsClient("http://test", transport=httpx.MockTransport(handler))
    assert client.account_balances(uuid.uuid4(), date(2026, 1, 1), date(2026, 12, 31)) == []
