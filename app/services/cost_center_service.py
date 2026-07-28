import uuid

from app.core.exceptions import ConflictError, NotFoundError
from app.models.cost_center import CostCenter
from app.repositories.company_repository import CompanyRepository
from app.repositories.cost_center_repository import CostCenterRepository
from app.schemas.common import Page
from app.schemas.cost_center import CostCenterCreate, CostCenterResponse, CostCenterUpdate


class CostCenterService:
    def __init__(self, repository: CostCenterRepository, companies: CompanyRepository) -> None:
        self.repository = repository
        self.companies = companies

    def create(self, data: CostCenterCreate) -> CostCenter:
        if self.companies.get(data.company_id) is None:
            raise NotFoundError("Empresa")
        if self.repository.find_duplicate(data):
            raise ConflictError("Este centro de custo já existe para a empresa.")
        return self.repository.create(data)

    def get(self, item_id: uuid.UUID) -> CostCenter:
        item = self.repository.get(item_id)
        if item is None:
            raise NotFoundError("Centro de custo")
        return item

    def list(self, company_id: uuid.UUID, page: int, page_size: int) -> Page[CostCenterResponse]:
        if self.companies.get(company_id) is None:
            raise NotFoundError("Empresa")
        items, total = self.repository.list(company_id, page, page_size)
        return Page[CostCenterResponse](items=items, total=total, page=page, page_size=page_size)

    def update(self, item_id: uuid.UUID, data: CostCenterUpdate) -> CostCenter:
        return self.repository.update(self.get(item_id), data)

    def deactivate(self, item_id: uuid.UUID) -> CostCenter:
        return self.repository.update(self.get(item_id), CostCenterUpdate(is_active=False))
