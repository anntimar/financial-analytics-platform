import os
import uuid
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import engine
from app.repositories.analytics_repository import AnalyticsRepository

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "true",
        reason="Defina RUN_INTEGRATION_TESTS=true para executar testes PostgreSQL.",
    ),
]


def test_database_migrations_and_analytics_views() -> None:
    with engine.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
        schemas = set(
            connection.scalars(
                text(
                    """
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name IN ('raw', 'core', 'analytics')
                    """
                )
            )
        )
        views = set(
            connection.scalars(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.views
                    WHERE table_schema = 'analytics'
                    """
                )
            )
        )

    assert revision == "20260727_0006"
    assert schemas == {"raw", "core", "analytics"}
    assert views == {
        "monthly_financial_summary",
        "category_financial_summary",
        "overdue_summary",
    }


def test_budget_comparison_query_executes_on_postgresql() -> None:
    with Session(engine) as session:
        result = AnalyticsRepository(session).budget_comparison(
            uuid.uuid4(), date(2026, 1, 1), date(2026, 12, 31)
        )

    assert result == []
