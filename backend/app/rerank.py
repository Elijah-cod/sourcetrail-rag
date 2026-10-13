"""Cross-encoder reranking: read the question and each candidate together, score the fit.

Why a second pass? Vector search compares two vectors that were made *separately*
(question alone, chunk alone). A cross-encoder reads question + chunk *together*, so it
can notice that "Revenue declined in 2024" answers "why did sales drop last year?" while
"Revenue grew in 2023" doesn't, even though both look similar. It's slower (one model run
per chunk), which is why we only use it on the 15 candidates RRF already picked.
"""

import math
from dataclasses import replace
from functools import lru_cache
from typing import Protocol

from app.config import cpu_threads, get_settings
from app.search import SearchHit

TOP_K = 6   # chunks handed to the LLM


class Reranker(Protocol):
    def score(self, question: str, passages: list[str]) -> list[float]: ...


class FastEmbedReranker:
    """ms-marco-MiniLM-L-6-v2: trained on real search queries + passages that answer them."""

    def __init__(self, model_name: str, cache_dir: str, batch_size: int = 4):
        from fastembed.rerank.cross_encoder import TextCrossEncoder   # imported lazily (tests use fakes)

        self._model = TextCrossEncoder(model_name=model_name, cache_dir=cache_dir, threads=cpu_threads(),
                                        enable_cpu_mem_arena=False)
        self.batch_size = batch_size

    def score(self, question: str, passages: list[str]) -> list[float]:
        # Passages of similar length go through the model together: a batch is padded to its
        # longest passage, and mixing a 100-character row with a 1,000-character section made
        # reranking 30 passages 45% slower (1.16 s against 0.80 s on one CPU).
        order = sorted(range(len(passages)), key=lambda i: len(passages[i]))
        scores = self._model.rerank(question, [passages[i] for i in order], batch_size=self.batch_size)
        out = [0.0] * len(passages)
        for i, score in zip(order, scores, strict=True):
            out[i] = float(score)
        return out


@lru_cache
def get_reranker() -> Reranker:
    settings = get_settings()
    return FastEmbedReranker(settings.reranker_model, settings.model_cache_dir, settings.model_batch_size)


def passage_text(hit: SearchHit) -> str:
    """Same idea as the embedding text: give the model the title/section for context."""
    context = " — ".join(part for part in (hit.document_title, hit.section) if part)
    return f"{context}\n\n{hit.text}" if context else hit.text


def sigmoid(x: float) -> float:
    """Squash any number into 0..1. The model outputs raw scores (e.g. -9.3 or 7.1)."""
    return 1.0 / (1.0 + math.exp(-x))


def rerank(reranker: Reranker, question: str, hits: list[SearchHit], top_k: int = TOP_K) -> list[SearchHit]:
    """Re-order `hits` by the cross-encoder's judgement and keep the best `top_k`."""
    if not hits:
        return []
    raw_scores = reranker.score(question, [passage_text(h) for h in hits])

    rescored = [replace(hit, score=sigmoid(raw), ranks=dict(hit.ranks))
                for hit, raw in zip(hits, raw_scores, strict=True)]
    # Best score first; on a tie keep the earlier (RRF) order, since sorted() is stable.
    rescored.sort(key=lambda h: -h.score)
    for position, hit in enumerate(rescored, start=1):
        hit.ranks["rerank"] = position
    return rescored[:top_k]
