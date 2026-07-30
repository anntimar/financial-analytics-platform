import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cost_center import CostCenter
from app.schemas.cost_center import CostCenterCreate, CostCenterUpdate


class CostCenterRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: CostCenterCreate) -> CostCenter:
        item = CostCenter(**data.model_dump())
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def get(self, item_id: uuid.UUID) -> CostCenter | None:
        return self.session.get(CostCenter, item_id)

    def find_duplicate(self, data: CostCenterCreate) -> CostCenter | None:
        return self.session.scalar(
            select(CostCenter).where(
                CostCenter.company_id == data.company_id,
                CostCenter.name == data.name,
            )
        )

    def list(
        self, company_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[CostCenter], int]:
        filters = [CostCenter.company_id == company_id, CostCenter.is_active.is_(True)]
        total = (
            self.session.scalar(select(func.count()).select_from(CostCenter).where(*filters)) or 0
        )
        statement = (
            select(CostCenter)
            .where(*filters)
            .order_by(CostCenter.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement)), total

    def update(self, item: CostCenter, data: CostCenterUpdate) -> CostCenter:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        self.session.commit()
        self.session.refresh(item)
        return item
