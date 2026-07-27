"""Create initial core financial tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260727_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS raw")
    op.execute("CREATE SCHEMA IF NOT EXISTS core")
    op.execute("CREATE SCHEMA IF NOT EXISTS analytics")
    uuid_type = postgresql.UUID(as_uuid=True)

    op.create_table(
        "companies",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("trade_name", sa.String(150)),
        sa.Column("document_number", sa.String(20), unique=True),
        sa.Column("industry", sa.String(100)),
        sa.Column("city", sa.String(100)),
        sa.Column("state", sa.String(2)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="core",
    )
    op.create_table(
        "categories",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("company_id", uuid_type, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("transaction_type", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("transaction_type IN ('revenue', 'expense')", name="ck_category_type"),
        sa.ForeignKeyConstraint(["company_id"], ["core.companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "name", "transaction_type", name="uq_category_company"),
        schema="core",
    )
    op.create_index("ix_categories_company_id", "categories", ["company_id"], schema="core")
    op.create_table(
        "transactions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("company_id", uuid_type, nullable=False),
        sa.Column("category_id", uuid_type, nullable=False),
        sa.Column("transaction_type", sa.String(20), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("competence_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date()),
        sa.Column("payment_date", sa.Date()),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("payment_method", sa.String(50)),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("external_id", sa.String(100)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("amount >= 0", name="ck_transaction_amount_positive"),
        sa.CheckConstraint(
            "transaction_type IN ('revenue', 'expense')", name="ck_transaction_type"
        ),
        sa.CheckConstraint(
            "status IN ('paid', 'pending', 'overdue', 'cancelled', 'partially_paid')",
            name="ck_transaction_status",
        ),
        sa.ForeignKeyConstraint(["category_id"], ["core.categories.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["core.companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="core",
    )
    for column in ("company_id", "category_id", "transaction_type", "competence_date", "status"):
        op.create_index(f"ix_transactions_{column}", "transactions", [column], schema="core")


def downgrade() -> None:
    op.drop_table("transactions", schema="core")
    op.drop_table("categories", schema="core")
    op.drop_table("companies", schema="core")
    op.execute("DROP SCHEMA IF EXISTS analytics")
    op.execute("DROP SCHEMA IF EXISTS raw")
    op.execute("DROP SCHEMA IF EXISTS core")
