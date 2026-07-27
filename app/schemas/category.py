import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TransactionType(StrEnum):
    REVENUE = "revenue"
    EXPENSE = "expense"


class CategoryCreate(BaseModel):
    company_id: uuid.UUID
    name: str = Field(min_length=2, max_length=100)
    transaction_type: TransactionType


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    is_active: bool | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    transaction_type: TransactionType
    is_active: bool
    created_at: datetime
