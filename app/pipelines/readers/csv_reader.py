import csv
import io

from app.core.exceptions import AppError
from app.pipelines.transformers.text import normalize_column_name

REQUIRED_COLUMNS = {
    "category_id",
    "description",
    "transaction_type",
    "amount",
    "competence_date",
    "status",
}


def read_csv_rows(content: bytes) -> list[dict[str, str]]:
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AppError("O CSV deve usar codificação UTF-8.") from exc

    try:
        dialect = csv.Sniffer().sniff(decoded[:4096], delimiters=",;")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(decoded), dialect=dialect)
    if reader.fieldnames is None:
        raise AppError("O arquivo CSV não possui cabeçalho.")

    normalized_fields = [normalize_column_name(field) for field in reader.fieldnames]
    missing = REQUIRED_COLUMNS - set(normalized_fields)
    if missing:
        columns = ", ".join(sorted(missing))
        raise AppError(f"Colunas obrigatórias ausentes: {columns}.")

    rows: list[dict[str, str]] = []
    for source_row in reader:
        row = {
            normalize_column_name(key): (value.strip() if value else "")
            for key, value in source_row.items()
            if key is not None
        }
        if any(row.values()):
            rows.append(row)
    return rows
