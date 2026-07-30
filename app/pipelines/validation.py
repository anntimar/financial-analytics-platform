import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.pipelines.transformers.dates import parse_date
from app.pipelines.transformers.hash import build_transaction_hash
from app.pipelines.transformers.money import parse_brl_amount
from app.schemas.category import TransactionType
from app.schemas.transaction import TransactionStatus


@dataclass(frozen=True)
class ValidationIssueData:
    field: str
    code: str
    message: str
    raw_value: str | None
    severity: str = "error"


@dataclass(frozen=True)
class PreparedTransaction:
    category_id: uuid.UUID
    transaction_type: str
    description: str
    amount: Decimal
    competence_date: date
    due_date: date | None
    payment_date: date | None
    status: str
    payment_method: str | None
    source: str
    external_id: str | None
    transaction_hash: str
    subcategory_id: uuid.UUID | None = None


def _enum_value(
    value: str, enum_type: type[TransactionType] | type[TransactionStatus], field: str
) -> tuple[str | None, ValidationIssueData | None]:
    try:
        return enum_type(value.strip().lower()).value, None
    except ValueError:
        allowed = ", ".join(item.value for item in enum_type)
        return None, ValidationIssueData(
            field, f"invalid_{field}", f"Valor inválido. Use: {allowed}.", value
        )


def prepare_transaction(
    row: dict[str, str], company_id: uuid.UUID
) -> tuple[PreparedTransaction | None, list[ValidationIssueData]]:
    issues: list[ValidationIssueData] = []

    description = row.get("description", "").strip()
    if len(description) < 3:
        issues.append(
            ValidationIssueData(
                "description",
                "invalid_description",
                "Descrição deve ter ao menos 3 caracteres.",
                description,
            )
        )

    try:
        category_id = uuid.UUID(row.get("category_id", ""))
    except ValueError:
        category_id = None
        issues.append(
            ValidationIssueData(
                "category_id",
                "invalid_category_id",
                "category_id deve ser um UUID válido.",
                row.get("category_id"),
            )
        )

    raw_subcategory_id = row.get("subcategory_id", "").strip()
    try:
        subcategory_id = uuid.UUID(raw_subcategory_id) if raw_subcategory_id else None
    except ValueError:
        subcategory_id = None
        issues.append(
            ValidationIssueData(
                "subcategory_id",
                "invalid_subcategory_id",
                "subcategory_id deve ser um UUID válido.",
                raw_subcategory_id,
            )
        )

    transaction_type, type_issue = _enum_value(
        row.get("transaction_type", ""), TransactionType, "transaction_type"
    )
    if type_issue:
        issues.append(type_issue)

    status, status_issue = _enum_value(row.get("status", ""), TransactionStatus, "status")
    if status_issue:
        issues.append(status_issue)

    try:
        amount = parse_brl_amount(row.get("amount", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        amount = None
        issues.append(
            ValidationIssueData(
                "amount",
                "invalid_amount",
                "Valor deve ser monetário e maior que zero.",
                row.get("amount"),
            )
        )

    parsed_dates: dict[str, date | None] = {}
    date_fields = (
        ("competence_date", True),
        ("due_date", False),
        ("payment_date", False),
    )
    for field, required in date_fields:
        try:
            parsed_dates[field] = parse_date(row.get(field, ""), required=required)
        except ValueError as exc:
            parsed_dates[field] = None
            issues.append(ValidationIssueData(field, f"invalid_{field}", str(exc), row.get(field)))

    payment_date = parsed_dates["payment_date"]
    if status == TransactionStatus.PAID and payment_date is None:
        issues.append(
            ValidationIssueData(
                "payment_date",
                "missing_payment_date",
                "Data de pagamento é obrigatória para status paid.",
                row.get("payment_date"),
            )
        )

    competence_date = parsed_dates["competence_date"]
    due_date = parsed_dates["due_date"]
    if competence_date and due_date and due_date < competence_date:
        issues.append(
            ValidationIssueData(
                "due_date",
                "due_before_competence",
                "Vencimento não pode ser anterior à competência.",
                row.get("due_date"),
            )
        )

    if issues or category_id is None or amount is None or competence_date is None:
        return None, issues
    assert transaction_type is not None
    assert status is not None
    external_id = row.get("external_id") or None
    prepared = PreparedTransaction(
        category_id=category_id,
        transaction_type=transaction_type,
        description=description,
        amount=amount,
        competence_date=competence_date,
        due_date=due_date,
        payment_date=payment_date,
        status=status,
        payment_method=row.get("payment_method") or None,
        source="csv",
        external_id=external_id,
        transaction_hash=build_transaction_hash(
            company_id,
            category_id,
            description,
            amount,
            competence_date,
            transaction_type,
            external_id,
        ),
        subcategory_id=subcategory_id,
    )
    return prepared, []
