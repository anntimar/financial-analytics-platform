"""Add cost centers and optional transaction links."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260728_0009"
down_revision: str | None = "20260728_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "cost_centers",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("company_id", uuid_type, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(30)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["company_id"], ["core.companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "name", name="uq_cost_center_company_name"),
        schema="core",
    )
    op.create_index("ix_cost_centers_company_id", "cost_centers", ["company_id"], schema="core")
    op.add_column("transactions", sa.Column("cost_center_id", uuid_type), schema="core")
    op.create_foreign_key(
        "fk_transactions_cost_center_id",
        "transactions",
        "cost_centers",
        ["cost_center_id"],
        ["id"],
        source_schema="core",
        referent_schema="core",
    )
    op.create_index(
        "ix_transactions_cost_center_id",
        "transactions",
        ["cost_center_id"],
        schema="core",
    )


def downgrade() -> None:
    op.drop_column("transactions", "cost_center_id", schema="core")
    op.drop_table("cost_centers", schema="core")
