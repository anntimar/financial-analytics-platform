import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.schemas.account import AccountCreate, AccountUpdate


class AccountRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: AccountCreate) -> Account:
        account = Account(**data.model_dump())
        self.session.add(account)
        self.session.commit()
        self.session.refresh(account)
        return account

    def get(self, account_id: uuid.UUID) -> Account | None:
        return self.session.get(Account, account_id)

    def find_by_name(self, company_id: uuid.UUID, name: str) -> Account | None:
        return self.session.scalar(
            select(Account).where(
                Account.company_id == company_id,
                func.lower(Account.name) == name.lower(),
            )
        )

    def list(
        self, company_id: uuid.UUID, page: int, page_size: int, active_only: bool
    ) -> tuple[list[Account], int]:
        filters = [Account.company_id == company_id]
        if active_only:
            filters.append(Account.is_active.is_(True))
        total = self.session.scalar(select(func.count()).select_from(Account).where(*filters)) or 0
        statement = (
            select(Account)
            .where(*filters)
            .order_by(Account.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement)), total

    def update(self, account: Account, data: AccountUpdate) -> Account:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(account, field, value)
        self.session.commit()
        self.session.refresh(account)
        return account
