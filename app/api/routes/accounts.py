import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_account_service
from app.core.security import CurrentUser, ensure_company_access, require_roles
from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate
from app.schemas.auth import UserRole
from app.schemas.common import Page
from app.services.account_service import AccountService

router = APIRouter(prefix="/accounts", tags=["accounts"])
Service = Annotated[AccountService, Depends(get_account_service)]
Editor = Annotated[object, Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST))]


@router.post("", response_model=AccountResponse, status_code=201)
def create_account(
    data: AccountCreate, service: Service, _editor: Editor, user: CurrentUser
) -> AccountResponse:
    ensure_company_access(user, data.company_id)
    return AccountResponse.model_validate(service.create(data))


@router.get("", response_model=Page[AccountResponse])
def list_accounts(
    company_id: uuid.UUID,
    service: Service,
    user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    active_only: bool = True,
) -> Page[AccountResponse]:
    ensure_company_access(user, company_id)
    return service.list(company_id, page, page_size, active_only)


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: uuid.UUID, service: Service, user: CurrentUser) -> AccountResponse:
    account = service.get(account_id)
    ensure_company_access(user, account.company_id)
    return AccountResponse.model_validate(account)


@router.patch("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: uuid.UUID,
    data: AccountUpdate,
    service: Service,
    _editor: Editor,
    user: CurrentUser,
) -> AccountResponse:
    ensure_company_access(user, service.get(account_id).company_id)
    return AccountResponse.model_validate(service.update(account_id, data))


@router.delete("/{account_id}", response_model=AccountResponse)
def deactivate_account(
    account_id: uuid.UUID, service: Service, _editor: Editor, user: CurrentUser
) -> AccountResponse:
    ensure_company_access(user, service.get(account_id).company_id)
    return AccountResponse.model_validate(service.deactivate(account_id))
