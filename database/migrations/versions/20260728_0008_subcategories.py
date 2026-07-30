"""Add financial subcategories and transaction links."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260728_0008"
down_revision: str | None = "20260728_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "subcategories",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("category_id", uuid_type, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["category_id"], ["core.categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category_id", "name", name="uq_subcategory_category_name"),
        schema="core",
    )
    op.create_index(
        "ix_subcategories_category_id",
        "subcategories",
        ["category_id"],
        schema="core",
    )
    op.add_column(
        "transactions",
        sa.Column("subcategory_id", uuid_type),
        schema="core",
    )
    op.create_foreign_key(
        "fk_transactions_subcategory_id",
        "transactions",
        "subcategories",
        ["subcategory_id"],
        ["id"],
        source_schema="core",
        referent_schema="core",
    )
    op.create_index(
        "ix_transactions_subcategory_id",
        "transactions",
        ["subcategory_id"],
        schema="core",
    )


def downgrade() -> None:
    op.drop_column("transactions", "subcategory_id", schema="core")
    op.drop_table("subcategories", schema="core")
