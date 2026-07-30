import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_category_service
from app.core.security import CurrentUser, ensure_company_access, require_roles
from app.schemas.auth import UserRole
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate, TransactionType
from app.schemas.common import Page
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])
Service = Annotated[CategoryService, Depends(get_category_service)]
Editor = Annotated[object, Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST))]


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate, service: Service, _editor: Editor, user: CurrentUser
) -> CategoryResponse:
    ensure_company_access(user, data.company_id)
    return CategoryResponse.model_validate(service.create(data))


@router.get("", response_model=Page[CategoryResponse])
def list_categories(
    company_id: uuid.UUID,
    service: Service,
    user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    transaction_type: TransactionType | None = None,
) -> Page[CategoryResponse]:
    ensure_company_access(user, company_id)
    return service.list(company_id, page, page_size, transaction_type)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: uuid.UUID, service: Service, user: CurrentUser) -> CategoryResponse:
    category = service.get(category_id)
    ensure_company_access(user, category.company_id)
    return CategoryResponse.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    service: Service,
    _editor: Editor,
    user: CurrentUser,
) -> CategoryResponse:
    ensure_company_access(user, service.get(category_id).company_id)
    return CategoryResponse.model_validate(service.update(category_id, data))


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_category(
    category_id: uuid.UUID, service: Service, _editor: Editor, user: CurrentUser
) -> Response:
    ensure_company_access(user, service.get(category_id).company_id)
    service.deactivate(category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
