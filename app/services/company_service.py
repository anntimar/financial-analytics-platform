import uuid

from app.core.exceptions import ConflictError, NotFoundError
from app.models.company import Company
from app.repositories.company_repository import CompanyRepository
from app.schemas.common import Page
from app.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate


class CompanyService:
    def __init__(self, repository: CompanyRepository) -> None:
        self.repository = repository

    def create(self, data: CompanyCreate) -> Company:
        if data.document_number and self.repository.get_by_document(data.document_number):
            raise ConflictError("Já existe uma empresa com este documento.")
        return self.repository.create(data)

    def get(self, company_id: uuid.UUID) -> Company:
        company = self.repository.get(company_id)
        if company is None:
            raise NotFoundError("Empresa")
        return company

    def list(self, page: int, page_size: int, active_only: bool) -> Page[CompanyResponse]:
        companies, total = self.repository.list(page, page_size, active_only)
        return Page[CompanyResponse](items=companies, total=total, page=page, page_size=page_size)

    def update(self, company_id: uuid.UUID, data: CompanyUpdate) -> Company:
        company = self.get(company_id)
        if data.document_number:
            existing = self.repository.get_by_document(data.document_number)
            if existing and existing.id != company_id:
                raise ConflictError("Já existe uma empresa com este documento.")
        return self.repository.update(company, data)

    def deactivate(self, company_id: uuid.UUID) -> Company:
        return self.repository.update(self.get(company_id), CompanyUpdate(is_active=False))
