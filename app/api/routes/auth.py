from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_auth_service
from app.core.security import CurrentUser, require_roles
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserResponse, UserRole
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
def create_user(data: UserCreate, service: Service, _admin: Admin) -> UserResponse:
    return UserResponse.model_validate(service.create_user(data))
