import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_transaction_service
from app.core.security import require_roles
from app.schemas.auth import UserRole
from app.schemas.category import TransactionType
from app.schemas.common import Page
from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionStatus,
    TransactionUpdate,
)
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])
Service = Annotated[TransactionService, Depends(get_transaction_service)]
Editor = Annotated[object, Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST))]


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    data: TransactionCreate, service: Service, _editor: Editor
) -> TransactionResponse:
    return TransactionResponse.model_validate(service.create(data))


@router.get("", response_model=Page[TransactionResponse])
def list_transactions(
    company_id: uuid.UUID,
    service: Service,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    start_date: date | None = None,
    end_date: date | None = None,
    transaction_type: TransactionType | None = None,
    category_id: uuid.UUID | None = None,
    status_filter: Annotated[TransactionStatus | None, Query(alias="status")] = None,
    minimum_amount: Annotated[Decimal | None, Query(ge=0)] = None,
    maximum_amount: Annotated[Decimal | None, Query(ge=0)] = None,
) -> Page[TransactionResponse]:
    return service.list(
        company_id,
        page,
        page_size,
        start_date,
        end_date,
        transaction_type,
        category_id,
        status_filter,
        minimum_amount,
        maximum_amount,
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: uuid.UUID, service: Service) -> TransactionResponse:
    return TransactionResponse.model_validate(service.get(transaction_id))


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: uuid.UUID, data: TransactionUpdate, service: Service, _editor: Editor
) -> TransactionResponse:
    return TransactionResponse.model_validate(service.update(transaction_id, data))


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: uuid.UUID, service: Service, _editor: Editor) -> Response:
    service.delete(transaction_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
