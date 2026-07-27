import hashlib
import uuid
from datetime import date
from decimal import Decimal


def build_transaction_hash(
    company_id: uuid.UUID,
    category_id: uuid.UUID,
    description: str,
    amount: Decimal,
    competence_date: date,
    transaction_type: str,
    external_id: str | None,
) -> str:
    content = "|".join(
        (
            str(company_id),
            str(category_id),
            description.strip().casefold(),
            str(amount.quantize(Decimal("0.01"))),
            competence_date.isoformat(),
            transaction_type,
            external_id or "",
        )
    )
    return hashlib.sha256(content.encode()).hexdigest()
