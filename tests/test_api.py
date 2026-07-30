import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_auth_service, get_company_service
from app.core.exceptions import ConflictError
from app.main import app
from app.schemas.auth import UserResponse, UserRole
from app.schemas.common import Page
from app.schemas.company import CompanyResponse


def company_record() -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid.uuid4(),
        name="Empresa Demo",
        trade_name="Demo",
        document_number="12345678000199",
        industry="Tecnologia",
        city="Fortaleza",
        state="CE",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_company(client: TestClient) -> None:
    service = Mock()
    record = company_record()
    service.create.return_value = record
    app.dependency_overrides[get_company_service] = lambda: service

    response = client.post(
        "/api/v1/companies",
        json={
            "name": "Empresa Demo",
            "trade_name": "Demo",
            "document_number": "12345678000199",
            "industry": "Tecnologia",
            "city": "Fortaleza",
            "state": "ce",
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == str(record.id)
    assert response.json()["state"] == "CE"
    service.create.assert_called_once()


def test_list_companies_returns_page(client: TestClient) -> None:
    service = Mock()
    item = CompanyResponse.model_validate(company_record())
    service.list.return_value = Page[CompanyResponse](items=[item], total=1, page=1, page_size=20)
    app.dependency_overrides[get_company_service] = lambda: service

    response = client.get("/api/v1/companies")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["name"] == "Empresa Demo"


def test_application_error_is_returned_as_json(client: TestClient) -> None:
    service = Mock()
    service.create.side_effect = ConflictError("Documento duplicado.")
    app.dependency_overrides[get_company_service] = lambda: service

    response = client.post(
        "/api/v1/companies",
        json={"name": "Empresa Demo", "document_number": "12345678000199"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Documento duplicado."}


def test_paid_transaction_requires_payment_date(client: TestClient) -> None:
    response = client.post(
        "/api/v1/transactions",
        json={
            "company_id": str(uuid.uuid4()),
            "category_id": str(uuid.uuid4()),
            "transaction_type": "revenue",
            "description": "Venda à vista",
            "amount": "1500.00",
            "competence_date": "2026-07-01",
            "status": "paid",
        },
    )

    assert response.status_code == 422
    assert "payment_date é obrigatória" in response.text


def test_pagination_rejects_page_size_over_limit(client: TestClient) -> None:
    response = client.get("/api/v1/companies?page_size=101")
    assert response.status_code == 422


def test_admin_lists_and_updates_users(client: TestClient) -> None:
    service = Mock()
    user_id = uuid.uuid4()
    user = UserResponse(
        id=user_id,
        company_id=None,
        name="Administrador",
        email="admin@example.com",
        role=UserRole.ADMIN,
        is_active=True,
    )
    service.list_users.return_value = Page[UserResponse](
        items=[user],
        total=1,
        page=1,
        page_size=20,
    )
    service.update_user.return_value = user
    app.dependency_overrides[get_auth_service] = lambda: service

    response = client.get("/api/v1/auth/users?active_only=true")
    assert response.status_code == 200
    assert response.json()["items"][0]["email"] == "admin@example.com"

    response = client.patch(
        f"/api/v1/auth/users/{user_id}",
        json={"name": "Administrador", "role": "admin", "is_active": True},
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(user_id)
    service.update_user.assert_called_once()

    service.list_audit_events.return_value = Page(items=[], total=0, page=1, page_size=20)
    response = client.get("/api/v1/auth/audit-events?action=user_updated")
    assert response.status_code == 200
    assert response.json()["total"] == 0
