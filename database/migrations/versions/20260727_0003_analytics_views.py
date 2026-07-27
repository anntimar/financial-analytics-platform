"""Create financial analytics views."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260727_0003"
down_revision: str | None = "20260727_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE VIEW analytics.monthly_financial_summary AS
        SELECT
            company_id,
            DATE_TRUNC('month', competence_date)::DATE AS reference_month,
            SUM(
                CASE WHEN transaction_type = 'revenue' AND status = 'paid'
                THEN amount ELSE 0 END
            ) AS total_revenue,
            SUM(
                CASE WHEN transaction_type = 'expense' AND status = 'paid'
                THEN amount ELSE 0 END
            ) AS total_expense,
            SUM(
                CASE
                    WHEN transaction_type = 'revenue' AND status = 'paid' THEN amount
                    WHEN transaction_type = 'expense' AND status = 'paid' THEN -amount
                    ELSE 0
                END
            ) AS net_result
        FROM core.transactions
        WHERE status <> 'cancelled'
        GROUP BY company_id, DATE_TRUNC('month', competence_date)
        """
    )
    op.execute(
        """
        CREATE VIEW analytics.category_financial_summary AS
        SELECT
            transaction.company_id,
            transaction.category_id,
            category.name AS category_name,
            transaction.transaction_type,
            DATE_TRUNC('month', transaction.competence_date)::DATE AS reference_month,
            COUNT(transaction.id) AS transaction_count,
            SUM(transaction.amount) AS total_amount
        FROM core.transactions AS transaction
        JOIN core.categories AS category ON category.id = transaction.category_id
        WHERE transaction.status = 'paid'
        GROUP BY
            transaction.company_id,
            transaction.category_id,
            category.name,
            transaction.transaction_type,
            DATE_TRUNC('month', transaction.competence_date)
        """
    )
    op.execute(
        """
        CREATE VIEW analytics.overdue_summary AS
        SELECT
            company_id,
            DATE_TRUNC('month', competence_date)::DATE AS reference_month,
            COUNT(id) AS overdue_count,
            SUM(amount) AS overdue_amount,
            AVG(CURRENT_DATE - due_date) AS average_days_overdue
        FROM core.transactions
        WHERE transaction_type = 'revenue'
          AND status = 'overdue'
        GROUP BY company_id, DATE_TRUNC('month', competence_date)
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS analytics.overdue_summary")
    op.execute("DROP VIEW IF EXISTS analytics.category_financial_summary")
    op.execute("DROP VIEW IF EXISTS analytics.monthly_financial_summary")
