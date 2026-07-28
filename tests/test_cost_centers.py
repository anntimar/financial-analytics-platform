import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_cost_center_service
from app.core.exceptions import ConflictError, NotFoundError
from app.main import app
from app.repositories.cost_center_repository import CostCenterRepository
from app.schemas.cost_center import CostCenterCreate, CostCenterResponse, CostCenterUpdate
from app.services.cost_center_service import CostCenterService


def payload() -> CostCenterCreate:
    return CostCenterCreate(company_id=uuid.uuid4(), name="Marketing", code="MKT")


def item(data: CostCenterCreate) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        **data.model_dump(),
        is_active=True,
        created_at=datetime.now(UTC),
    )


def test_cost_center_service_lifecycle_and_validation() -> None:
    data = payload()
    center = item(data)
    repository = Mock()
    repository.find_duplicate.return_value = None
    repository.create.return_value = center
    repository.get.return_value = center
    repository.list.return_value = ([center], 1)
    repository.update.return_value = center
    companies = Mock()
    companies.get.return_value = SimpleNamespace(id=data.company_id)
    service = CostCenterService(repository, companies)

    assert service.create(data) is center
    assert service.get(center.id) is center
    assert service.list(data.company_id, 1, 20).total == 1
    assert service.update(center.id, CostCenterUpdate(name="Growth")) is center
    assert service.deactivate(center.id) is center

    companies.get.return_value = None
    with pytest.raises(NotFoundError):
        service.create(data)
    with pytest.raises(NotFoundError):
        service.list(data.company_id, 1, 20)
    repository.get.return_value = None
    with pytest.raises(NotFoundError):
        service.get(uuid.uuid4())
    companies.get.return_value = SimpleNamespace(id=data.company_id)
    repository.find_duplicate.return_value = center
    with pytest.raises(ConflictError):
        service.create(data)


def test_cost_center_repository_and_routes() -> None:
    data = payload()
    session = MagicMock()
    repository = CostCenterRepository(session)
    session.scalar.side_effect = [None, 1]
    session.scalars.return_value = []
    created = repository.create(data)
    repository.get(created.id)
    assert repository.find_duplicate(data) is None
    assert repository.list(data.company_id, 1, 20) == ([], 1)
    repository.update(created, CostCenterUpdate(name="Growth"))
    assert created.name == "Growth"

    center = item(data)
    service = Mock()
    service.create.return_value = center
    service.get.return_value = center
    service.update.return_value = center
    service.list.return_value = {
        "items": [CostCenterResponse.model_validate(center)],
        "total": 1,
        "page": 1,
        "page_size": 20,
    }
    app.dependency_overrides[get_cost_center_service] = lambda: service
    with TestClient(app) as client:
        responses = [
            client.post("/api/v1/cost-centers", json=data.model_dump(mode="json")),
            client.get("/api/v1/cost-centers", params={"company_id": str(data.company_id)}),
            client.get(f"/api/v1/cost-centers/{center.id}"),
            client.patch(f"/api/v1/cost-centers/{center.id}", json={"name": "Growth"}),
            client.delete(f"/api/v1/cost-centers/{center.id}"),
        ]
    assert [response.status_code for response in responses] == [201, 200, 200, 200, 204]
