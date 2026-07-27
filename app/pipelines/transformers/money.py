from decimal import Decimal, InvalidOperation


def parse_brl_amount(value: str | int | float | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))

    cleaned = value.replace("R$", "").replace("\u00a0", "").replace(" ", "").strip()
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")

    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Valor monetário inválido: {value}") from exc
