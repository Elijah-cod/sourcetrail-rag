"""The full question-answering pipeline: retrieve -> check relevance -> generate -> cite.

Try it from the terminal (needs LLM_API_KEY in .env):
    uv run python -m app.qa "your question"
"""

import sys
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

import psycopg

from app.config import get_settings
from app.embed import Embedder
from app.generate import NOT_FOUND, Citation, generate_answer
from app.llm import LLMClient, LLMUnavailable
from app.rerank import Reranker
from app.retrieve import Mode, retrieve
from app.search import SearchHit

Status = Literal["answered", "not_found", "llm_unavailable"]


@dataclass
class Answer:
    status: Status
    answer: str
    citations: list[Citation] = field(default_factory=list)
    sources: list[SearchHit] = field(default_factory=list)   # everything we retrieved, cited or not


def ask(conn: psycopg.Connection, embedder: Embedder, reranker: Reranker | None, llm: LLMClient,
        question: str, workspace_ids: list[UUID], mode: Mode = "hybrid_rerank",
        min_relevance: float | None = None) -> Answer:
    hits = retrieve(conn, embedder, question, workspace_ids, mode=mode, reranker=reranker)

    # Don't spend an LLM call (and free quota) when nothing relevant was found.
    # Only reranker scores are 0..1 probabilities, so the threshold applies to that mode.
    threshold = get_settings().min_relevance if min_relevance is None else min_relevance
    if not hits or (mode == "hybrid_rerank" and hits[0].score < threshold):
        return Answer(status="not_found", answer=NOT_FOUND, sources=hits)

    try:
        text, citations = generate_answer(llm, question, hits)
    except LLMUnavailable as exc:
        # Still useful: show the sources we found, with a clear message.
        return Answer(status="llm_unavailable",
                      answer=f"{exc} Here are the most relevant passages I found.", sources=hits)

    status: Status = "not_found" if text.strip() == NOT_FOUND else "answered"
    return Answer(status=status, answer=text, citations=citations, sources=hits)


def main() -> None:
    from app.embed import get_embedder
    from app.llm import get_llm
    from app.rerank import get_reranker
    from app.store import DEMO_WORKSPACE_ID

    question = " ".join(sys.argv[1:]) or "Why did revenue decline in 2024?"
    with psycopg.connect(get_settings().database_url, autocommit=True) as conn:
        result = ask(conn, get_embedder(), get_reranker(), get_llm(), question, [DEMO_WORKSPACE_ID])

    print(f"Question: {question}\nStatus:   {result.status}\n\n{result.answer}\n")
    for c in result.citations:
        where = f"page {c.page}" if c.page else (c.section or "")
        print(f"[{c.n}] {c.document_title} {where}  ->  {c.chunk_id}")
        print(f"     {c.snippet[:120]!r}")


if __name__ == "__main__":
    main()
