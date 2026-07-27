import uuid

from app.core.exceptions import ConflictError, NotFoundError
from app.models.category import Category
from app.repositories.category_repository import CategoryRepository
from app.repositories.company_repository import CompanyRepository
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate, TransactionType
from app.schemas.common import Page


class CategoryService:
    def __init__(
        self,
        repository: CategoryRepository,
        company_repository: CompanyRepository,
    ) -> None:
        self.repository = repository
        self.company_repository = company_repository

    def create(self, data: CategoryCreate) -> Category:
        if self.company_repository.get(data.company_id) is None:
            raise NotFoundError("Empresa")
        if self.repository.find_duplicate(data):
            raise ConflictError("Esta categoria já existe para a empresa.")
        return self.repository.create(data)

    def get(self, category_id: uuid.UUID) -> Category:
        category = self.repository.get(category_id)
        if category is None:
            raise NotFoundError("Categoria")
        return category

    def list(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        transaction_type: TransactionType | None,
    ) -> Page[CategoryResponse]:
        if self.company_repository.get(company_id) is None:
            raise NotFoundError("Empresa")
        categories, total = self.repository.list(company_id, page, page_size, transaction_type)
        return Page[CategoryResponse](items=categories, total=total, page=page, page_size=page_size)

    def update(self, category_id: uuid.UUID, data: CategoryUpdate) -> Category:
        return self.repository.update(self.get(category_id), data)

    def deactivate(self, category_id: uuid.UUID) -> Category:
        return self.repository.update(self.get(category_id), CategoryUpdate(is_active=False))
