from app.core.config import settings
from app.core.exceptions import AppError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserResponse, UserRole


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
