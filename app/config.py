"""Application settings, read from environment variables (and a local .env file)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://sourcetrail:sourcetrail@localhost:5432/sourcetrail"


@lru_cache
def get_settings() -> Settings:
    return Settings()
