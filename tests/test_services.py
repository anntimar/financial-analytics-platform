import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.schemas.category import CategoryCreate, TransactionType
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.schemas.transaction import (
    TransactionCreate,
    TransactionStatus,
    TransactionUpdate,
)
from app.services.category_service import CategoryService
from app.services.company_service import CompanyService
from app.services.transaction_service import TransactionService


def test_company_service_rejects_duplicate_document() -> None:
    repository = Mock()
    repository.get_by_document.return_value = SimpleNamespace(id=uuid.uuid4())
    service = CompanyService(repository)

    with pytest.raises(ConflictError):
        service.create(CompanyCreate(name="Empresa Demo", document_number="12345678000199"))

    repository.create.assert_not_called()


def test_company_service_creates_company() -> None:
    repository = Mock()
    repository.get_by_document.return_value = None
    created = SimpleNamespace(id=uuid.uuid4())
    repository.create.return_value = created
    service = CompanyService(repository)

    result = service.create(CompanyCreate(name="Empresa Demo"))

    assert result is created
    repository.create.assert_called_once()


def test_company_service_gets_lists_updates_and_deactivates() -> None:
    company_id = uuid.uuid4()
    now = datetime.now(UTC)
    company = SimpleNamespace(
        id=company_id,
        name="Empresa Demo",
        trade_name=None,
        document_number=None,
        industry=None,
        city=None,
        state=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    repository = Mock()
    repository.get.return_value = company
    repository.list.return_value = ([company], 1)
    repository.update.return_value = company
    service = CompanyService(repository)

    assert service.get(company_id) is company
    page = service.list(page=1, page_size=20, active_only=True)
    assert page.total == 1
    service.update(company_id, CompanyUpdate(name="Novo nome"))
    service.deactivate(company_id)

    assert repository.update.call_count == 2


def test_company_service_raises_when_company_does_not_exist() -> None:
    repository = Mock()
    repository.get.return_value = None

    with pytest.raises(NotFoundError):
        CompanyService(repository).get(uuid.uuid4())


def test_category_service_validates_company_and_duplicate() -> None:
    company_repository = Mock()
    category_repository = Mock()
    data = CategoryCreate(
        company_id=uuid.uuid4(),
        name="Marketing",
        transaction_type=TransactionType.EXPENSE,
    )
    service = CategoryService(category_repository, company_repository)

    company_repository.get.return_value = None
    with pytest.raises(NotFoundError):
        service.create(data)

    company_repository.get.return_value = SimpleNamespace(id=data.company_id)
    category_repository.find_duplicate.return_value = SimpleNamespace(id=uuid.uuid4())
    with pytest.raises(ConflictError):
        service.create(data)


def test_category_service_creates_and_lists() -> None:
    now = datetime.now(UTC)
    data = CategoryCreate(
        company_id=uuid.uuid4(),
        name="Marketing",
        transaction_type=TransactionType.EXPENSE,
    )
    category = SimpleNamespace(
        id=uuid.uuid4(),
        company_id=data.company_id,
        name=data.name,
        transaction_type=data.transaction_type,
        is_active=True,
        created_at=now,
    )
    company_repository = Mock()
    company_repository.get.return_value = SimpleNamespace(id=data.company_id)
    category_repository = Mock()
    category_repository.find_duplicate.return_value = None
    category_repository.create.return_value = category
    category_repository.list.return_value = ([category], 1)
    service = CategoryService(category_repository, company_repository)

    assert service.create(data) is category
    page = service.list(data.company_id, 1, 20, TransactionType.EXPENSE)
    assert page.total == 1


def test_category_service_raises_when_category_does_not_exist() -> None:
    category_repository = Mock()
    category_repository.get.return_value = None
    service = CategoryService(category_repository, Mock())

    with pytest.raises(NotFoundError):
        service.get(uuid.uuid4())


def test_transaction_service_validates_category_ownership() -> None:
    company_id = uuid.uuid4()
    company_repository = Mock()
    company_repository.get.return_value = SimpleNamespace(id=company_id)
    category_repository = Mock()
    category_repository.get.return_value = SimpleNamespace(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        transaction_type=TransactionType.REVENUE,
    )
    service = TransactionService(Mock(), company_repository, category_repository)
    data = TransactionCreate(
        company_id=company_id,
        category_id=category_repository.get.return_value.id,
        transaction_type=TransactionType.REVENUE,
        description="Venda mensal",
        amount=Decimal("100"),
        competence_date=date(2026, 7, 1),
        payment_date=date(2026, 7, 1),
        status=TransactionStatus.PAID,
    )

    with pytest.raises(AppError, match="não pertence"):
        service.create(data)


def test_transaction_service_rejects_invalid_date_range() -> None:
    service = TransactionService(Mock(), Mock(), Mock())

    with pytest.raises(AppError, match="start_date"):
        service.list(
            company_id=uuid.uuid4(),
            page=1,
            page_size=20,
            start_date=date(2026, 7, 31),
            end_date=date(2026, 7, 1),
            transaction_type=TransactionType.REVENUE,
            category_id=None,
            status=None,
            minimum_amount=None,
            maximum_amount=None,
        )


def test_transaction_service_rejects_invalid_amount_range() -> None:
    service = TransactionService(Mock(), Mock(), Mock())

    with pytest.raises(AppError, match="minimum_amount"):
        service.list(
            company_id=uuid.uuid4(),
            page=1,
            page_size=20,
            start_date=None,
            end_date=None,
            transaction_type=None,
            category_id=None,
            status=None,
            minimum_amount=Decimal("200"),
            maximum_amount=Decimal("100"),
        )


def test_transaction_service_full_lifecycle() -> None:
    company_id = uuid.uuid4()
    category_id = uuid.uuid4()
    transaction_id = uuid.uuid4()
    transaction = SimpleNamespace(
        id=transaction_id,
        company_id=company_id,
        category_id=category_id,
        transaction_type="revenue",
        payment_date=None,
    )
    repository = Mock()
    repository.get.return_value = transaction
    repository.create.return_value = transaction
    repository.update.return_value = transaction
    repository.list.return_value = ([], 0)
    company_repository = Mock()
    company_repository.get.return_value = SimpleNamespace(id=company_id)
    category_repository = Mock()
    category_repository.get.return_value = SimpleNamespace(
        id=category_id,
        company_id=company_id,
        transaction_type=TransactionType.REVENUE,
    )
    service = TransactionService(repository, company_repository, category_repository)
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
    assert service.create(data) is transaction
    assert service.get(transaction_id) is transaction
    page = service.list(company_id, 1, 20, None, None, None, None, None, None, None)
    assert page.total == 0
    assert (
        service.update(
            transaction_id,
            TransactionUpdate(category_id=category_id),
        )
        is transaction
    )
    service.delete(transaction_id)
    repository.delete.assert_called_once_with(transaction)


def test_transaction_service_validation_failures() -> None:
    service = TransactionService(Mock(), Mock(), Mock())
    service.company_repository.get.return_value = None
    data = TransactionCreate(
        company_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        transaction_type=TransactionType.EXPENSE,
        description="Conta",
        amount=Decimal("10"),
        competence_date=date(2026, 1, 1),
        status=TransactionStatus.PENDING,
    )
    with pytest.raises(NotFoundError):
        service.create(data)
    service.repository.get.return_value = None
    with pytest.raises(NotFoundError):
        service.get(uuid.uuid4())
    service.category_repository.get.return_value = None
    with pytest.raises(NotFoundError):
        service._validate_category(data.category_id, data.company_id, data.transaction_type)
    service.category_repository.get.return_value = SimpleNamespace(
        company_id=data.company_id, transaction_type=TransactionType.REVENUE
    )
    with pytest.raises(AppError, match="tipo"):
        service._validate_category(data.category_id, data.company_id, data.transaction_type)


def test_transaction_update_paid_requires_payment_date() -> None:
    repository = Mock()
    repository.get.return_value = SimpleNamespace(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        transaction_type="expense",
        payment_date=None,
    )
    service = TransactionService(repository, Mock(), Mock())
    with pytest.raises(AppError, match="payment_date"):
        service.update(
            repository.get.return_value.id,
            TransactionUpdate(status=TransactionStatus.PAID),
        )


def test_transaction_service_validates_account() -> None:
    company_id = uuid.uuid4()
    account_id = uuid.uuid4()
    accounts = Mock()
    service = TransactionService(Mock(), Mock(), Mock(), accounts)

    accounts.get.return_value = None
    with pytest.raises(NotFoundError):
        service._validate_account(account_id, company_id)
    accounts.get.return_value = SimpleNamespace(company_id=uuid.uuid4(), is_active=True)
    with pytest.raises(AppError, match="não pertence"):
        service._validate_account(account_id, company_id)
    accounts.get.return_value = SimpleNamespace(company_id=company_id, is_active=False)
    with pytest.raises(AppError, match="inativa"):
        service._validate_account(account_id, company_id)
    accounts.get.return_value = SimpleNamespace(company_id=company_id, is_active=True)
    service._validate_account(account_id, company_id)


def test_transaction_service_validates_subcategory_and_filter() -> None:
    company_id = uuid.uuid4()
    category_id = uuid.uuid4()
    subcategory_id = uuid.uuid4()
    repository = Mock()
    repository.list.return_value = ([], 0)
    companies = Mock()
    companies.get.return_value = SimpleNamespace(id=company_id)
    categories = Mock()
    categories.get.return_value = SimpleNamespace(
        id=category_id,
        company_id=company_id,
        transaction_type=TransactionType.EXPENSE,
    )
    subcategories = Mock()
    service = TransactionService(repository, companies, categories, None, subcategories)
    payload = TransactionCreate(
        company_id=company_id,
        category_id=category_id,
        subcategory_id=subcategory_id,
        transaction_type=TransactionType.EXPENSE,
        description="Tráfego pago",
        amount=Decimal("100"),
        competence_date=date(2026, 1, 1),
        payment_date=date(2026, 1, 1),
        status=TransactionStatus.PAID,
    )

    subcategories.get.return_value = None
    with pytest.raises(NotFoundError, match="Subcategoria"):
        service.create(payload)
    subcategories.get.return_value = SimpleNamespace(category_id=uuid.uuid4(), is_active=True)
    with pytest.raises(AppError, match="não pertence"):
        service.create(payload)
    subcategories.get.return_value = SimpleNamespace(category_id=category_id, is_active=False)
    with pytest.raises(AppError, match="inativa"):
        service.create(payload)

    subcategories.get.return_value = SimpleNamespace(category_id=category_id, is_active=True)
    repository.create.return_value = SimpleNamespace(id=uuid.uuid4())
    assert service.create(payload) is repository.create.return_value
    service.list(
        company_id,
        1,
        20,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        subcategory_id=subcategory_id,
    )
    assert repository.list.call_args.kwargs["subcategory_id"] == subcategory_id

    transaction = SimpleNamespace(
        id=uuid.uuid4(),
        company_id=company_id,
        category_id=category_id,
        subcategory_id=subcategory_id,
        transaction_type="expense",
        payment_date=date(2026, 1, 1),
    )
    repository.get.return_value = transaction
    repository.update.return_value = transaction
    service.update(transaction.id, TransactionUpdate(subcategory_id=subcategory_id))
    service.update(transaction.id, TransactionUpdate(category_id=category_id))
