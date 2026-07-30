import uuid
from datetime import date
from decimal import Decimal

from app.core.exceptions import AppError, NotFoundError
from app.models.category import Category
from app.models.transaction import Transaction
from app.repositories.account_repository import AccountRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.category import TransactionType
from app.schemas.common import Page
from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionStatus,
    TransactionUpdate,
)


class TransactionService:
    def __init__(
        self,
        repository: TransactionRepository,
        company_repository: CompanyRepository,
        category_repository: CategoryRepository,
        account_repository: AccountRepository | None = None,
    ) -> None:
        self.repository = repository
        self.company_repository = company_repository
        self.category_repository = category_repository
        self.account_repository = account_repository

    def _validate_account(self, account_id: uuid.UUID, company_id: uuid.UUID) -> None:
        account = self.account_repository.get(account_id) if self.account_repository else None
        if account is None:
            raise NotFoundError("Conta")
        if account.company_id != company_id:
            raise AppError("A conta não pertence à empresa informada.")
        if not account.is_active:
            raise AppError("A conta informada está inativa.")

    def _validate_category(
        self,
        category_id: uuid.UUID,
        company_id: uuid.UUID,
        transaction_type: TransactionType,
    ) -> Category:
        category = self.category_repository.get(category_id)
        if category is None:
            raise NotFoundError("Categoria")
        if category.company_id != company_id:
            raise AppError("A categoria não pertence à empresa informada.")
        if category.transaction_type != transaction_type:
            raise AppError("O tipo da categoria não corresponde ao tipo da transação.")
        return category

    def create(self, data: TransactionCreate) -> Transaction:
        if self.company_repository.get(data.company_id) is None:
            raise NotFoundError("Empresa")
        self._validate_category(data.category_id, data.company_id, data.transaction_type)
        if data.account_id:
            self._validate_account(data.account_id, data.company_id)
        return self.repository.create(data)

    def get(self, transaction_id: uuid.UUID) -> Transaction:
        transaction = self.repository.get(transaction_id)
        if transaction is None:
            raise NotFoundError("Transação")
        return transaction

    def list(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        start_date: date | None,
        end_date: date | None,
        transaction_type: TransactionType | None,
        category_id: uuid.UUID | None,
        status: TransactionStatus | None,
        minimum_amount: Decimal | None,
        maximum_amount: Decimal | None,
        account_id: uuid.UUID | None = None,
    ) -> Page[TransactionResponse]:
        if start_date and end_date and start_date > end_date:
            raise AppError("start_date não pode ser posterior a end_date.")
        if (
            minimum_amount is not None
            and maximum_amount is not None
            and minimum_amount > maximum_amount
        ):
            raise AppError("minimum_amount não pode ser maior que maximum_amount.")
        transactions, total = self.repository.list(
            company_id=company_id,
            page=page,
            page_size=page_size,
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type,
            category_id=category_id,
            account_id=account_id,
            status=status,
            minimum_amount=minimum_amount,
            maximum_amount=maximum_amount,
        )
        return Page[TransactionResponse](
            items=transactions, total=total, page=page, page_size=page_size
        )

    def update(self, transaction_id: uuid.UUID, data: TransactionUpdate) -> Transaction:
        transaction = self.get(transaction_id)
        if data.account_id:
            self._validate_account(data.account_id, transaction.company_id)
        if data.category_id:
            self._validate_category(
                data.category_id,
                transaction.company_id,
                TransactionType(transaction.transaction_type),
            )
        if data.status == TransactionStatus.PAID:
            payment_date = data.payment_date or transaction.payment_date
            if payment_date is None:
                raise AppError("payment_date é obrigatória para transações pagas.")
        return self.repository.update(transaction, data)

    def delete(self, transaction_id: uuid.UUID) -> None:
        self.repository.delete(self.get(transaction_id))
