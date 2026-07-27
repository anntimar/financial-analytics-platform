import argparse
import calendar
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import numpy as np
from faker import Faker
from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.category import Category
from app.models.company import Company
from app.models.transaction import Transaction
from app.pipelines.transformers.hash import build_transaction_hash

SEED = 20260727
END_MONTH = date(2026, 7, 1)
MONTH_COUNT = 24
NAMESPACE = uuid.UUID("d90e1f68-809e-4fb2-9790-19072d187b5b")


@dataclass(frozen=True)
class DemoCompany:
    key: str
    name: str
    trade_name: str
    document_number: str
    industry: str
    city: str
    state: str
    scale: Decimal


COMPANIES = (
    DemoCompany(
        "aurora",
        "Aurora Comércio Digital Ltda.",
        "Aurora Digital",
        "11111111000191",
        "Comércio eletrônico",
        "Fortaleza",
        "CE",
        Decimal("1.00"),
    ),
    DemoCompany(
        "nordeste",
        "Nordeste Serviços Empresariais Ltda.",
        "Nordeste Serviços",
        "22222222000191",
        "Serviços profissionais",
        "Recife",
        "PE",
        Decimal("0.72"),
    ),
    DemoCompany(
        "verde",
        "Verde Logística Sustentável Ltda.",
        "Verde Log",
        "33333333000191",
        "Logística",
        "Natal",
        "RN",
        Decimal("1.35"),
    ),
)

CATEGORIES: dict[str, tuple[str, ...]] = {
    "revenue": ("Vendas", "Serviços", "Assinaturas"),
    "expense": (
        "Pessoal",
        "Fornecedores",
        "Impostos",
        "Marketing",
        "Tecnologia",
        "Aluguel",
        "Logística",
        "Administrativo",
    ),
}

REVENUE_WEIGHTS = np.array([0.55, 0.28, 0.17])
EXPENSE_WEIGHTS = np.array([0.34, 0.24, 0.12, 0.08, 0.07, 0.06, 0.05, 0.04])
BASE_AMOUNTS = {
    "Vendas": (3200, 0.85),
    "Serviços": (5200, 0.65),
    "Assinaturas": (800, 0.45),
    "Pessoal": (4200, 0.35),
    "Fornecedores": (2600, 0.70),
    "Impostos": (1900, 0.55),
    "Marketing": (1200, 0.80),
    "Tecnologia": (850, 0.65),
    "Aluguel": (3500, 0.12),
    "Logística": (1450, 0.75),
    "Administrativo": (700, 0.70),
}


def deterministic_uuid(value: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, value)


def month_sequence() -> list[date]:
    months = []
    year = END_MONTH.year
    month = END_MONTH.month
    for offset in range(MONTH_COUNT - 1, -1, -1):
        absolute = year * 12 + month - 1 - offset
        months.append(date(absolute // 12, absolute % 12 + 1, 1))
    return months


def ensure_company(session: Session, spec: DemoCompany) -> Company:
    company = session.scalar(select(Company).where(Company.document_number == spec.document_number))
    if company:
        return company
    company = Company(
        id=deterministic_uuid(f"company:{spec.key}"),
        name=spec.name,
        trade_name=spec.trade_name,
        document_number=spec.document_number,
        industry=spec.industry,
        city=spec.city,
        state=spec.state,
    )
    session.add(company)
    session.flush()
    return company


def ensure_categories(session: Session, company: Company, company_key: str) -> dict[str, Category]:
    existing = {
        category.name: category
        for category in session.scalars(select(Category).where(Category.company_id == company.id))
    }
    for transaction_type, names in CATEGORIES.items():
        for name in names:
            if name not in existing:
                category = Category(
                    id=deterministic_uuid(f"category:{company_key}:{name}"),
                    company_id=company.id,
                    name=name,
                    transaction_type=transaction_type,
                )
                session.add(category)
                existing[name] = category
    session.flush()
    return existing


def choose_status(rng: np.random.Generator, transaction_type: str, due_date: date) -> str:
    if transaction_type == "revenue":
        status = str(
            rng.choice(
                ["paid", "pending", "overdue", "partially_paid", "cancelled"],
                p=[0.80, 0.10, 0.07, 0.02, 0.01],
            )
        )
    else:
        status = str(
            rng.choice(
                ["paid", "pending", "overdue", "partially_paid", "cancelled"],
                p=[0.90, 0.05, 0.025, 0.015, 0.01],
            )
        )
    if status == "overdue" and due_date >= date(2026, 7, 27):
        return "pending"
    return status


def generate_amount(
    rng: np.random.Generator,
    category: str,
    spec: DemoCompany,
    reference_month: date,
    month_index: int,
) -> Decimal:
    median, sigma = BASE_AMOUNTS[category]
    amount = Decimal(str(rng.lognormal(np.log(median), sigma))) * spec.scale
    if category in CATEGORIES["revenue"]:
        amount *= Decimal("1.015") ** month_index
        if reference_month.month == 12:
            amount *= Decimal("1.28")
    if category == "Impostos" and reference_month.month == 1:
        amount *= Decimal("1.45")
    if rng.random() < 0.007:
        amount *= Decimal(str(rng.uniform(3.5, 7.0)))
    return amount.quantize(Decimal("0.01"))


def generate_transactions(
    spec: DemoCompany,
    company: Company,
    categories: dict[str, Category],
    row_count: int,
    rng: np.random.Generator,
    fake: Faker,
) -> list[dict[str, Any]]:
    months = month_sequence()
    rows: list[dict[str, Any]] = []
    for index in range(row_count):
        month_index = int(rng.integers(0, len(months)))
        reference_month = months[month_index]
        days_in_month = calendar.monthrange(reference_month.year, reference_month.month)[1]
        competence_date = reference_month.replace(day=int(rng.integers(1, days_in_month + 1)))
        transaction_type = "revenue" if rng.random() < 0.46 else "expense"
        names = CATEGORIES[transaction_type]
        weights = REVENUE_WEIGHTS if transaction_type == "revenue" else EXPENSE_WEIGHTS
        category_name = str(rng.choice(names, p=weights))
        category = categories[category_name]
        amount = generate_amount(rng, category_name, spec, reference_month, month_index)
        due_date = competence_date + timedelta(days=int(rng.integers(5, 31)))
        status = choose_status(rng, transaction_type, due_date)
        payment_date = None
        if status in {"paid", "partially_paid"}:
            payment_date = due_date + timedelta(days=int(rng.integers(-3, 9)))
        external_id = f"SYN-{spec.key.upper()}-{index + 1:06d}"
        description = (
            f"Recebimento de {category_name.lower()} — {fake.company()}"
            if transaction_type == "revenue"
            else f"Pagamento de {category_name.lower()} — {fake.company()}"
        )
        transaction_hash = build_transaction_hash(
            company.id,
            category.id,
            description,
            amount,
            competence_date,
            transaction_type,
            external_id,
        )
        rows.append(
            {
                "id": uuid.uuid4(),
                "company_id": company.id,
                "category_id": category.id,
                "transaction_type": transaction_type,
                "description": description[:255],
                "amount": amount,
                "competence_date": competence_date,
                "due_date": due_date,
                "payment_date": payment_date,
                "status": status,
                "payment_method": str(rng.choice(["pix", "boleto", "transferência", "cartão"])),
                "source": "synthetic",
                "external_id": external_id,
                "transaction_hash": transaction_hash,
            }
        )
    return rows


def seed(row_count: int) -> None:
    rng = np.random.default_rng(SEED)
    fake = Faker("pt_BR")
    fake.seed_instance(SEED)
    allocations = [
        row_count // len(COMPANIES) + (1 if index < row_count % len(COMPANIES) else 0)
        for index in range(len(COMPANIES))
    ]

    with SessionLocal() as session:
        inserted = 0
        for spec, company_rows in zip(COMPANIES, allocations, strict=True):
            company = ensure_company(session, spec)
            categories = ensure_categories(session, company, spec.key)
            existing_count = session.scalar(
                select(func.count())
                .select_from(Transaction)
                .where(
                    Transaction.company_id == company.id,
                    Transaction.source == "synthetic",
                )
            )
            if existing_count:
                print(
                    f"{spec.trade_name}: {existing_count} transações sintéticas "
                    "já existem; carga ignorada."
                )
                continue
            rows = generate_transactions(spec, company, categories, company_rows, rng, fake)
            for start in range(0, len(rows), 2_000):
                session.execute(insert(Transaction), rows[start : start + 2_000])
            inserted += len(rows)
            print(f"{spec.trade_name}: {len(rows)} transações geradas.")
        session.commit()
        print(f"Carga concluída: {inserted} novas transações sintéticas.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Carrega dados sintéticos de demonstração.")
    parser.add_argument(
        "--rows",
        type=int,
        default=20_000,
        help="Quantidade total de transações (padrão: 20000).",
    )
    args = parser.parse_args()
    if args.rows < len(COMPANIES):
        parser.error(f"--rows deve ser pelo menos {len(COMPANIES)}")
    seed(args.rows)


if __name__ == "__main__":
    main()
