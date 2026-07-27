import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate


class CompanyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: CompanyCreate) -> Company:
        company = Company(**data.model_dump())
        self.session.add(company)
        self.session.commit()
        self.session.refresh(company)
        return company

    def get(self, company_id: uuid.UUID) -> Company | None:
        return self.session.get(Company, company_id)

    def get_by_document(self, document_number: str) -> Company | None:
        return self.session.scalar(
            select(Company).where(Company.document_number == document_number)
        )

    def list(self, page: int, page_size: int, active_only: bool) -> tuple[list[Company], int]:
        filters = [Company.is_active.is_(True)] if active_only else []
        total = self.session.scalar(select(func.count()).select_from(Company).where(*filters)) or 0
        statement = (
            select(Company)
            .where(*filters)
            .order_by(Company.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement)), total

    def update(self, company: Company, data: CompanyUpdate) -> Company:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(company, field, value)
        self.session.commit()
        self.session.refresh(company)
        return company
