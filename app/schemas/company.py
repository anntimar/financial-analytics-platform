import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CompanyBase(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    trade_name: str | None = Field(default=None, max_length=150)
    document_number: str | None = Field(default=None, min_length=11, max_length=20)
    industry: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=2)

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str | None) -> str | None:
        return value.upper() if value else None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    trade_name: str | None = Field(default=None, max_length=150)
    document_number: str | None = Field(default=None, min_length=11, max_length=20)
    industry: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    is_active: bool | None = None

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str | None) -> str | None:
        return value.upper() if value else None


class CompanyResponse(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
