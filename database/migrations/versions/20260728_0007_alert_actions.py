"""Add operational actions for calculated financial alerts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260728_0007"
down_revision: str | None = "20260727_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "alert_actions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("company_id", uuid_type, nullable=False),
        sa.Column("alert_code", sa.String(180), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("note", sa.String(500)),
        sa.Column("updated_by", uuid_type, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "status IN ('open', 'acknowledged', 'resolved')",
            name="ck_alert_action_status",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["core.companies.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["core.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "alert_code",
            "reference_date",
            name="uq_alert_action_reference",
        ),
        schema="core",
    )
    op.create_index(
        "ix_alert_actions_company_id",
        "alert_actions",
        ["company_id"],
        schema="core",
    )


def downgrade() -> None:
    op.drop_table("alert_actions", schema="core")
