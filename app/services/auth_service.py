import uuid

from app.core.config import settings
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.user_audit_repository import UserAuditRepository
from app.repositories.user_repository import UserRepository
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


class AuthService:
    def __init__(
        self,
        repository: UserRepository,
        company_repository: CompanyRepository,
        audit_repository: UserAuditRepository,
    ) -> None:
        self.repository = repository
        self.company_repository = company_repository
        self.audit_repository = audit_repository

    def create_user(
        self,
        data: UserCreate,
        bootstrap: bool = False,
        actor_id: uuid.UUID | None = None,
    ) -> User:
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
        user = self.repository.create(
            User(
                name=data.name,
                email=data.email.lower(),
                password_hash=hash_password(data.password),
                role=data.role.value,
                company_id=data.company_id,
            )
        )
        self.audit_repository.create(
            actor_id,
            user.id,
            "user_created",
            {
                "name": {"from": None, "to": user.name},
                "email": {"from": None, "to": user.email},
                "role": {"from": None, "to": user.role},
                "company_id": {
                    "from": None,
                    "to": str(user.company_id) if user.company_id else None,
                },
                "is_active": {"from": None, "to": True},
            },
        )
        return user

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
        before = {
            "name": user.name,
            "role": user.role,
            "company_id": str(user.company_id) if user.company_id else None,
            "is_active": user.is_active,
        }
        updated = self.repository.update(user, data)
        after = {
            "name": updated.name,
            "role": updated.role,
            "company_id": str(updated.company_id) if updated.company_id else None,
            "is_active": updated.is_active,
        }
        changes = {
            field: {"from": before[field], "to": value}
            for field, value in after.items()
            if before[field] != value
        }
        if changes:
            self.audit_repository.create(actor_id, user_id, "user_updated", changes)
        return updated

    def list_audit_events(
        self,
        page: int,
        page_size: int,
        target_user_id: uuid.UUID | None,
        action: str | None,
    ) -> Page[UserAuditEventResponse]:
        events, total = self.audit_repository.list(
            page,
            page_size,
            target_user_id,
            action,
        )
        return Page[UserAuditEventResponse](
            items=events,
            total=total,
            page=page,
            page_size=page_size,
        )
