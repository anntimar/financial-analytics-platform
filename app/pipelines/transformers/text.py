import re
import unicodedata


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", normalized.strip().lower())


def normalize_column_name(value: str) -> str:
    normalized = normalize_text(value) or ""
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
