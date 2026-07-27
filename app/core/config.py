from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FinAnalytics"
    app_env: Literal["development", "test", "production"] = "development"
    app_debug: bool = False
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    secret_key: str = "development-only-change-me-at-least-32-characters"
    access_token_expire_minutes: int = 60
    allowed_hosts: str = "localhost,127.0.0.1"
    database_url: str = (
        "postgresql+psycopg://finanalytics_user:change_me@localhost:5432/finanalytics"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://") and "+psycopg" not in value:
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
