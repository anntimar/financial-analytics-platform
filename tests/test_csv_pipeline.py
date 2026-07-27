import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import AppError
from app.pipelines.readers.csv_reader import read_csv_rows
from app.pipelines.transformers.dates import parse_date
from app.pipelines.transformers.hash import build_transaction_hash
from app.pipelines.validation import prepare_transaction


def valid_row(category_id: uuid.UUID) -> dict[str, str]:
    return {
        "category_id": str(category_id),
        "description": "Mensalidade de julho",
        "transaction_type": "revenue",
        "amount": "R$ 1.250,90",
        "competence_date": "01/07/2026",
        "due_date": "10/07/2026",
        "payment_date": "10/07/2026",
        "status": "paid",
        "payment_method": "pix",
        "external_id": "EXT-1",
    }


def test_csv_reader_accepts_semicolon_and_normalizes_headers() -> None:
    content = (
        "Category ID;Description;Transaction Type;Amount;Competence Date;Status\n"
        f"{uuid.uuid4()};Venda;revenue;100,50;2026-07-01;pending\n"
    ).encode()

    rows = read_csv_rows(content)

    assert len(rows) == 1
    assert rows[0]["transaction_type"] == "revenue"
    assert rows[0]["amount"] == "100,50"


def test_csv_reader_rejects_missing_columns() -> None:
    with pytest.raises(AppError, match="Colunas obrigatórias ausentes"):
        read_csv_rows(b"description,amount\nVenda,100\n")


def test_csv_reader_rejects_non_utf8() -> None:
    with pytest.raises(AppError, match="UTF-8"):
        read_csv_rows(b"\xff\xfe\x00")


def test_prepare_transaction_converts_valid_row() -> None:
    company_id = uuid.uuid4()
    category_id = uuid.uuid4()

    prepared, issues = prepare_transaction(valid_row(category_id), company_id)

    assert issues == []
    assert prepared is not None
    assert prepared.amount == Decimal("1250.90")
    assert prepared.competence_date == date(2026, 7, 1)
    assert prepared.category_id == category_id
    assert len(prepared.transaction_hash) == 64


def test_prepare_transaction_collects_multiple_issues() -> None:
    row = valid_row(uuid.uuid4())
    row.update(
        {
            "category_id": "inválido",
            "description": "x",
            "transaction_type": "credit",
            "amount": "-5",
            "competence_date": "31/02/2026",
            "due_date": "ontem",
            "payment_date": "",
            "status": "paid",
        }
    )

    prepared, issues = prepare_transaction(row, uuid.uuid4())

    assert prepared is None
    assert {issue.code for issue in issues} >= {
        "invalid_category_id",
        "invalid_description",
        "invalid_transaction_type",
        "invalid_amount",
        "invalid_competence_date",
        "invalid_due_date",
        "missing_payment_date",
    }


def test_prepare_transaction_rejects_due_date_before_competence() -> None:
    row = valid_row(uuid.uuid4())
    row["due_date"] = "2026-06-30"

    prepared, issues = prepare_transaction(row, uuid.uuid4())

    assert prepared is None
    assert issues[0].code == "due_before_competence"


def test_parse_date_supports_optional_empty_value() -> None:
    assert parse_date("") is None
    with pytest.raises(ValueError, match="obrigatória"):
        parse_date("", required=True)


def test_transaction_hash_is_deterministic() -> None:
    company_id = uuid.uuid4()
    category_id = uuid.uuid4()
    values = (
        company_id,
        category_id,
        "Venda",
        Decimal("100.00"),
        date(2026, 7, 1),
        "revenue",
        None,
    )
    assert build_transaction_hash(*values) == build_transaction_hash(*values)
