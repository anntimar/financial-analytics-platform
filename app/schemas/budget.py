import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.category import TransactionType


class BudgetCreate(BaseModel):
    company_id: uuid.UUID
    category_id: uuid.UUID
    transaction_type: TransactionType
    reference_month: date
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)

    @field_validator("reference_month")
    @classmethod
    def month_must_start_on_first_day(cls, value: date) -> date:
        if value.day != 1:
            raise ValueError("reference_month deve ser o primeiro dia do mês.")
        return value


class BudgetUpdate(BaseModel):
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    category_id: uuid.UUID
    transaction_type: TransactionType
    reference_month: date
    amount: Decimal
    created_at: datetime
    updated_at: datetime


class BudgetComparison(BaseModel):
    reference_month: date
    category_id: uuid.UUID
    category_name: str
    transaction_type: TransactionType
    planned_amount: Decimal
    realized_amount: Decimal
    variance_amount: Decimal
    variance_percentage: Decimal | None
