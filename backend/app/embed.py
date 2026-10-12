"""Embeddings: turn text into vectors (lists of numbers) that capture meaning.

Texts with similar meaning get vectors that point in similar directions, so
"How do I install it?" lands close to "Installation steps", even with no shared words.
"""

from functools import lru_cache
from typing import Protocol

from app.config import cpu_threads, get_settings


class Embedder(Protocol):
    """Anything with these methods can be used as an embedder (real model or a test fake)."""

    dim: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class FastEmbedEmbedder:
    """bge-small-en-v1.5 via FastEmbed: small (~70 MB), CPU-only, 384 dimensions."""

    def __init__(self, model_name: str, dim: int, cache_dir: str, batch_size: int = 4):
        from fastembed import TextEmbedding   # imported here so tests don't need the model

        self.dim, self.batch_size = dim, batch_size
        # No memory arena: ONNX would otherwise keep its peak allocation for good (see config).
        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir, threads=cpu_threads(),
                                    enable_cpu_mem_arena=False)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # passage_embed = "these are passages to be searched"
        return [vector.tolist() for vector in self._model.passage_embed(texts, batch_size=self.batch_size)]

    def embed_query(self, text: str) -> list[float]:
        # query_embed = "this is a question"; bge models encode questions slightly differently
        return next(iter(self._model.query_embed(text))).tolist()


@lru_cache
def get_embedder() -> Embedder:
    """Load the model once (first call downloads it, later calls reuse it)."""
    settings = get_settings()
    return FastEmbedEmbedder(settings.embedding_model, settings.embedding_dim, settings.model_cache_dir,
                             settings.model_batch_size)
