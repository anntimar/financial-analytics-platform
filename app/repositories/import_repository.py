import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.data_quality_issue import DataQualityIssue
from app.models.import_batch import ImportBatch
from app.models.raw_imported_transaction import RawImportedTransaction
from app.models.transaction import Transaction
from app.pipelines.validation import PreparedTransaction, ValidationIssueData


class ImportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_batch(self, company_id: uuid.UUID, file_name: str, file_hash: str) -> ImportBatch:
        batch = ImportBatch(
            company_id=company_id,
            file_name=file_name,
            file_hash=file_hash,
            import_type="transactions_csv",
            status="processing",
        )
        self.session.add(batch)
        self.session.commit()
        self.session.refresh(batch)
        return batch

    def get_batch(self, batch_id: uuid.UUID) -> ImportBatch | None:
        return self.session.get(ImportBatch, batch_id)

    def find_completed_file(self, company_id: uuid.UUID, file_hash: str) -> ImportBatch | None:
        return self.session.scalar(
            select(ImportBatch).where(
                ImportBatch.company_id == company_id,
                ImportBatch.file_hash == file_hash,
                ImportBatch.status.in_(("completed", "completed_with_errors")),
            )
        )

    def list_batches(
        self, company_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[ImportBatch], int]:
        filters = [ImportBatch.company_id == company_id]
        total = (
            self.session.scalar(select(func.count()).select_from(ImportBatch).where(*filters)) or 0
        )
        statement = (
            select(ImportBatch)
            .where(*filters)
            .order_by(ImportBatch.started_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement)), total

    def list_issues(
        self, batch_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[DataQualityIssue], int]:
        filters = [DataQualityIssue.import_batch_id == batch_id]
        total = (
            self.session.scalar(select(func.count()).select_from(DataQualityIssue).where(*filters))
            or 0
        )
        statement = (
            select(DataQualityIssue)
            .where(*filters)
            .order_by(DataQualityIssue.row_number, DataQualityIssue.created_at)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement)), total

    def add_raw_row(self, batch_id: uuid.UUID, row_number: int, payload: dict[str, Any]) -> None:
        self.session.add(
            RawImportedTransaction(
                import_batch_id=batch_id,
                row_number=row_number,
                payload=payload,
            )
        )

    def add_issue(
        self,
        batch_id: uuid.UUID,
        row_number: int,
        issue: ValidationIssueData,
    ) -> None:
        self.session.add(
            DataQualityIssue(
                import_batch_id=batch_id,
                row_number=row_number,
                field_name=issue.field,
                issue_type=issue.code,
                issue_description=issue.message,
                raw_value=issue.raw_value,
                severity=issue.severity,
            )
        )

    def transaction_hash_exists(self, transaction_hash: str) -> bool:
        return (
            self.session.scalar(
                select(Transaction.id).where(Transaction.transaction_hash == transaction_hash)
            )
            is not None
        )

    def add_transaction(
        self,
        company_id: uuid.UUID,
        batch_id: uuid.UUID,
        prepared: PreparedTransaction,
    ) -> None:
        self.session.add(
            Transaction(
                company_id=company_id,
                import_batch_id=batch_id,
                **prepared.__dict__,
            )
        )

    def complete_batch(
        self, batch: ImportBatch, total: int, valid: int, rejected: int
    ) -> ImportBatch:
        batch.total_rows = total
        batch.valid_rows = valid
        batch.rejected_rows = rejected
        batch.status = "completed_with_errors" if rejected else "completed"
        batch.completed_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(batch)
        return batch

    def fail_batch(self, batch: ImportBatch, message: str) -> ImportBatch:
        self.session.rollback()
        batch.status = "failed"
        batch.error_message = message
        batch.completed_at = datetime.now(UTC)
        self.session.add(batch)
        self.session.commit()
        self.session.refresh(batch)
        return batch
