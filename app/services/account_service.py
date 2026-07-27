import uuid

from app.core.exceptions import ConflictError, NotFoundError
from app.models.account import Account
from app.repositories.account_repository import AccountRepository
from app.repositories.company_repository import CompanyRepository
from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate
from app.schemas.common import Page


class AccountService:
    def __init__(
        self, repository: AccountRepository, company_repository: CompanyRepository
    ) -> None:
        self.repository = repository
        self.company_repository = company_repository

    def create(self, data: AccountCreate) -> Account:
        if self.company_repository.get(data.company_id) is None:
            raise NotFoundError("Empresa")
        if self.repository.find_by_name(data.company_id, data.name):
            raise ConflictError("Já existe uma conta com este nome para a empresa.")
        return self.repository.create(data)

    def get(self, account_id: uuid.UUID) -> Account:
        account = self.repository.get(account_id)
        if account is None:
            raise NotFoundError("Conta")
        return account

    def list(
        self, company_id: uuid.UUID, page: int, page_size: int, active_only: bool
    ) -> Page[AccountResponse]:
        if self.company_repository.get(company_id) is None:
            raise NotFoundError("Empresa")
        accounts, total = self.repository.list(company_id, page, page_size, active_only)
        return Page[AccountResponse](items=accounts, total=total, page=page, page_size=page_size)

    def update(self, account_id: uuid.UUID, data: AccountUpdate) -> Account:
        account = self.get(account_id)
        if (
            data.name
            and data.name.lower() != account.name.lower()
            and self.repository.find_by_name(account.company_id, data.name)
        ):
            raise ConflictError("Já existe uma conta com este nome para a empresa.")
        return self.repository.update(account, data)

    def deactivate(self, account_id: uuid.UUID) -> Account:
        return self.repository.update(self.get(account_id), AccountUpdate(is_active=False))
