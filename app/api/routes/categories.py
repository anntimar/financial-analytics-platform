import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_category_service
from app.core.security import require_roles
from app.schemas.auth import UserRole
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate, TransactionType
from app.schemas.common import Page
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])
Service = Annotated[CategoryService, Depends(get_category_service)]
Editor = Annotated[object, Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST))]


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, service: Service, _editor: Editor) -> CategoryResponse:
    return CategoryResponse.model_validate(service.create(data))


@router.get("", response_model=Page[CategoryResponse])
def list_categories(
    company_id: uuid.UUID,
    service: Service,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    transaction_type: TransactionType | None = None,
) -> Page[CategoryResponse]:
    return service.list(company_id, page, page_size, transaction_type)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: uuid.UUID, service: Service) -> CategoryResponse:
    return CategoryResponse.model_validate(service.get(category_id))


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: uuid.UUID, data: CategoryUpdate, service: Service, _editor: Editor
) -> CategoryResponse:
    return CategoryResponse.model_validate(service.update(category_id, data))


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_category(category_id: uuid.UUID, service: Service, _editor: Editor) -> Response:
    service.deactivate(category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
