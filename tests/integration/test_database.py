import os

import pytest
from sqlalchemy import text

from app.core.database import engine

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

    assert revision == "20260727_0004"
    assert schemas == {"raw", "core", "analytics"}
    assert views == {
        "monthly_financial_summary",
        "category_financial_summary",
        "overdue_summary",
    }
