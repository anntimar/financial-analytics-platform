import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ImportStatus(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class ImportBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    file_name: str
    file_hash: str
    import_type: str
    status: ImportStatus
    total_rows: int
    valid_rows: int
    rejected_rows: int
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None


class DataQualityIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    import_batch_id: uuid.UUID
    row_number: int | None
    field_name: str | None
    issue_type: str
    issue_description: str
    raw_value: str | None
    severity: str
    created_at: datetime
