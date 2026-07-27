from decimal import Decimal

import pytest

from app.pipelines.transformers.money import parse_brl_amount


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("R$ 1.250,90", Decimal("1250.90")),
        ("12,50", Decimal("12.50")),
        (10, Decimal("10")),
        (10.5, Decimal("10.5")),
        (Decimal("3.14"), Decimal("3.14")),
    ],
)
def test_parse_brl_amount(raw: str | int | float | Decimal, expected: Decimal) -> None:
    assert parse_brl_amount(raw) == expected


def test_parse_brl_amount_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="Valor monetário inválido"):
        parse_brl_amount("não é dinheiro")
