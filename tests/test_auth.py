import uuid
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.core.exceptions import AppError, ConflictError
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    require_roles,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, UserCreate, UserRole
from app.services.auth_service import AuthService


def _service() -> tuple[AuthService, Mock]:
    repository = Mock()
    return AuthService(repository, Mock()), repository


def test_password_hash_is_salted_and_verifiable() -> None:
    first = hash_password("safe-password")
    second = hash_password("safe-password")
    assert first != second
    assert verify_password("safe-password", first)
    assert not verify_password("wrong-password", first)


def test_bootstrap_creates_first_admin() -> None:
    service, repository = _service()
    repository.count.return_value = 0
    repository.get_by_email.return_value = None
    repository.create.side_effect = lambda user: user
    data = UserCreate(
        name="Administrador",
        email="ADMIN@example.com",
        password="safe-password",
        role=UserRole.ADMIN,
    )
    user = service.create_user(data, bootstrap=True)
    assert user.email == "admin@example.com"
    assert user.role == "admin"
    assert verify_password("safe-password", user.password_hash)


def test_bootstrap_cannot_run_twice() -> None:
    service, repository = _service()
    repository.count.return_value = 1
    data = UserCreate(
        name="Administrador",
        email="admin@example.com",
        password="safe-password",
        role=UserRole.ADMIN,
    )
    with pytest.raises(ConflictError):
        service.create_user(data, bootstrap=True)


def test_non_admin_requires_company() -> None:
    service, repository = _service()
    repository.get_by_email.return_value = None
    data = UserCreate(
        name="Gestor",
        email="manager@example.com",
        password="safe-password",
        role=UserRole.MANAGER,
    )
    with pytest.raises(AppError, match="vinculados"):
        service.create_user(data)


def test_login_rejects_invalid_password() -> None:
    service, repository = _service()
    repository.get_by_email.return_value = SimpleNamespace(
        is_active=True,
        password_hash=hash_password("correct-password"),
    )
    with pytest.raises(AppError) as error:
        service.login(LoginRequest(email="user@example.com", password="wrong-password"))
    assert error.value.status_code == 401


def test_role_dependency_enforces_allowed_roles() -> None:
    dependency = require_roles(UserRole.ADMIN, UserRole.ANALYST)
    manager = SimpleNamespace(role="manager")
    with pytest.raises(AppError) as error:
        dependency(manager)
    assert error.value.status_code == 403
    analyst = SimpleNamespace(role="analyst")
    assert dependency(analyst) is analyst


def test_access_token_resolves_active_user() -> None:
    user = User(
        id=uuid.uuid4(),
        name="Admin",
        email="admin@example.com",
        password_hash="hash",
        role="admin",
        is_active=True,
    )
    token = create_access_token(user)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with patch("app.core.security.UserRepository") as repository_type:
        repository_type.return_value.get.return_value = user
        assert get_current_user(credentials, Mock()) is user


@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_current_user_rejects_missing_or_invalid_token(token: str | None) -> None:
    credentials = (
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token) if token else None
    )
    with pytest.raises(AppError) as error:
        get_current_user(credentials, Mock())
    assert error.value.status_code == 401


def test_current_user_rejects_inactive_user() -> None:
    user = User(
        id=uuid.uuid4(),
        name="Admin",
        email="admin@example.com",
        password_hash="hash",
        role="admin",
        is_active=False,
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=create_access_token(user)
    )
    with patch("app.core.security.UserRepository") as repository_type:
        repository_type.return_value.get.return_value = user
        with pytest.raises(AppError):
            get_current_user(credentials, Mock())


def test_auth_service_creates_company_user_and_logs_in() -> None:
    service, repository = _service()
    company_id = uuid.uuid4()
    service.company_repository.get.return_value = SimpleNamespace(id=company_id)
    repository.get_by_email.side_effect = [None, None]
    repository.create.side_effect = lambda user: user
    analyst = service.create_user(
        UserCreate(
            name="Analista",
            email="analyst@example.com",
            password="safe-password",
            role=UserRole.ANALYST,
            company_id=company_id,
        )
    )
    analyst.id = uuid.uuid4()
    analyst.is_active = True
    repository.get_by_email.side_effect = None
    repository.get_by_email.return_value = analyst
    token = service.login(LoginRequest(email=analyst.email, password="safe-password"))
    assert token.user.role == UserRole.ANALYST
    assert token.access_token
