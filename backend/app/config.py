"""Application settings, read from environment variables (and a local .env file)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://sourcetrail:sourcetrail@localhost:5432/sourcetrail"

    # Embedding model (FastEmbed / ONNX, runs on CPU). Must match vector(384) in the schema.
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    model_cache_dir: str = ".cache/models"   # where downloaded models are kept


@lru_cache
def get_settings() -> Settings:
    return Settings()
