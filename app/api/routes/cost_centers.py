import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_cost_center_service
from app.core.security import CurrentUser, ensure_company_access, require_roles
from app.schemas.auth import UserRole
from app.schemas.common import Page
from app.schemas.cost_center import CostCenterCreate, CostCenterResponse, CostCenterUpdate
from app.services.cost_center_service import CostCenterService

router = APIRouter(prefix="/cost-centers", tags=["cost-centers"])
Service = Annotated[CostCenterService, Depends(get_cost_center_service)]
Editor = Annotated[object, Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST))]


@router.post("", response_model=CostCenterResponse, status_code=status.HTTP_201_CREATED)
def create_cost_center(
    data: CostCenterCreate, service: Service, _editor: Editor, user: CurrentUser
) -> CostCenterResponse:
    ensure_company_access(user, data.company_id)
    return CostCenterResponse.model_validate(service.create(data))


@router.get("", response_model=Page[CostCenterResponse])
def list_cost_centers(
    company_id: uuid.UUID,
    service: Service,
    user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[CostCenterResponse]:
    ensure_company_access(user, company_id)
    return service.list(company_id, page, page_size)


@router.get("/{item_id}", response_model=CostCenterResponse)
def get_cost_center(item_id: uuid.UUID, service: Service, user: CurrentUser) -> CostCenterResponse:
    item = service.get(item_id)
    ensure_company_access(user, item.company_id)
    return CostCenterResponse.model_validate(item)


@router.patch("/{item_id}", response_model=CostCenterResponse)
def update_cost_center(
    item_id: uuid.UUID,
    data: CostCenterUpdate,
    service: Service,
    _editor: Editor,
    user: CurrentUser,
) -> CostCenterResponse:
    ensure_company_access(user, service.get(item_id).company_id)
    return CostCenterResponse.model_validate(service.update(item_id, data))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_cost_center(
    item_id: uuid.UUID, service: Service, _editor: Editor, user: CurrentUser
) -> Response:
    ensure_company_access(user, service.get(item_id).company_id)
    service.deactivate(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
