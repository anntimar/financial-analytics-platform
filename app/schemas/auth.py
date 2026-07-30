import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    MANAGER = "manager"


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: UserRole
    company_id: uuid.UUID | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    role: UserRole | None = None
    company_id: uuid.UUID | None = None
    is_active: bool | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID | None
    name: str
    email: str
    role: UserRole
    is_active: bool


class UserAuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    target_user_id: uuid.UUID
    action: str
    changes: dict[str, Any]
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
