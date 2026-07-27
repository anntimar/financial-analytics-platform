"""Add transaction import and data quality tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260727_0002"
down_revision: str | None = "20260727_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "import_batches",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("company_id", uuid_type, nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("import_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("valid_rows", sa.Integer(), nullable=False),
        sa.Column("rejected_rows", sa.Integer(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        sa.ForeignKeyConstraint(["company_id"], ["core.companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="core",
    )
    op.create_index(
        "ix_import_batches_company_id",
        "import_batches",
        ["company_id"],
        schema="core",
    )
    op.create_index(
        "ix_import_batches_file_hash",
        "import_batches",
        ["file_hash"],
        schema="core",
    )
    op.create_table(
        "data_quality_issues",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("import_batch_id", uuid_type, nullable=False),
        sa.Column("row_number", sa.Integer()),
        sa.Column("field_name", sa.String(100)),
        sa.Column("issue_type", sa.String(100), nullable=False),
        sa.Column("issue_description", sa.Text(), nullable=False),
        sa.Column("raw_value", sa.Text()),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["import_batch_id"], ["core.import_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="core",
    )
    op.create_index(
        "ix_data_quality_issues_import_batch_id",
        "data_quality_issues",
        ["import_batch_id"],
        schema="core",
    )
    op.create_table(
        "imported_transactions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("import_batch_id", uuid_type, nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["import_batch_id"], ["core.import_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="raw",
    )
    op.create_index(
        "ix_imported_transactions_import_batch_id",
        "imported_transactions",
        ["import_batch_id"],
        schema="raw",
    )
    op.add_column(
        "transactions",
        sa.Column("transaction_hash", sa.String(64)),
        schema="core",
    )
    op.add_column(
        "transactions",
        sa.Column("import_batch_id", uuid_type),
        schema="core",
    )
    op.create_foreign_key(
        "fk_transactions_import_batch",
        "transactions",
        "import_batches",
        ["import_batch_id"],
        ["id"],
        source_schema="core",
        referent_schema="core",
    )
    op.create_index(
        "ix_transactions_transaction_hash",
        "transactions",
        ["transaction_hash"],
        unique=True,
        schema="core",
    )
    op.create_index(
        "ix_transactions_import_batch_id",
        "transactions",
        ["import_batch_id"],
        schema="core",
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_import_batch_id", table_name="transactions", schema="core")
    op.drop_index("ix_transactions_transaction_hash", table_name="transactions", schema="core")
    op.drop_constraint(
        "fk_transactions_import_batch",
        "transactions",
        schema="core",
        type_="foreignkey",
    )
    op.drop_column("transactions", "import_batch_id", schema="core")
    op.drop_column("transactions", "transaction_hash", schema="core")
    op.drop_table("imported_transactions", schema="raw")
    op.drop_table("data_quality_issues", schema="core")
    op.drop_table("import_batches", schema="core")
