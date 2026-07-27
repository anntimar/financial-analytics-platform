import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.schemas.category import TransactionType
from app.schemas.transaction import TransactionCreate, TransactionStatus, TransactionUpdate


class TransactionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: TransactionCreate) -> Transaction:
        transaction = Transaction(**data.model_dump())
        self.session.add(transaction)
        self.session.commit()
        self.session.refresh(transaction)
        return transaction

    def get(self, transaction_id: uuid.UUID) -> Transaction | None:
        return self.session.get(Transaction, transaction_id)

    def list(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        start_date: date | None = None,
        end_date: date | None = None,
        transaction_type: TransactionType | None = None,
        category_id: uuid.UUID | None = None,
        account_id: uuid.UUID | None = None,
        status: TransactionStatus | None = None,
        minimum_amount: Decimal | None = None,
        maximum_amount: Decimal | None = None,
    ) -> tuple[list[Transaction], int]:
        filters = [Transaction.company_id == company_id]
        if start_date:
            filters.append(Transaction.competence_date >= start_date)
        if end_date:
            filters.append(Transaction.competence_date <= end_date)
        if transaction_type:
            filters.append(Transaction.transaction_type == transaction_type)
        if category_id:
            filters.append(Transaction.category_id == category_id)
        if account_id:
            filters.append(Transaction.account_id == account_id)
        if status:
            filters.append(Transaction.status == status)
        if minimum_amount is not None:
            filters.append(Transaction.amount >= minimum_amount)
        if maximum_amount is not None:
            filters.append(Transaction.amount <= maximum_amount)

        total = (
            self.session.scalar(select(func.count()).select_from(Transaction).where(*filters)) or 0
        )
        statement = (
            select(Transaction)
            .where(*filters)
            .order_by(Transaction.competence_date.desc(), Transaction.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement)), total

    def update(self, transaction: Transaction, data: TransactionUpdate) -> Transaction:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(transaction, field, value)
        self.session.commit()
        self.session.refresh(transaction)
        return transaction

    def delete(self, transaction: Transaction) -> None:
        self.session.delete(transaction)
        self.session.commit()
