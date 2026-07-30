import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_auth_service
from app.core.security import CurrentUser, require_roles
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserAuditEventResponse,
    UserCreate,
    UserResponse,
    UserRole,
    UserUpdate,
)
from app.schemas.common import Page
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
Service = Annotated[AuthService, Depends(get_auth_service)]
Admin = Annotated[object, Depends(require_roles(UserRole.ADMIN))]


@router.post("/bootstrap", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def bootstrap(data: UserCreate, service: Service) -> UserResponse:
    return UserResponse.model_validate(service.create_user(data, bootstrap=True))


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, service: Service) -> TokenResponse:
    return service.login(data)


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    service: Service,
    admin: CurrentUser,
    _admin: Admin,
) -> UserResponse:
    return UserResponse.model_validate(service.create_user(data, actor_id=admin.id))


@router.get("/users", response_model=Page[UserResponse])
def list_users(
    service: Service,
    _admin: Admin,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    company_id: uuid.UUID | None = None,
    active_only: bool = False,
) -> Page[UserResponse]:
    return service.list_users(page, page_size, company_id, active_only)


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    service: Service,
    admin: CurrentUser,
    _admin: Admin,
) -> UserResponse:
    return UserResponse.model_validate(service.update_user(user_id, data, admin.id))


@router.get("/audit-events", response_model=Page[UserAuditEventResponse])
def list_audit_events(
    service: Service,
    _admin: Admin,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    target_user_id: uuid.UUID | None = None,
    action: str | None = None,
) -> Page[UserAuditEventResponse]:
    return service.list_audit_events(page, page_size, target_user_id, action)
