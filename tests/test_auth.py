import uuid
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.core.exceptions import AppError, ConflictError
from app.core.security import (
    create_access_token,
    ensure_company_access,
    get_current_user,
    hash_password,
    require_roles,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, UserCreate, UserRole, UserUpdate
from app.services.auth_service import AuthService


def _service() -> tuple[AuthService, Mock]:
    repository = Mock()
    return AuthService(repository, Mock(), Mock()), repository


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


def test_company_access_allows_admin_and_own_company() -> None:
    company_id = uuid.uuid4()
    ensure_company_access(SimpleNamespace(role="admin", company_id=None), company_id)
    ensure_company_access(
        SimpleNamespace(role="manager", company_id=company_id),
        company_id,
    )


def test_company_access_rejects_cross_tenant_and_unassigned_user() -> None:
    company_id = uuid.uuid4()
    for assigned_company in (uuid.uuid4(), None):
        with pytest.raises(AppError) as error:
            ensure_company_access(
                SimpleNamespace(role="analyst", company_id=assigned_company),
                company_id,
            )
        assert error.value.status_code == 403


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


def test_admin_lists_users_with_company_filter() -> None:
    service, repository = _service()
    company_id = uuid.uuid4()
    service.company_repository.get.return_value = SimpleNamespace(id=company_id)
    repository.list.return_value = ([], 0)

    result = service.list_users(2, 10, company_id, active_only=True)

    assert result.page == 2
    assert result.total == 0
    repository.list.assert_called_once_with(2, 10, company_id, True)


def test_user_update_changes_role_company_and_status() -> None:
    service, repository = _service()
    user_id = uuid.uuid4()
    company_id = uuid.uuid4()
    user = SimpleNamespace(
        id=user_id,
        company_id=None,
        name="Admin antigo",
        role="admin",
        is_active=True,
    )
    repository.get.return_value = user
    repository.update.side_effect = lambda record, data: record
    service.company_repository.get.return_value = SimpleNamespace(id=company_id)

    result = service.update_user(
        user_id,
        UserUpdate(
            name="Gestor novo",
            role=UserRole.MANAGER,
            company_id=company_id,
            is_active=False,
        ),
        actor_id=uuid.uuid4(),
    )

    assert result is user
    update = repository.update.call_args.args[1]
    assert update.role == UserRole.MANAGER
    assert update.company_id == company_id


def test_user_update_rejects_self_deactivation_and_missing_company() -> None:
    service, repository = _service()
    user_id = uuid.uuid4()
    repository.get.return_value = SimpleNamespace(
        id=user_id,
        company_id=None,
        role="admin",
        is_active=True,
    )

    with pytest.raises(AppError, match="próprio acesso"):
        service.update_user(user_id, UserUpdate(is_active=False), actor_id=user_id)
    with pytest.raises(AppError, match="vinculados"):
        service.update_user(
            user_id,
            UserUpdate(role=UserRole.ANALYST),
            actor_id=uuid.uuid4(),
        )


def test_promoting_user_to_admin_removes_company() -> None:
    service, repository = _service()
    user_id = uuid.uuid4()
    repository.get.return_value = SimpleNamespace(
        id=user_id,
        name="Gestor",
        company_id=uuid.uuid4(),
        role="manager",
        is_active=True,
    )
    repository.update.side_effect = lambda user, data: user

    service.update_user(
        user_id,
        UserUpdate(role=UserRole.ADMIN),
        actor_id=uuid.uuid4(),
    )

    assert repository.update.call_args.args[1].company_id is None


def test_user_creation_records_audit_without_password() -> None:
    service, repository = _service()
    actor_id = uuid.uuid4()
    user_id = uuid.uuid4()
    repository.get_by_email.return_value = None

    def create(user: User) -> User:
        user.id = user_id
        return user

    repository.create.side_effect = create
    service.create_user(
        UserCreate(
            name="Administrador",
            email="audit@example.com",
            password="safe-password",
            role=UserRole.ADMIN,
        ),
        actor_id=actor_id,
    )

    audit_call = service.audit_repository.create.call_args
    assert audit_call.args[:3] == (actor_id, user_id, "user_created")
    assert "password" not in audit_call.args[3]


def test_user_update_records_only_changed_fields() -> None:
    service, repository = _service()
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        name="Gestor",
        email="manager@example.com",
        password_hash="hash",
        role="manager",
        company_id=uuid.uuid4(),
        is_active=True,
    )
    repository.get.return_value = user

    def update(record: User, data: UserUpdate) -> User:
        record.name = data.name or record.name
        return record

    repository.update.side_effect = update
    service.update_user(
        user_id,
        UserUpdate(name="Gestor Financeiro"),
        actor_id=uuid.uuid4(),
    )

    changes = service.audit_repository.create.call_args.args[3]
    assert changes == {"name": {"from": "Gestor", "to": "Gestor Financeiro"}}


def test_admin_lists_audit_events() -> None:
    service, _repository = _service()
    service.audit_repository.list.return_value = ([], 0)

    result = service.list_audit_events(1, 20, None, "user_updated")

    assert result.total == 0
    service.audit_repository.list.assert_called_once_with(1, 20, None, "user_updated")
