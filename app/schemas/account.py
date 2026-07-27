import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AccountType(StrEnum):
    CHECKING = "checking"
    CASH = "cash"
    DIGITAL_WALLET = "digital_wallet"
    CREDIT_CARD = "credit_card"
    INVESTMENT = "investment"


class AccountCreate(BaseModel):
    company_id: uuid.UUID
    name: str = Field(min_length=2, max_length=100)
    account_type: AccountType
    institution: str | None = Field(default=None, max_length=100)
    opening_balance: Decimal = Field(default=Decimal(0), max_digits=14, decimal_places=2)


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    institution: str | None = Field(default=None, max_length=100)
    opening_balance: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    is_active: bool | None = None


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    account_type: AccountType
    institution: str | None
    opening_balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AccountBalance(BaseModel):
    account_id: uuid.UUID
    account_name: str
    account_type: AccountType
    opening_balance: Decimal
    inflows: Decimal
    outflows: Decimal
    current_balance: Decimal
