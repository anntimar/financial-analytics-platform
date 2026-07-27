import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.dependencies import get_budget_service
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.main import app
from app.repositories.budget_repository import BudgetRepository
from app.schemas.budget import BudgetCreate, BudgetResponse, BudgetUpdate
from app.schemas.category import TransactionType
from app.services.budget_service import BudgetService
from dashboard.api_client import FinAnalyticsClient


def budget_data() -> BudgetCreate:
    return BudgetCreate(
        company_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        transaction_type=TransactionType.EXPENSE,
        reference_month=date(2026, 7, 1),
        amount=Decimal("1000"),
    )


def budget_object(data: BudgetCreate) -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid.uuid4(),
        **data.model_dump(),
        created_at=now,
        updated_at=now,
    )


def test_budget_schema_requires_first_day_of_month() -> None:
    with pytest.raises(ValidationError, match="primeiro dia"):
        BudgetCreate(
            **{
                **budget_data().model_dump(),
                "reference_month": date(2026, 7, 2),
            }
        )


def test_budget_service_full_lifecycle() -> None:
    data = budget_data()
    budget = budget_object(data)
    repository = Mock()
    repository.find_duplicate.return_value = None
    repository.create.return_value = budget
    repository.get.return_value = budget
    repository.list.return_value = ([budget], 1)
    repository.update.return_value = budget
    company_repository = Mock()
    company_repository.get.return_value = SimpleNamespace(id=data.company_id)
    category_repository = Mock()
    category_repository.get.return_value = SimpleNamespace(
        id=data.category_id,
        company_id=data.company_id,
        transaction_type=data.transaction_type,
    )
    service = BudgetService(repository, company_repository, category_repository)

    assert service.create(data) is budget
    assert service.get(budget.id) is budget
    assert service.list(data.company_id, 1, 20, None, None, None).total == 1
    assert service.update(budget.id, BudgetUpdate(amount=Decimal("1200"))) is budget
    service.delete(budget.id)
    repository.delete.assert_called_once_with(budget)


def test_budget_service_validates_relationships_and_duplicates() -> None:
    data = budget_data()
    repository = Mock()
    companies = Mock()
    categories = Mock()
    service = BudgetService(repository, companies, categories)

    companies.get.return_value = None
    with pytest.raises(NotFoundError):
        service.create(data)

    companies.get.return_value = SimpleNamespace(id=data.company_id)
    categories.get.return_value = None
    with pytest.raises(NotFoundError):
        service.create(data)

    categories.get.return_value = SimpleNamespace(
        company_id=uuid.uuid4(), transaction_type=data.transaction_type
    )
    with pytest.raises(AppError, match="não pertence"):
        service.create(data)

    categories.get.return_value = SimpleNamespace(
        company_id=data.company_id, transaction_type=TransactionType.REVENUE
    )
    with pytest.raises(AppError, match="tipo"):
        service.create(data)

    categories.get.return_value = SimpleNamespace(
        company_id=data.company_id, transaction_type=data.transaction_type
    )
    repository.find_duplicate.return_value = SimpleNamespace(id=uuid.uuid4())
    with pytest.raises(ConflictError):
        service.create(data)


def test_budget_service_list_and_get_failures() -> None:
    service = BudgetService(Mock(), Mock(), Mock())
    service.repository.get.return_value = None
    with pytest.raises(NotFoundError):
        service.get(uuid.uuid4())
    with pytest.raises(AppError, match="start_date"):
        service.list(uuid.uuid4(), 1, 20, date(2026, 12, 1), date(2026, 1, 1), None)
    service.company_repository.get.return_value = None
    with pytest.raises(NotFoundError):
        service.list(uuid.uuid4(), 1, 20, None, None, None)


def test_budget_repository_builds_queries_and_mutations() -> None:
    session = MagicMock()
    repository = BudgetRepository(session)
    data = budget_data()
    session.scalar.side_effect = [None, 1]
    session.scalars.return_value = []

    created = repository.create(data)
    assert created.amount == Decimal("1000")
    repository.get(created.id)
    assert repository.find_duplicate(data) is None
    assert repository.list(
        data.company_id, 1, 20, date(2026, 1, 1), date(2026, 12, 1), data.transaction_type
    ) == ([], 1)
    repository.update(created, BudgetUpdate(amount=Decimal("900")))
    assert created.amount == Decimal("900")
    repository.delete(created)
    assert session.commit.call_count == 3


def test_budget_routes_create_list_update_and_delete() -> None:
    data = budget_data()
    budget = budget_object(data)
    service = Mock()
    service.create.return_value = budget
    service.get.return_value = budget
    service.update.return_value = budget
    service.list.return_value = {
        "items": [BudgetResponse.model_validate(budget)],
        "total": 1,
        "page": 1,
        "page_size": 20,
    }
    app.dependency_overrides[get_budget_service] = lambda: service

    with TestClient(app) as client:
        created = client.post("/api/v1/budgets", json=data.model_dump(mode="json"))
        listed = client.get("/api/v1/budgets", params={"company_id": str(data.company_id)})
        updated = client.patch(f"/api/v1/budgets/{budget.id}", json={"amount": "1200.00"})
        deleted = client.delete(f"/api/v1/budgets/{budget.id}")

    assert created.status_code == 201
    assert listed.status_code == 200
    assert updated.status_code == 200
    assert deleted.status_code == 204


def test_dashboard_client_requests_budget_comparison() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/analytics/budget-comparison"
        assert request.url.params["company_id"]
        return httpx.Response(200, json=[])

    client = FinAnalyticsClient(
        "http://test",
        transport=httpx.MockTransport(handler),
    )
    assert client.budget_comparison(uuid.uuid4(), date(2026, 1, 1), date(2026, 12, 31)) == []
