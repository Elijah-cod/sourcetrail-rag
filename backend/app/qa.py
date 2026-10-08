"""The full question-answering pipeline: retrieve -> check relevance -> generate -> cite.

Try it from the terminal (needs LLM_API_KEY in .env):
    uv run python -m app.qa "your question"
"""

import sys
import time
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

import psycopg

from app.config import get_settings
from app.embed import Embedder
from app.generate import NOT_FOUND, Citation, generate_answer
from app.identifiers import (MAX_FOLLOWED, boundary, exact_matches, find_identifiers, is_document_code,
                             references, wants_reference_followed)
from app.llm import LLMClient, LLMUnavailable
from app.query import ParsedQuery, parse_query
from app.rerank import TOP_K, Reranker, rerank
from app.retrieve import Mode, retrieve
from app.search import SearchHit

Status = Literal["answered", "not_found", "llm_unavailable"]


@dataclass
class Answer:
    status: Status
    answer: str
    citations: list[Citation] = field(default_factory=list)
    sources: list[SearchHit] = field(default_factory=list)   # everything we retrieved, cited or not
    filters: dict = field(default_factory=dict)              # e.g. {"year": 2024} if one was applied
    timings: dict = field(default_factory=dict)              # milliseconds per stage


# After reranking, passages scoring far below the best one are noise, not support.
NOISE_FLOOR = 0.05      # reranker probability below which a passage is never useful
RELATIVE_CUTOFF = 0.2   # ...and anything under 20% of the best passage's score is dropped


@dataclass
class Sources:
    """What retrieval found for a question, before any LLM call."""

    hits: list[SearchHit]
    parsed: ParsedQuery
    timings: dict
    exact: list[SearchHit] = field(default_factory=list)
    final: Answer | None = None          # set when retrieval alone settles the answer


def gather_sources(conn: psycopg.Connection, embedder: Embedder, reranker: Reranker | None, question: str,
                   workspace_ids: list[UUID], mode: Mode = "hybrid_rerank", min_relevance: float | None = None,
                   top_k: int = TOP_K) -> Sources:
    """Retrieve the passages the LLM will be given (the eval scores this step on its own)."""
    parsed = parse_query(question)
    timings: dict[str, float] = {}
    hits = retrieve(conn, embedder, parsed.text, workspace_ids, mode=mode, reranker=reranker,
                    year=parsed.year, top_k=top_k, timings=timings)
    # Every mode hands the LLM at most top_k sources (only the reranker trimmed before).
    hits = hits[:top_k]
    if mode == "hybrid_rerank" and hits:
        best = hits[0].score
        hits = [h for i, h in enumerate(hits) if i == 0 or h.score >= max(NOISE_FLOOR, best * RELATIVE_CUTOFF)]

    # Identifiers (SEC-014, EVAL-01850...) are looked up exactly; see app/identifiers.py.
    idents = find_identifiers(question)
    exact: list[SearchHit] = []
    if idents:
        started = time.perf_counter()
        exact = exact_matches(conn, idents, workspace_ids)
        missing = [i for i in idents if not any(_mentions(h, i) for h in exact)]
        if missing and len(missing) == len(idents) and all(is_document_code(i) for i in idents):
            # Certain, not a search miss: no document contains this code at all.
            return Sources([], parsed, timings, final=Answer(
                status="not_found", answer=f"None of the documents mention {', '.join(missing)}.",
                filters=parsed.filters, timings=timings))
        if exact:
            hits = _prefer_exact(conn, reranker if mode == "hybrid_rerank" else None, parsed.text, question,
                                 idents, exact, hits, workspace_ids, top_k)
        timings["lookup_ms"] = (time.perf_counter() - started) * 1000

    # Don't spend an LLM call (and free quota) when nothing relevant was found.
    # Only reranker scores are 0..1 probabilities, so the threshold applies to that mode.
    # An exact identifier match is relevant by definition, whatever the reranker thinks.
    threshold = get_settings().min_relevance if min_relevance is None else min_relevance
    if not hits or (not exact and mode == "hybrid_rerank" and hits[0].score < threshold):
        return Sources(hits, parsed, timings, exact, final=Answer(
            status="not_found", answer=NOT_FOUND, sources=hits, filters=parsed.filters, timings=timings))
    return Sources(hits, parsed, timings, exact)


def ask(conn: psycopg.Connection, embedder: Embedder, reranker: Reranker | None, llm: LLMClient,
        question: str, workspace_ids: list[UUID], mode: Mode = "hybrid_rerank",
        min_relevance: float | None = None, top_k: int = TOP_K) -> Answer:
    found = gather_sources(conn, embedder, reranker, question, workspace_ids, mode, min_relevance, top_k)
    if found.final is not None:
        return found.final
    hits, parsed, timings = found.hits, found.parsed, found.timings

    started = time.perf_counter()
    try:
        text, citations = generate_answer(llm, question, hits)
        timings["generation_ms"] = (time.perf_counter() - started) * 1000
    except LLMUnavailable as exc:
        # Still useful: show the sources we found, with a clear message.
        return Answer(status="llm_unavailable", sources=hits, filters=parsed.filters, timings=timings,
                      answer=f"{exc} Here are the most relevant passages I found.")

    status: Status = "not_found" if text.strip() == NOT_FOUND else "answered"
    return Answer(status=status, answer=text, citations=citations, sources=hits,
                  filters=parsed.filters, timings=timings)


def _mentions(hit: SearchHit, ident: str) -> bool:
    return bool(boundary(ident).search(f"{hit.section or ''}\n{hit.text}"))


def _unique(hits: list[SearchHit]) -> list[SearchHit]:
    """Drop repeats of the same passage (copies can carry different scores), keeping the first."""
    seen: set[tuple] = set()
    out = []
    for h in hits:
        key = (h.document_id, h.chunk_id)
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out


def _prefer_exact(conn: psycopg.Connection, reranker: Reranker | None, query: str, question: str,
                  idents: list[str], exact: list[SearchHit], hits: list[SearchHit],
                  workspace_ids: list[UUID], top_k: int) -> list[SearchHit]:
    """Sources for a question that names identifiers:

    1. passages that define them (their heading), then passages that mention them;
    2. if the question asks to follow a reference ("the section SEC-117 cross-references"),
       the passages that define the referenced IDs;
    3. remaining slots: search results from *other* documents only. Other passages of the same
       document are the lookalikes (SEC-004 when asked about SEC-014) that caused wrong answers.
    """
    if reranker is not None:
        # Score them like any other source (for the relevance labels), but keep defining-first order.
        exact = rerank(reranker, query, exact, top_k=len(exact))
        exact.sort(key=lambda h: h.ranks["exact"])
    chosen = exact[:top_k]

    if wants_reference_followed(question):
        defining = [h for h in chosen if h.ranks["exact"] == 1]
        refs = references(defining, exclude=idents)
        followed = [h for h in exact_matches(conn, refs, workspace_ids) if h.ranks["exact"] == 1][:MAX_FOLLOWED]
        for h in followed:
            h.ranks["followed"] = 1
        # Put the followed passages right after the ones that pointed to them (no duplicates).
        chosen = _unique(defining + followed + chosen)[:top_k]

    exact_docs = {h.document_id for h in chosen}
    others = [h for h in hits if h.document_id not in exact_docs]
    return chosen + others[: max(0, top_k - len(chosen))]


def main() -> None:
    from app.embed import get_embedder
    from app.llm import get_llm
    from app.rerank import get_reranker
    from app.store import DEMO_WORKSPACE_ID

    question = " ".join(sys.argv[1:]) or "Why did revenue decline in 2024?"
    with psycopg.connect(get_settings().database_url, autocommit=True) as conn:
        result = ask(conn, get_embedder(), get_reranker(), get_llm(), question, [DEMO_WORKSPACE_ID])

    print(f"Question: {question}\nStatus:   {result.status}\nFilters:  {result.filters or 'none'}"
          f"\n\n{result.answer}\n")
    for c in result.citations:
        where = f"page {c.page}" if c.page else (c.section or "")
        print(f"[{c.n}] {c.document_title} {where}  ->  {c.chunk_id}")
        print(f"     {c.snippet[:120]!r}")


if __name__ == "__main__":
    main()
