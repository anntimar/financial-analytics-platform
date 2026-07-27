import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate, TransactionType


class CategoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: CategoryCreate) -> Category:
        category = Category(**data.model_dump())
        self.session.add(category)
        self.session.commit()
        self.session.refresh(category)
        return category

    def get(self, category_id: uuid.UUID) -> Category | None:
        return self.session.get(Category, category_id)

    def find_duplicate(self, data: CategoryCreate) -> Category | None:
        return self.session.scalar(
            select(Category).where(
                Category.company_id == data.company_id,
                Category.name == data.name,
                Category.transaction_type == data.transaction_type,
            )
        )

    def list(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        transaction_type: TransactionType | None,
    ) -> tuple[list[Category], int]:
        filters = [Category.company_id == company_id, Category.is_active.is_(True)]
        if transaction_type:
            filters.append(Category.transaction_type == transaction_type)
        total = self.session.scalar(select(func.count()).select_from(Category).where(*filters)) or 0
        statement = (
            select(Category)
            .where(*filters)
            .order_by(Category.transaction_type, Category.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement)), total

    def update(self, category: Category, data: CategoryUpdate) -> Category:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(category, field, value)
        self.session.commit()
        self.session.refresh(category)
        return category
