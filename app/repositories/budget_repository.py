import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.schemas.budget import BudgetCreate, BudgetUpdate
from app.schemas.category import TransactionType


class BudgetRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: BudgetCreate) -> Budget:
        budget = Budget(**data.model_dump())
        self.session.add(budget)
        self.session.commit()
        self.session.refresh(budget)
        return budget

    def get(self, budget_id: uuid.UUID) -> Budget | None:
        return self.session.get(Budget, budget_id)

    def find_duplicate(self, data: BudgetCreate) -> Budget | None:
        return self.session.scalar(
            select(Budget).where(
                Budget.company_id == data.company_id,
                Budget.category_id == data.category_id,
                Budget.transaction_type == data.transaction_type,
                Budget.reference_month == data.reference_month,
            )
        )

    def list(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        start_date: date | None,
        end_date: date | None,
        transaction_type: TransactionType | None,
    ) -> tuple[list[Budget], int]:
        filters = [Budget.company_id == company_id]
        if start_date:
            filters.append(Budget.reference_month >= start_date)
        if end_date:
            filters.append(Budget.reference_month <= end_date)
        if transaction_type:
            filters.append(Budget.transaction_type == transaction_type)
        total = self.session.scalar(select(func.count()).select_from(Budget).where(*filters)) or 0
        statement = (
            select(Budget)
            .where(*filters)
            .order_by(Budget.reference_month.desc(), Budget.transaction_type)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement)), total

    def update(self, budget: Budget, data: BudgetUpdate) -> Budget:
        budget.amount = data.amount
        self.session.commit()
        self.session.refresh(budget)
        return budget

    def delete(self, budget: Budget) -> None:
        self.session.delete(budget)
        self.session.commit()
