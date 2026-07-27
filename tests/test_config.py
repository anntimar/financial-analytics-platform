from app.core.config import Settings


def test_render_database_url_uses_psycopg_driver() -> None:
    settings = Settings(
        database_url="postgres://user:password@host/database",
        _env_file=None,
    )
    assert settings.database_url.startswith("postgresql+psycopg://")
