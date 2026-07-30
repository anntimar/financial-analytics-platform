import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.category import TransactionType


class TransactionStatus(StrEnum):
    PAID = "paid"
    PENDING = "pending"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    PARTIALLY_PAID = "partially_paid"


class TransactionCreate(BaseModel):
    company_id: uuid.UUID
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID
    subcategory_id: uuid.UUID | None = None
    transaction_type: TransactionType
    description: str = Field(min_length=3, max_length=255)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    competence_date: date
    due_date: date | None = None
    payment_date: date | None = None
    status: TransactionStatus
    payment_method: str | None = Field(default=None, max_length=50)
    source: str = Field(default="manual", min_length=2, max_length=50)
    external_id: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_payment_date(self) -> "TransactionCreate":
        if self.status == TransactionStatus.PAID and self.payment_date is None:
            raise ValueError("payment_date é obrigatória para transações pagas")
        return self


class TransactionUpdate(BaseModel):
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    subcategory_id: uuid.UUID | None = None
    description: str | None = Field(default=None, min_length=3, max_length=255)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    competence_date: date | None = None
    due_date: date | None = None
    payment_date: date | None = None
    status: TransactionStatus | None = None
    payment_method: str | None = Field(default=None, max_length=50)


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    account_id: uuid.UUID | None
    category_id: uuid.UUID
    subcategory_id: uuid.UUID | None = None
    transaction_type: TransactionType
    description: str
    amount: Decimal
    competence_date: date
    due_date: date | None
    payment_date: date | None
    status: TransactionStatus
    payment_method: str | None
    source: str
    external_id: str | None
    created_at: datetime
    updated_at: datetime
