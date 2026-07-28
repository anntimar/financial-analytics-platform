import hashlib
import logging
import time
import uuid

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.metrics import IMPORT_DURATION, IMPORT_ROWS
from app.models.import_batch import ImportBatch
from app.pipelines.readers.csv_reader import read_csv_rows
from app.pipelines.validation import ValidationIssueData, prepare_transaction
from app.repositories.category_repository import CategoryRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.import_repository import ImportRepository
from app.schemas.common import Page
from app.schemas.import_batch import (
    DataQualityIssueResponse,
    ImportBatchResponse,
)

MAX_UPLOAD_SIZE = 5 * 1024 * 1024
logger = logging.getLogger("finanalytics.imports")


class ImportService:
    def __init__(
        self,
        repository: ImportRepository,
        company_repository: CompanyRepository,
        category_repository: CategoryRepository,
    ) -> None:
        self.repository = repository
        self.company_repository = company_repository
        self.category_repository = category_repository

    def import_transactions(
        self, company_id: uuid.UUID, file_name: str, content: bytes
    ) -> ImportBatch:
        if self.company_repository.get(company_id) is None:
            raise NotFoundError("Empresa")
        if not file_name.lower().endswith(".csv"):
            raise AppError("Apenas arquivos CSV são aceitos.")
        if not content:
            raise AppError("O arquivo está vazio.")
        if len(content) > MAX_UPLOAD_SIZE:
            raise AppError("O arquivo excede o limite de 5 MB.")

        file_hash = hashlib.sha256(content).hexdigest()
        if self.repository.find_completed_file(company_id, file_hash):
            raise ConflictError("Este arquivo já foi importado para a empresa.")

        rows = read_csv_rows(content)
        if not rows:
            raise AppError("O arquivo não possui registros.")
        batch = self.repository.create_batch(company_id, file_name, file_hash)
        started_at = time.perf_counter()
        logger.info(
            "transaction_import_started",
            extra={
                "batch_id": str(batch.id),
                "company_id": str(company_id),
                "file_name": file_name,
                "total_rows": len(rows),
            },
        )

        valid = 0
        rejected = 0
        hashes_in_file: set[str] = set()
        try:
            for row_number, row in enumerate(rows, start=2):
                self.repository.add_raw_row(batch.id, row_number, row)
                prepared, issues = prepare_transaction(row, company_id)
                if prepared is not None:
                    category = self.category_repository.get(prepared.category_id)
                    if category is None:
                        issues.append(
                            ValidationIssueData(
                                "category_id",
                                "category_not_found",
                                "Categoria não encontrada.",
                                str(prepared.category_id),
                            )
                        )
                    elif category.company_id != company_id:
                        issues.append(
                            ValidationIssueData(
                                "category_id",
                                "category_company_mismatch",
                                "Categoria não pertence à empresa.",
                                str(prepared.category_id),
                            )
                        )
                    elif category.transaction_type != prepared.transaction_type:
                        issues.append(
                            ValidationIssueData(
                                "transaction_type",
                                "category_type_mismatch",
                                "Tipo da categoria difere do tipo da transação.",
                                prepared.transaction_type,
                            )
                        )

                if prepared is not None and (
                    prepared.transaction_hash in hashes_in_file
                    or self.repository.transaction_hash_exists(prepared.transaction_hash)
                ):
                    issues.append(
                        ValidationIssueData(
                            "transaction_hash",
                            "duplicate_transaction",
                            "Transação duplicada.",
                            prepared.transaction_hash,
                        )
                    )

                if issues or prepared is None:
                    rejected += 1
                    for issue in issues:
                        self.repository.add_issue(batch.id, row_number, issue)
                    continue

                self.repository.add_transaction(company_id, batch.id, prepared)
                hashes_in_file.add(prepared.transaction_hash)
                valid += 1

            completed_batch = self.repository.complete_batch(
                batch, total=len(rows), valid=valid, rejected=rejected
            )
            IMPORT_ROWS.labels("valid").inc(valid)
            IMPORT_ROWS.labels("rejected").inc(rejected)
            IMPORT_DURATION.observe(time.perf_counter() - started_at)
            logger.info(
                "transaction_import_completed",
                extra={
                    "batch_id": str(batch.id),
                    "company_id": str(company_id),
                    "total_rows": len(rows),
                    "valid_rows": valid,
                    "rejected_rows": rejected,
                    "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                },
            )
            return completed_batch
        except Exception as exc:
            self.repository.fail_batch(batch, str(exc))
            logger.exception(
                "transaction_import_failed",
                extra={
                    "batch_id": str(batch.id),
                    "company_id": str(company_id),
                    "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                },
            )
            raise AppError("Falha inesperada durante a importação.") from exc

    def get(self, batch_id: uuid.UUID) -> ImportBatch:
        batch = self.repository.get_batch(batch_id)
        if batch is None:
            raise NotFoundError("Lote de importação")
        return batch

    def list(self, company_id: uuid.UUID, page: int, page_size: int) -> Page[ImportBatchResponse]:
        batches, total = self.repository.list_batches(company_id, page, page_size)
        return Page[ImportBatchResponse](items=batches, total=total, page=page, page_size=page_size)

    def list_issues(
        self, batch_id: uuid.UUID, page: int, page_size: int
    ) -> Page[DataQualityIssueResponse]:
        self.get(batch_id)
        issues, total = self.repository.list_issues(batch_id, page, page_size)
        return Page[DataQualityIssueResponse](
            items=issues, total=total, page=page, page_size=page_size
        )
