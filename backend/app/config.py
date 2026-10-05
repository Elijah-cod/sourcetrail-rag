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

    # Cross-encoder reranker (FastEmbed / ONNX, ~80 MB, CPU).
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    # Below this reranker score (0..1) we treat the sources as irrelevant and skip the LLM.
    min_relevance: float = 0.01

    # LLM: any OpenAI-compatible chat API. Default: Groq's free tier.
    # Local alternative (Ollama): LLM_BASE_URL=http://localhost:11434/v1  LLM_MODEL=llama3.2
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = ""                      # set LLM_API_KEY in .env, never in code
    llm_model: str = "openai/gpt-oss-120b"
    # Reasoning models (GPT-OSS) "think" before answering. "low" keeps that short: citing
    # sources needs little thought, and it saves free-tier tokens. Set to "" for models
    # that don't support it (e.g. many Ollama models).
    llm_reasoning_effort: str = "low"
    llm_max_tokens: int = 1500                 # room for brief reasoning + a concise answer
    llm_timeout_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
