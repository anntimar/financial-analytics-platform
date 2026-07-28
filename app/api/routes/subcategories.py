import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_subcategory_service
from app.core.exceptions import NotFoundError
from app.core.security import CurrentUser, ensure_company_access, require_roles
from app.schemas.auth import UserRole
from app.schemas.common import Page
from app.schemas.subcategory import (
    SubcategoryCreate,
    SubcategoryResponse,
    SubcategoryUpdate,
)
from app.services.subcategory_service import SubcategoryService

router = APIRouter(prefix="/subcategories", tags=["subcategories"])
Service = Annotated[SubcategoryService, Depends(get_subcategory_service)]
Editor = Annotated[object, Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST))]


def ensure_subcategory_access(
    service: SubcategoryService, user: CurrentUser, subcategory_id: uuid.UUID
) -> None:
    subcategory = service.get(subcategory_id)
    category = service.categories.get(subcategory.category_id)
    if category is None:
        raise NotFoundError("Categoria")
    ensure_company_access(user, category.company_id)


@router.post("", response_model=SubcategoryResponse, status_code=status.HTTP_201_CREATED)
def create_subcategory(
    data: SubcategoryCreate,
    service: Service,
    _editor: Editor,
    user: CurrentUser,
) -> SubcategoryResponse:
    category = service.categories.get(data.category_id)
    if category is not None:
        ensure_company_access(user, category.company_id)
    return SubcategoryResponse.model_validate(service.create(data))


@router.get("", response_model=Page[SubcategoryResponse])
def list_subcategories(
    category_id: uuid.UUID,
    service: Service,
    user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[SubcategoryResponse]:
    category = service.categories.get(category_id)
    if category is not None:
        ensure_company_access(user, category.company_id)
    return service.list(category_id, page, page_size)


@router.get("/{subcategory_id}", response_model=SubcategoryResponse)
def get_subcategory(
    subcategory_id: uuid.UUID, service: Service, user: CurrentUser
) -> SubcategoryResponse:
    ensure_subcategory_access(service, user, subcategory_id)
    return SubcategoryResponse.model_validate(service.get(subcategory_id))


@router.patch("/{subcategory_id}", response_model=SubcategoryResponse)
def update_subcategory(
    subcategory_id: uuid.UUID,
    data: SubcategoryUpdate,
    service: Service,
    _editor: Editor,
    user: CurrentUser,
) -> SubcategoryResponse:
    ensure_subcategory_access(service, user, subcategory_id)
    return SubcategoryResponse.model_validate(service.update(subcategory_id, data))


@router.delete("/{subcategory_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_subcategory(
    subcategory_id: uuid.UUID,
    service: Service,
    _editor: Editor,
    user: CurrentUser,
) -> Response:
    ensure_subcategory_access(service, user, subcategory_id)
    service.deactivate(subcategory_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
