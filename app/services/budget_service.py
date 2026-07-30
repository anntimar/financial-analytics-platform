import uuid
from datetime import date

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models.budget import Budget
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.company_repository import CompanyRepository
from app.schemas.budget import BudgetCreate, BudgetResponse, BudgetUpdate
from app.schemas.category import TransactionType
from app.schemas.common import Page


class BudgetService:
    def __init__(
        self,
        repository: BudgetRepository,
        company_repository: CompanyRepository,
        category_repository: CategoryRepository,
    ) -> None:
        self.repository = repository
        self.company_repository = company_repository
        self.category_repository = category_repository

    def create(self, data: BudgetCreate) -> Budget:
        if self.company_repository.get(data.company_id) is None:
            raise NotFoundError("Empresa")
        category = self.category_repository.get(data.category_id)
        if category is None:
            raise NotFoundError("Categoria")
        if category.company_id != data.company_id:
            raise AppError("A categoria não pertence à empresa informada.")
        if category.transaction_type != data.transaction_type:
            raise AppError("O tipo do orçamento deve ser igual ao tipo da categoria.")
        if self.repository.find_duplicate(data):
            raise ConflictError("Já existe orçamento para esta categoria e mês.")
        return self.repository.create(data)

    def get(self, budget_id: uuid.UUID) -> Budget:
        budget = self.repository.get(budget_id)
        if budget is None:
            raise NotFoundError("Orçamento")
        return budget

    def list(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        start_date: date | None,
        end_date: date | None,
        transaction_type: TransactionType | None,
    ) -> Page[BudgetResponse]:
        if start_date and end_date and start_date > end_date:
            raise AppError("start_date não pode ser posterior a end_date.")
        if self.company_repository.get(company_id) is None:
            raise NotFoundError("Empresa")
        items, total = self.repository.list(
            company_id, page, page_size, start_date, end_date, transaction_type
        )
        return Page[BudgetResponse](items=items, total=total, page=page, page_size=page_size)

    def update(self, budget_id: uuid.UUID, data: BudgetUpdate) -> Budget:
        return self.repository.update(self.get(budget_id), data)

    def delete(self, budget_id: uuid.UUID) -> None:
        self.repository.delete(self.get(budget_id))
