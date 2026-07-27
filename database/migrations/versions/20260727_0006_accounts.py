"""Add financial accounts and optional transaction links."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260727_0006"
down_revision: str | None = "20260727_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "accounts",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("company_id", uuid_type, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("account_type", sa.String(30), nullable=False),
        sa.Column("institution", sa.String(100)),
        sa.Column("opening_balance", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "account_type IN ('checking', 'cash', 'digital_wallet', 'credit_card', 'investment')",
            name="ck_account_type",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["core.companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="core",
    )
    op.create_index("ix_accounts_company_id", "accounts", ["company_id"], schema="core")
    op.add_column("transactions", sa.Column("account_id", uuid_type), schema="core")
    op.create_foreign_key(
        "fk_transactions_account_id",
        "transactions",
        "accounts",
        ["account_id"],
        ["id"],
        source_schema="core",
        referent_schema="core",
    )
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"], schema="core")


def downgrade() -> None:
    op.drop_column("transactions", "account_id", schema="core")
    op.drop_table("accounts", schema="core")
