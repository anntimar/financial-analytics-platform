import uuid

from app.core.config import settings
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserRole,
    UserUpdate,
)
from app.schemas.common import Page


class AuthService:
    def __init__(
        self,
        repository: UserRepository,
        company_repository: CompanyRepository,
    ) -> None:
        self.repository = repository
        self.company_repository = company_repository

    def create_user(self, data: UserCreate, bootstrap: bool = False) -> User:
        if bootstrap:
            if self.repository.count() != 0:
                raise ConflictError("O administrador inicial já foi configurado.")
            if data.role != UserRole.ADMIN:
                raise AppError("O primeiro usuário deve possuir perfil admin.")
        if self.repository.get_by_email(data.email) is not None:
            raise ConflictError("Já existe um usuário com este e-mail.")
        if data.company_id and self.company_repository.get(data.company_id) is None:
            raise AppError("Empresa informada não existe.")
        if data.role != UserRole.ADMIN and data.company_id is None:
            raise AppError("Analistas e gestores devem estar vinculados a uma empresa.")
        return self.repository.create(
            User(
                name=data.name,
                email=data.email.lower(),
                password_hash=hash_password(data.password),
                role=data.role.value,
                company_id=data.company_id,
            )
        )

    def login(self, data: LoginRequest) -> TokenResponse:
        user = self.repository.get_by_email(data.email)
        if (
            user is None
            or not user.is_active
            or not verify_password(data.password, user.password_hash)
        ):
            raise AppError("E-mail ou senha inválidos.", status_code=401)
        return TokenResponse(
            access_token=create_access_token(user),
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserResponse.model_validate(user),
        )

    def list_users(
        self,
        page: int,
        page_size: int,
        company_id: uuid.UUID | None,
        active_only: bool,
    ) -> Page[UserResponse]:
        if company_id and self.company_repository.get(company_id) is None:
            raise NotFoundError("Empresa")
        users, total = self.repository.list(page, page_size, company_id, active_only)
        return Page[UserResponse](items=users, total=total, page=page, page_size=page_size)

    def update_user(
        self,
        user_id: uuid.UUID,
        data: UserUpdate,
        actor_id: uuid.UUID,
    ) -> User:
        user = self.repository.get(user_id)
        if user is None:
            raise NotFoundError("Usuário")
        if data.is_active is False and user_id == actor_id:
            raise AppError("Você não pode desativar o próprio acesso.")
        target_role = data.role or UserRole(user.role)
        target_company_id = (
            data.company_id if "company_id" in data.model_fields_set else user.company_id
        )
        if target_company_id and self.company_repository.get(target_company_id) is None:
            raise NotFoundError("Empresa")
        if target_role != UserRole.ADMIN and target_company_id is None:
            raise AppError("Analistas e gestores devem estar vinculados a uma empresa.")
        if target_role == UserRole.ADMIN and "company_id" not in data.model_fields_set:
            data = data.model_copy(update={"company_id": None})
        return self.repository.update(user, data)
