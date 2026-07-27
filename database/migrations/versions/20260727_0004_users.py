"""Add users for authentication and role-based access control."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260727_0004"
down_revision: str | None = "20260727_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "users",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("company_id", uuid_type),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("role IN ('admin', 'analyst', 'manager')", name="ck_user_role"),
        sa.ForeignKeyConstraint(["company_id"], ["core.companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        schema="core",
    )
    op.create_index("ix_users_company_id", "users", ["company_id"], schema="core")
    op.create_index("ix_users_email", "users", ["email"], unique=True, schema="core")


def downgrade() -> None:
    op.drop_table("users", schema="core")
