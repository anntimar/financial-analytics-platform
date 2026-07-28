import uuid

from app.core.exceptions import ConflictError, NotFoundError
from app.models.subcategory import Subcategory
from app.repositories.category_repository import CategoryRepository
from app.repositories.subcategory_repository import SubcategoryRepository
from app.schemas.common import Page
from app.schemas.subcategory import (
    SubcategoryCreate,
    SubcategoryResponse,
    SubcategoryUpdate,
)


class SubcategoryService:
    def __init__(
        self,
        repository: SubcategoryRepository,
        categories: CategoryRepository,
    ) -> None:
        self.repository = repository
        self.categories = categories

    def create(self, data: SubcategoryCreate) -> Subcategory:
        if self.categories.get(data.category_id) is None:
            raise NotFoundError("Categoria")
        if self.repository.find_duplicate(data):
            raise ConflictError("Esta subcategoria já existe para a categoria.")
        return self.repository.create(data)

    def get(self, subcategory_id: uuid.UUID) -> Subcategory:
        subcategory = self.repository.get(subcategory_id)
        if subcategory is None:
            raise NotFoundError("Subcategoria")
        return subcategory

    def list(self, category_id: uuid.UUID, page: int, page_size: int) -> Page[SubcategoryResponse]:
        if self.categories.get(category_id) is None:
            raise NotFoundError("Categoria")
        items, total = self.repository.list(category_id, page, page_size)
        return Page[SubcategoryResponse](items=items, total=total, page=page, page_size=page_size)

    def update(self, subcategory_id: uuid.UUID, data: SubcategoryUpdate) -> Subcategory:
        return self.repository.update(self.get(subcategory_id), data)

    def deactivate(self, subcategory_id: uuid.UUID) -> Subcategory:
        return self.repository.update(self.get(subcategory_id), SubcategoryUpdate(is_active=False))
