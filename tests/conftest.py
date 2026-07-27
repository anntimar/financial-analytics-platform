import uuid
from collections.abc import Iterator
from types import SimpleNamespace

import pytest

from app.core.security import get_current_user
from app.main import app


@pytest.fixture(autouse=True)
def authenticated_user() -> Iterator[None]:
    user = SimpleNamespace(
        id=uuid.uuid4(),
        company_id=None,
        name="Usuário de Teste",
        email="test@example.com",
        role="admin",
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()
