"""Hybrid retrieval: run vector + keyword search, merge them with RRF, optionally rerank.

Try it from the terminal (shows vector, keyword and hybrid results):
    uv run python -m app.retrieve "your question"
"""

import sys
import time
from dataclasses import replace
from typing import Literal
from uuid import UUID

import psycopg

from app.embed import Embedder
from app.rerank import TOP_K, Reranker, rerank
from app.search import SearchHit, keyword_search, vector_search

Mode = Literal["vector", "keyword", "hybrid", "hybrid_rerank"]
MODES = ("vector", "keyword", "hybrid", "hybrid_rerank")

RRF_K = 60            # standard value from the original RRF paper (Cormack et al., 2009)
CANDIDATES = 20       # how many results to take from each search method
FUSED_LIMIT = 30      # how many fused results to keep (the reranker will narrow these down)


def rrf_fuse(ranked_lists: dict[str, list[SearchHit]], k: int = RRF_K,
             limit: int = FUSED_LIMIT) -> list[SearchHit]:
    """Reciprocal Rank Fusion.

    Each list votes for its chunks: the chunk at rank r gets 1 / (k + r) points.
    Points from all lists are added up. Only *positions* matter, never the raw scores,
    so lists with completely different score scales can be combined fairly.
    """
    fused: dict[tuple, SearchHit] = {}
    for method, hits in ranked_lists.items():
        for rank, hit in enumerate(hits, start=1):
            key = (hit.document_id, hit.chunk_id)        # chunk IDs are unique per document
            if key not in fused:
                fused[key] = replace(hit, score=0.0, ranks={})
            fused[key].score += 1.0 / (k + rank)
            fused[key].ranks[method] = rank

    ordered = sorted(
        fused.values(),
        # Highest RRF score first; ties go to the chunk with the best single rank,
        # then to chunk_id so the order is always the same.
        key=lambda h: (-h.score, min(h.ranks.values()), h.chunk_id),
    )
    return ordered[:limit]


def retrieve(conn: psycopg.Connection, embedder: Embedder, question: str, workspace_ids: list[UUID],
             mode: Mode = "hybrid_rerank", year: int | None = None, reranker: Reranker | None = None,
             candidates: int = CANDIDATES, limit: int = FUSED_LIMIT, top_k: int = TOP_K,
             timings: dict[str, float] | None = None) -> list[SearchHit]:
    """Find the chunks most likely to answer `question`.

    `mode` lets the evaluation compare methods, matching the diagram:
    vector only -> keyword only -> hybrid -> hybrid + reranker.
    Pass a dict as `timings` to receive how long each stage took (milliseconds).
    """
    if mode not in MODES:
        raise ValueError(f"Unknown retrieval mode: {mode!r}")
    if mode == "hybrid_rerank" and reranker is None:
        raise ValueError("mode 'hybrid_rerank' needs a reranker")

    timings = {} if timings is None else timings
    started = time.perf_counter()
    lists: dict[str, list[SearchHit]] = {}
    if mode in ("vector", "hybrid", "hybrid_rerank"):
        lists["vector"] = vector_search(conn, embedder.embed_query(question), workspace_ids,
                                        limit=candidates, year=year)
    if mode in ("keyword", "hybrid", "hybrid_rerank"):
        lists["keyword"] = keyword_search(conn, question, workspace_ids, limit=candidates, year=year)
    fused = rrf_fuse(lists, limit=limit)
    timings["search_ms"] = (time.perf_counter() - started) * 1000

    if mode == "hybrid_rerank":
        started = time.perf_counter()
        reranked = rerank(reranker, question, fused, top_k=top_k)
        timings["rerank_ms"] = (time.perf_counter() - started) * 1000
        return reranked
    return fused


def main() -> None:
    from app.config import get_settings
    from app.embed import get_embedder
    from app.rerank import get_reranker
    from app.store import DEMO_WORKSPACE_ID

    question = " ".join(sys.argv[1:]) or "How much did revenue grow?"
    embedder, reranker = get_embedder(), get_reranker()
    with psycopg.connect(get_settings().database_url, autocommit=True) as conn:
        results = {mode: retrieve(conn, embedder, question, [DEMO_WORKSPACE_ID], mode=mode,
                                  reranker=reranker, limit=5, top_k=5)
                   for mode in MODES}

    print(f"Question: {question}")
    for mode, hits in results.items():
        label = "rerank" if mode == "hybrid_rerank" else "rrf"
        print(f"\n== {mode} ==")
        if not hits:
            print("   (no results)")
        for i, hit in enumerate(hits, start=1):
            ranks = ", ".join(f"{m} #{r}" for m, r in hit.ranks.items())
            print(f"{i}. [{label} {hit.score:.4f}] {hit.chunk_id}  ({ranks})")
            print(f"   {hit.text[:110]!r}")

if __name__ == "__main__":
    main()
