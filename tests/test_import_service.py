import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.services.import_service import ImportService


def csv_content(category_id: uuid.UUID, *, duplicate: bool = False) -> bytes:
    header = (
        "category_id,description,transaction_type,amount,"
        "competence_date,due_date,payment_date,status\n"
    )
    row = f"{category_id},Venda mensal,revenue,100.00,2026-07-01,2026-07-10,2026-07-10,paid\n"
    return (header + row + (row if duplicate else "")).encode()


def batch_record(company_id: uuid.UUID) -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid.uuid4(),
        company_id=company_id,
        file_name="transactions.csv",
        file_hash="a" * 64,
        import_type="transactions_csv",
        status="processing",
        total_rows=0,
        valid_rows=0,
        rejected_rows=0,
        started_at=now,
        completed_at=None,
        error_message=None,
    )


def build_service(company_id: uuid.UUID, category_id: uuid.UUID) -> tuple[ImportService, Mock]:
    repository = Mock()
    repository.find_completed_file.return_value = None
    repository.transaction_hash_exists.return_value = False
    batch = batch_record(company_id)
    repository.create_batch.return_value = batch
    repository.complete_batch.return_value = batch
    company_repository = Mock()
    company_repository.get.return_value = SimpleNamespace(id=company_id)
    category_repository = Mock()
    category_repository.get.return_value = SimpleNamespace(
        id=category_id,
        company_id=company_id,
        transaction_type="revenue",
    )
    return (
        ImportService(repository, company_repository, category_repository),
        repository,
    )


def test_import_service_imports_valid_transaction() -> None:
    company_id = uuid.uuid4()
    category_id = uuid.uuid4()
    service, repository = build_service(company_id, category_id)

    result = service.import_transactions(company_id, "transactions.csv", csv_content(category_id))

    assert result is repository.create_batch.return_value
    repository.add_raw_row.assert_called_once()
    repository.add_transaction.assert_called_once()
    repository.complete_batch.assert_called_once_with(
        repository.create_batch.return_value, total=1, valid=1, rejected=0
    )


def test_import_service_rejects_duplicate_inside_file() -> None:
    company_id = uuid.uuid4()
    category_id = uuid.uuid4()
    service, repository = build_service(company_id, category_id)

    service.import_transactions(
        company_id, "transactions.csv", csv_content(category_id, duplicate=True)
    )

    assert repository.add_transaction.call_count == 1
    repository.add_issue.assert_called_once()
    repository.complete_batch.assert_called_once_with(
        repository.create_batch.return_value, total=2, valid=1, rejected=1
    )


@pytest.mark.parametrize(
    ("file_name", "content", "message"),
    [
        ("transactions.xlsx", b"data", "CSV"),
        ("transactions.csv", b"", "vazio"),
    ],
)
def test_import_service_validates_file(file_name: str, content: bytes, message: str) -> None:
    company_id = uuid.uuid4()
    company_repository = Mock()
    company_repository.get.return_value = SimpleNamespace(id=company_id)
    service = ImportService(Mock(), company_repository, Mock())

    with pytest.raises(AppError, match=message):
        service.import_transactions(company_id, file_name, content)


def test_import_service_rejects_oversized_file() -> None:
    company_id = uuid.uuid4()
    company_repository = Mock()
    company_repository.get.return_value = SimpleNamespace(id=company_id)
    service = ImportService(Mock(), company_repository, Mock())

    with pytest.raises(AppError, match="5 MB"):
        service.import_transactions(
            company_id,
            "transactions.csv",
            b"x" * (5 * 1024 * 1024 + 1),
        )


def test_import_service_rejects_missing_company() -> None:
    company_repository = Mock()
    company_repository.get.return_value = None
    service = ImportService(Mock(), company_repository, Mock())

    with pytest.raises(NotFoundError):
        service.import_transactions(uuid.uuid4(), "transactions.csv", b"data")


def test_import_service_rejects_reimported_file() -> None:
    company_id = uuid.uuid4()
    category_id = uuid.uuid4()
    service, repository = build_service(company_id, category_id)
    repository.find_completed_file.return_value = batch_record(company_id)

    with pytest.raises(ConflictError):
        service.import_transactions(company_id, "transactions.csv", csv_content(category_id))


def test_import_service_queries_batches_and_issues() -> None:
    company_id = uuid.uuid4()
    batch = batch_record(company_id)
    repository = Mock()
    repository.get_batch.return_value = batch
    repository.list_batches.return_value = ([batch], 1)
    repository.list_issues.return_value = ([], 0)
    service = ImportService(repository, Mock(), Mock())
    assert service.get(batch.id) is batch
    assert service.list(company_id, 1, 20).total == 1
    assert service.list_issues(batch.id, 1, 20).total == 0
    repository.get_batch.return_value = None
    with pytest.raises(NotFoundError):
        service.get(batch.id)


def test_import_service_wraps_unexpected_failure() -> None:
    company_id = uuid.uuid4()
    category_id = uuid.uuid4()
    service, repository = build_service(company_id, category_id)
    repository.add_transaction.side_effect = RuntimeError("database failed")
    with pytest.raises(AppError, match="inesperada"):
        service.import_transactions(company_id, "transactions.csv", csv_content(category_id))
    repository.fail_batch.assert_called_once()
