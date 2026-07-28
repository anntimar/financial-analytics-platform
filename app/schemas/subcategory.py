import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SubcategoryCreate(BaseModel):
    category_id: uuid.UUID
    name: str = Field(min_length=2, max_length=100)


class SubcategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    is_active: bool | None = None


class SubcategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID
    name: str
    is_active: bool
    created_at: datetime
