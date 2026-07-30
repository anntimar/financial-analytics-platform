import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_budget_service
from app.core.security import CurrentUser, ensure_company_access, require_roles
from app.schemas.auth import UserRole
from app.schemas.budget import BudgetCreate, BudgetResponse, BudgetUpdate
from app.schemas.category import TransactionType
from app.schemas.common import Page
from app.services.budget_service import BudgetService

router = APIRouter(prefix="/budgets", tags=["budgets"])
Service = Annotated[BudgetService, Depends(get_budget_service)]
Editor = Annotated[object, Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST))]


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    data: BudgetCreate, service: Service, _editor: Editor, user: CurrentUser
) -> BudgetResponse:
    ensure_company_access(user, data.company_id)
    return BudgetResponse.model_validate(service.create(data))


@router.get("", response_model=Page[BudgetResponse])
def list_budgets(
    company_id: uuid.UUID,
    service: Service,
    user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    start_date: date | None = None,
    end_date: date | None = None,
    transaction_type: TransactionType | None = None,
) -> Page[BudgetResponse]:
    ensure_company_access(user, company_id)
    return service.list(company_id, page, page_size, start_date, end_date, transaction_type)


@router.patch("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: uuid.UUID,
    data: BudgetUpdate,
    service: Service,
    _editor: Editor,
    user: CurrentUser,
) -> BudgetResponse:
    ensure_company_access(user, service.get(budget_id).company_id)
    return BudgetResponse.model_validate(service.update(budget_id, data))


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: uuid.UUID, service: Service, _editor: Editor, user: CurrentUser
) -> Response:
    ensure_company_access(user, service.get(budget_id).company_id)
    service.delete(budget_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
