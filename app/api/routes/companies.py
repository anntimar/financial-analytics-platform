import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_company_service
from app.core.security import require_roles
from app.schemas.auth import UserRole
from app.schemas.common import Page
from app.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])
Service = Annotated[CompanyService, Depends(get_company_service)]
Admin = Annotated[object, Depends(require_roles(UserRole.ADMIN))]


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(data: CompanyCreate, service: Service, _admin: Admin) -> CompanyResponse:
    return CompanyResponse.model_validate(service.create(data))


@router.get("", response_model=Page[CompanyResponse])
def list_companies(
    service: Service,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    active_only: bool = True,
) -> Page[CompanyResponse]:
    return service.list(page, page_size, active_only)


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(company_id: uuid.UUID, service: Service) -> CompanyResponse:
    return CompanyResponse.model_validate(service.get(company_id))


@router.patch("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: uuid.UUID, data: CompanyUpdate, service: Service, _admin: Admin
) -> CompanyResponse:
    return CompanyResponse.model_validate(service.update(company_id, data))


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_company(company_id: uuid.UUID, service: Service, _admin: Admin) -> Response:
    service.deactivate(company_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
