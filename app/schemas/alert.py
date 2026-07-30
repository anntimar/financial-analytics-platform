import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertWorkflowStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class FinancialAlert(BaseModel):
    code: str
    severity: AlertSeverity
    title: str
    message: str
    reference_date: date
    context: dict[str, Any]
    workflow_status: AlertWorkflowStatus = AlertWorkflowStatus.OPEN
    workflow_note: str | None = None
    workflow_updated_at: datetime | None = None


class AlertActionUpdate(BaseModel):
    company_id: uuid.UUID
    alert_code: str
    reference_date: date
    period_start: date
    period_end: date
    status: AlertWorkflowStatus
    note: str | None = None


class AlertActionResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    alert_code: str
    reference_date: date
    status: AlertWorkflowStatus
    note: str | None
    updated_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
