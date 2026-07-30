"""Add monthly budgets."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260727_0005"
down_revision: str | None = "20260727_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "budgets",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("company_id", uuid_type, nullable=False),
        sa.Column("category_id", uuid_type, nullable=False),
        sa.Column("transaction_type", sa.String(20), nullable=False),
        sa.Column("reference_month", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("amount >= 0", name="ck_budget_amount_positive"),
        sa.CheckConstraint("transaction_type IN ('revenue', 'expense')", name="ck_budget_type"),
        sa.ForeignKeyConstraint(["category_id"], ["core.categories.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["core.companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "category_id",
            "transaction_type",
            "reference_month",
            name="uq_budget_company_category_type_month",
        ),
        schema="core",
    )
    op.create_index("ix_budgets_company_id", "budgets", ["company_id"], schema="core")
    op.create_index("ix_budgets_category_id", "budgets", ["category_id"], schema="core")
    op.create_index("ix_budgets_reference_month", "budgets", ["reference_month"], schema="core")


def downgrade() -> None:
    op.drop_table("budgets", schema="core")
