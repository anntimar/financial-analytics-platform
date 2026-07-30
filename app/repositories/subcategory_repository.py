import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.subcategory import Subcategory
from app.schemas.subcategory import SubcategoryCreate, SubcategoryUpdate


class SubcategoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: SubcategoryCreate) -> Subcategory:
        subcategory = Subcategory(**data.model_dump())
        self.session.add(subcategory)
        self.session.commit()
        self.session.refresh(subcategory)
        return subcategory

    def get(self, subcategory_id: uuid.UUID) -> Subcategory | None:
        return self.session.get(Subcategory, subcategory_id)

    def find_duplicate(self, data: SubcategoryCreate) -> Subcategory | None:
        return self.session.scalar(
            select(Subcategory).where(
                Subcategory.category_id == data.category_id,
                Subcategory.name == data.name,
            )
        )

    def list(
        self, category_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[Subcategory], int]:
        filters = [
            Subcategory.category_id == category_id,
            Subcategory.is_active.is_(True),
        ]
        total = (
            self.session.scalar(select(func.count()).select_from(Subcategory).where(*filters)) or 0
        )
        statement = (
            select(Subcategory)
            .where(*filters)
            .order_by(Subcategory.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement)), total

    def update(self, subcategory: Subcategory, data: SubcategoryUpdate) -> Subcategory:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(subcategory, field, value)
        self.session.commit()
        self.session.refresh(subcategory)
        return subcategory
