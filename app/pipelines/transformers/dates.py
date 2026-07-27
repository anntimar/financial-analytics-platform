from datetime import date, datetime


def parse_date(value: str, *, required: bool = False) -> date | None:
    cleaned = value.strip()
    if not cleaned:
        if required:
            raise ValueError("data obrigatória")
        return None

    for date_format in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(cleaned, date_format).date()
        except ValueError:
            continue
    raise ValueError("use AAAA-MM-DD ou DD/MM/AAAA")
