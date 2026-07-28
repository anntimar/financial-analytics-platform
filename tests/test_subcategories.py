import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_subcategory_service
from app.core.exceptions import ConflictError, NotFoundError
from app.main import app
from app.repositories.subcategory_repository import SubcategoryRepository
from app.schemas.subcategory import (
    SubcategoryCreate,
    SubcategoryResponse,
    SubcategoryUpdate,
)
from app.services.subcategory_service import SubcategoryService


def data() -> SubcategoryCreate:
    return SubcategoryCreate(category_id=uuid.uuid4(), name="Tráfego pago")


def object_for(payload: SubcategoryCreate) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        **payload.model_dump(),
        is_active=True,
        created_at=datetime.now(UTC),
    )


def test_subcategory_service_full_lifecycle() -> None:
    payload = data()
    subcategory = object_for(payload)
    repository = Mock()
    repository.find_duplicate.return_value = None
    repository.create.return_value = subcategory
    repository.get.return_value = subcategory
    repository.list.return_value = ([subcategory], 1)
    repository.update.return_value = subcategory
    categories = Mock()
    categories.get.return_value = SimpleNamespace(id=payload.category_id)
    service = SubcategoryService(repository, categories)

    assert service.create(payload) is subcategory
    assert service.get(subcategory.id) is subcategory
    assert service.list(payload.category_id, 1, 20).total == 1
    assert service.update(subcategory.id, SubcategoryUpdate(name="Mídia")) is subcategory
    assert service.deactivate(subcategory.id) is subcategory


def test_subcategory_service_validates_relationships_and_duplicates() -> None:
    payload = data()
    repository = Mock()
    categories = Mock()
    service = SubcategoryService(repository, categories)
    categories.get.return_value = None
    with pytest.raises(NotFoundError):
        service.create(payload)
    with pytest.raises(NotFoundError):
        service.list(payload.category_id, 1, 20)

    categories.get.return_value = SimpleNamespace(id=payload.category_id)
    repository.find_duplicate.return_value = SimpleNamespace(id=uuid.uuid4())
    with pytest.raises(ConflictError):
        service.create(payload)

    repository.get.return_value = None
    with pytest.raises(NotFoundError):
        service.get(uuid.uuid4())


def test_subcategory_repository_queries_and_mutations() -> None:
    payload = data()
    session = MagicMock()
    repository = SubcategoryRepository(session)
    session.scalar.side_effect = [None, 1]
    session.scalars.return_value = []

    created = repository.create(payload)
    assert created.name == payload.name
    repository.get(created.id)
    assert repository.find_duplicate(payload) is None
    assert repository.list(payload.category_id, 1, 20) == ([], 1)
    repository.update(created, SubcategoryUpdate(name="Mídia paga"))
    assert created.name == "Mídia paga"
    assert session.commit.call_count == 2


def test_subcategory_routes_full_lifecycle() -> None:
    payload = data()
    subcategory = object_for(payload)
    category = SimpleNamespace(id=payload.category_id, company_id=uuid.uuid4())
    service = Mock()
    service.categories.get.return_value = category
    service.create.return_value = subcategory
    service.get.return_value = subcategory
    service.update.return_value = subcategory
    service.deactivate.return_value = subcategory
    service.list.return_value = {
        "items": [SubcategoryResponse.model_validate(subcategory)],
        "total": 1,
        "page": 1,
        "page_size": 20,
    }
    app.dependency_overrides[get_subcategory_service] = lambda: service

    with TestClient(app) as client:
        created = client.post("/api/v1/subcategories", json=payload.model_dump(mode="json"))
        listed = client.get(
            "/api/v1/subcategories", params={"category_id": str(payload.category_id)}
        )
        fetched = client.get(f"/api/v1/subcategories/{subcategory.id}")
        updated = client.patch(
            f"/api/v1/subcategories/{subcategory.id}", json={"name": "Mídia paga"}
        )
        deleted = client.delete(f"/api/v1/subcategories/{subcategory.id}")

    assert [created.status_code, listed.status_code, fetched.status_code] == [201, 200, 200]
    assert updated.status_code == 200
    assert deleted.status_code == 204


def test_subcategory_access_detects_missing_parent() -> None:
    payload = data()
    subcategory = object_for(payload)
    service = Mock()
    service.get.return_value = subcategory
    service.categories.get.return_value = None
    app.dependency_overrides[get_subcategory_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(f"/api/v1/subcategories/{subcategory.id}")

    assert response.status_code == 404
