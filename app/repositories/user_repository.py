import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import UserUpdate


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def count(self) -> int:
        return self.session.scalar(select(func.count(User.id))) or 0

    def get(self, user_id: uuid.UUID) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email.lower()))

    def create(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def list(
        self,
        page: int,
        page_size: int,
        company_id: uuid.UUID | None,
        active_only: bool,
    ) -> tuple[list[User], int]:
        filters = []
        if company_id is not None:
            filters.append(User.company_id == company_id)
        if active_only:
            filters.append(User.is_active.is_(True))
        total = self.session.scalar(select(func.count()).select_from(User).where(*filters)) or 0
        statement = (
            select(User)
            .where(*filters)
            .order_by(User.name, User.email)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement)), total

    def update(self, user: User, data: UserUpdate) -> User:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value.value if hasattr(value, "value") else value)
        self.session.commit()
        self.session.refresh(user)
        return user
