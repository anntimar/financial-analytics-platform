import uuid
from decimal import Decimal

import numpy as np
from faker import Faker

from app.models.category import Category
from app.models.company import Company
from scripts.seed_demo_data import (
    CATEGORIES,
    COMPANIES,
    deterministic_uuid,
    generate_transactions,
    month_sequence,
)


def test_month_sequence_has_24_ordered_months() -> None:
    months = month_sequence()
    assert len(months) == 24
    assert months[0].isoformat() == "2024-08-01"
    assert months[-1].isoformat() == "2026-07-01"
    assert months == sorted(months)


def test_deterministic_uuid_is_stable() -> None:
    assert deterministic_uuid("company:aurora") == deterministic_uuid("company:aurora")
    assert deterministic_uuid("company:aurora") != deterministic_uuid("company:verde")


def test_generate_transactions_produces_valid_financial_rows() -> None:
    spec = COMPANIES[0]
    company = Company(
        id=deterministic_uuid("test-company"),
        name=spec.name,
        document_number=spec.document_number,
    )
    categories = {}
    for transaction_type, names in CATEGORIES.items():
        for name in names:
            categories[name] = Category(
                id=uuid.uuid4(),
                company_id=company.id,
                name=name,
                transaction_type=transaction_type,
            )
    rng = np.random.default_rng(42)
    fake = Faker("pt_BR")
    fake.seed_instance(42)

    rows = generate_transactions(spec, company, categories, 250, rng, fake)

    assert len(rows) == 250
    assert {row["transaction_type"] for row in rows} == {"revenue", "expense"}
    assert all(Decimal(row["amount"]) > 0 for row in rows)
    assert all(len(row["transaction_hash"]) == 64 for row in rows)
    assert all(row["source"] == "synthetic" for row in rows)
    assert all(
        row["payment_date"] is not None
        for row in rows
        if row["status"] in {"paid", "partially_paid"}
    )
