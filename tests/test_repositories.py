import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models.category import Category
from app.models.company import Company
from app.models.import_batch import ImportBatch
from app.models.transaction import Transaction
from app.models.user import User
from app.pipelines.validation import PreparedTransaction, ValidationIssueData
from app.repositories.category_repository import CategoryRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.import_repository import ImportRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserRole, UserUpdate
from app.schemas.category import CategoryCreate, CategoryUpdate, TransactionType
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.schemas.transaction import TransactionCreate, TransactionStatus, TransactionUpdate


def test_company_repository_crud_and_list() -> None:
    session = MagicMock()
    company_id = uuid.uuid4()
    existing = Company(id=company_id, name="Empresa")
    session.get.return_value = existing
    session.scalar.side_effect = [existing, 1, 2]
    session.scalars.return_value = [existing]
    repository = CompanyRepository(session)

    created = repository.create(CompanyCreate(name="Nova Empresa"))
    assert created.name == "Nova Empresa"
    assert repository.get(company_id) is existing
    assert repository.get_by_document("12345678000199") is existing
    assert repository.list(1, 20, True) == ([existing], 1)
    assert repository.list(2, 10, False) == ([existing], 2)
    updated = repository.update(existing, CompanyUpdate(name="Atualizada", state="ce"))
    assert updated.name == "Atualizada"
    assert updated.state == "CE"
    assert session.commit.call_count == 2


def test_category_repository_crud_and_filtered_list() -> None:
    session = MagicMock()
    company_id = uuid.uuid4()
    category = Category(
        id=uuid.uuid4(),
        company_id=company_id,
        name="Marketing",
        transaction_type="expense",
    )
    session.get.return_value = category
    session.scalar.side_effect = [category, 1, 1]
    session.scalars.return_value = [category]
    repository = CategoryRepository(session)
    data = CategoryCreate(
        company_id=company_id,
        name="Marketing",
        transaction_type=TransactionType.EXPENSE,
    )

    assert repository.create(data).name == "Marketing"
    assert repository.get(category.id) is category
    assert repository.find_duplicate(data) is category
    assert repository.list(company_id, 1, 20, TransactionType.EXPENSE)[1] == 1
    assert repository.list(company_id, 1, 20, None)[1] == 1
    repository.update(category, CategoryUpdate(name="Mídia"))
    assert category.name == "Mídia"


def test_transaction_repository_crud_filters_and_delete() -> None:
    session = MagicMock()
    company_id = uuid.uuid4()
    category_id = uuid.uuid4()
    transaction = Transaction(
        id=uuid.uuid4(),
        company_id=company_id,
        category_id=category_id,
        transaction_type="revenue",
        description="Venda",
        amount=Decimal("100"),
        competence_date=date(2026, 1, 1),
        status="paid",
        source="manual",
    )
    session.get.return_value = transaction
    session.scalar.return_value = 1
    session.scalars.return_value = [transaction]
    repository = TransactionRepository(session)
    data = TransactionCreate(
        company_id=company_id,
        category_id=category_id,
        transaction_type=TransactionType.REVENUE,
        description="Venda",
        amount=Decimal("100"),
        competence_date=date(2026, 1, 1),
        payment_date=date(2026, 1, 1),
        status=TransactionStatus.PAID,
    )

    assert repository.create(data).amount == Decimal("100")
    assert repository.get(transaction.id) is transaction
    items, total = repository.list(
        company_id,
        1,
        20,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        transaction_type=TransactionType.REVENUE,
        category_id=category_id,
        status=TransactionStatus.PAID,
        minimum_amount=Decimal("1"),
        maximum_amount=Decimal("200"),
    )
    assert items == [transaction]
    assert total == 1
    repository.update(transaction, TransactionUpdate(description="Venda atualizada"))
    assert transaction.description == "Venda atualizada"
    repository.delete(transaction)
    session.delete.assert_called_once_with(transaction)


def test_import_repository_full_lifecycle() -> None:
    session = MagicMock()
    company_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    batch = ImportBatch(
        id=batch_id,
        company_id=company_id,
        file_name="data.csv",
        file_hash="a" * 64,
        import_type="transactions_csv",
        status="processing",
    )
    session.get.return_value = batch
    session.scalar.side_effect = [batch, 2, 3, uuid.uuid4(), None]
    session.scalars.side_effect = [[batch], [SimpleNamespace(id=uuid.uuid4())]]
    repository = ImportRepository(session)

    created = repository.create_batch(company_id, "data.csv", "a" * 64)
    assert created.status == "processing"
    assert repository.get_batch(batch_id) is batch
    assert repository.find_completed_file(company_id, "a" * 64) is batch
    assert repository.list_batches(company_id, 1, 20)[1] == 2
    assert repository.list_issues(batch_id, 1, 20)[1] == 3
    repository.add_raw_row(batch_id, 2, {"amount": "10"})
    issue = ValidationIssueData("amount", "invalid", "Inválido", "x")
    repository.add_issue(batch_id, 2, issue)
    assert repository.transaction_hash_exists("hash")
    assert not repository.transaction_hash_exists("other")

    prepared = PreparedTransaction(
        category_id=uuid.uuid4(),
        transaction_type="expense",
        description="Serviço",
        amount=Decimal("50"),
        competence_date=date(2026, 1, 1),
        due_date=None,
        payment_date=date(2026, 1, 1),
        status="paid",
        payment_method=None,
        source="csv",
        external_id=None,
        transaction_hash="hash",
    )
    repository.add_transaction(company_id, batch_id, prepared)
    completed = repository.complete_batch(batch, total=4, valid=3, rejected=1)
    assert completed.status == "completed_with_errors"
    completed = repository.complete_batch(batch, total=4, valid=4, rejected=0)
    assert completed.status == "completed"
    failed = repository.fail_batch(batch, "erro")
    assert failed.status == "failed"
    assert session.rollback.called


def test_user_repository_queries_and_create() -> None:
    session = MagicMock()
    user = User(
        id=uuid.uuid4(),
        name="Admin",
        email="admin@example.com",
        password_hash="hash",
        role="admin",
    )
    session.scalar.side_effect = [2, user, 1, 2]
    session.get.return_value = user
    session.scalars.return_value = [user]
    repository = UserRepository(session)

    assert repository.count() == 2
    assert repository.get(user.id) is user
    assert repository.get_by_email("ADMIN@example.com") is user
    assert repository.create(user) is user
    assert repository.list(1, 20, None, True) == ([user], 1)
    assert repository.list(2, 10, uuid.uuid4(), False) == ([user], 2)
    updated = repository.update(
        user,
        UserUpdate(name="Administrador", role=UserRole.ADMIN, is_active=False),
    )
    assert updated.name == "Administrador"
    assert updated.role == "admin"
    assert not updated.is_active
    session.add.assert_called_with(user)
