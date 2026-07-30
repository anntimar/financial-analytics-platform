"""Add immutable user access audit events."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260730_0010"
down_revision: str | None = "20260728_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "user_audit_events",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("actor_user_id", uuid_type),
        sa.Column("target_user_id", uuid_type, nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("changes", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["core.users.id"]),
        sa.ForeignKeyConstraint(["target_user_id"], ["core.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="core",
    )
    for column in ("actor_user_id", "target_user_id", "action", "created_at"):
        op.create_index(
            f"ix_user_audit_events_{column}",
            "user_audit_events",
            [column],
            schema="core",
        )


def downgrade() -> None:
    op.drop_table("user_audit_events", schema="core")
