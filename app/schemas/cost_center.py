import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CostCenterCreate(BaseModel):
    company_id: uuid.UUID
    name: str = Field(min_length=2, max_length=100)
    code: str | None = Field(default=None, max_length=30)


class CostCenterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    code: str | None = Field(default=None, max_length=30)
    is_active: bool | None = None


class CostCenterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    code: str | None
    is_active: bool
    created_at: datetime
