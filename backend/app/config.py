"""Application settings, read from environment variables (and a local .env file)."""

import math
import os
from functools import lru_cache
from pathlib import Path

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
    # Chosen from eval/results.md: answerable questions scored >= 0.69, unanswerable <= 0.13,
    # so 0.3 sits in the gap with a margin on both sides.
    min_relevance: float = 0.3
    # Passages per model call. Memory grows with the batch: reranking 40 passages at 32 per
    # batch took the models to 1.3 GB, at 4 per batch to 0.4 GB (with ONNX's memory arena
    # off, see embed.py), at the same speed. Small batches fit a 512 MB server.
    model_batch_size: int = 4
    # CPU threads per model. 0 = the CPUs this container may actually use (see cpu_threads()).
    # ONNX otherwise starts one thread per CPU of the *host*: on a 1-vCPU Cloud Run instance
    # that is dozens of threads time-sharing one CPU, and reranking 30 passages took 5 s
    # instead of under 1 s (16 threads on one core measured 16x slower than 1).
    model_threads: int = 0

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

    # Uploads
    max_upload_mb: int = 10
    # Workspace cookie. Set COOKIE_SECURE=true in production (HTTPS only).
    cookie_secure: bool = False

    # ---- Public-site protection ----
    # Storage caps per visitor workspace
    max_documents_per_workspace: int = 10
    max_chunks_per_workspace: int = 2000
    # Rate limits per client (hashed IP address)
    queries_per_minute: int = 10
    uploads_per_hour: int = 20
    # Site-wide cap on LLM calls per 24 h, kept under Groq's free daily quota
    llm_calls_per_day: int = 800
    # Visitor workspaces are deleted this long after their last activity
    workspace_ttl_hours: int = 24
    cleanup_enabled: bool = True
    cleanup_interval_minutes: int = 60
    # Behind a proxy (Render), the real client IP is in X-Forwarded-For. Only trust that
    # header when a proxy you control adds it; otherwise anyone can fake it.
    trust_forwarded_for: bool = False

    # The Next.js static export (frontend/out). Served at "/" when the folder exists.
    frontend_dir: str = "../frontend/out"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def cpu_threads() -> int:
    """Threads for the models: MODEL_THREADS if set, else the container's CPU quota or CPU count."""
    configured = get_settings().model_threads
    if configured > 0:
        return configured
    available = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else (os.cpu_count() or 1)
    quota = _cgroup_cpu_quota()
    return max(1, min(available, quota) if quota else available)


def _cgroup_cpu_quota() -> int | None:
    """CPUs allowed by the container's cgroup (Docker --cpus, Kubernetes limits), if limited."""
    try:  # cgroup v2: "200000 100000" = 2 CPUs, "max 100000" = no limit
        quota, period = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        return None if quota == "max" else max(1, math.ceil(int(quota) / int(period)))
    except (OSError, ValueError):
        pass
    try:  # cgroup v1
        quota = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        period = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        return None if quota <= 0 else max(1, math.ceil(quota / period))
    except (OSError, ValueError):
        return None
