from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class FinancialAlert(BaseModel):
    code: str
    severity: AlertSeverity
    title: str
    message: str
    reference_date: date
    context: dict[str, Any]
