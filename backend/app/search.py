"""Search over stored chunks. This file: vector (semantic) search.

Run a quick search from the terminal:
    uv run python -m app.search "your question"
"""

import sys
from dataclasses import dataclass
from uuid import UUID

import psycopg

from app.store import DEMO_WORKSPACE_ID, to_pgvector


@dataclass
class SearchHit:
    """One search result: a chunk plus what we need to cite it."""

    chunk_id: str
    document_id: UUID
    document_title: str
    source_type: str
    source_uri: str | None
    text: str
    page: int | None
    section: str | None
    score: float          # higher = better; meaning depends on the search method


# Columns every search returns, in SearchHit order. "c" = chunks, "d" = documents.
HIT_COLUMNS = """
    c.id, c.document_id, d.title, d.source_type, d.source_uri, c.text, c.page, c.section
"""


def vector_search(conn: psycopg.Connection, query_vector: list[float], workspace_ids: list[UUID],
                  limit: int = 20, year: int | None = None) -> list[SearchHit]:
    """The `limit` chunks whose embeddings are closest to the question's embedding."""
    sql = f"""
        SELECT {HIT_COLUMNS},
               1 - (c.embedding <=> %(q)s::vector) AS score   -- cosine similarity, 1 = identical
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE d.workspace_id = ANY(%(workspaces)s)
          AND (%(year)s::int IS NULL OR d.published_year = %(year)s::int)
        ORDER BY c.embedding <=> %(q)s::vector                 -- smallest distance first
        LIMIT %(limit)s
    """
    params = {"q": to_pgvector(query_vector), "workspaces": list(workspace_ids),
              "year": year, "limit": limit}

    with conn.transaction():
        # The HNSW index finds *approximate* neighbours quickly by checking ef_search
        # candidates. Because we also filter by workspace, look at more candidates...
        conn.execute("SET LOCAL hnsw.ef_search = 100")
        # ...and (pgvector 0.8+) keep scanning until enough rows pass the filter.
        _try_setting(conn, "SET LOCAL hnsw.iterative_scan = relaxed_order")
        rows = conn.execute(sql, params).fetchall()
    return [SearchHit(*row) for row in rows]


def _try_setting(conn: psycopg.Connection, statement: str) -> None:
    """Apply a setting if this Postgres/pgvector version knows it; otherwise carry on."""
    try:
        with conn.transaction():      # a savepoint: a failure here doesn't abort the search
            conn.execute(statement)
    except psycopg.Error:
        pass


def main() -> None:
    from app.config import get_settings
    from app.embed import get_embedder

    question = " ".join(sys.argv[1:]) or "What happened to revenue in 2024?"
    with psycopg.connect(get_settings().database_url, autocommit=True) as conn:
        hits = vector_search(conn, get_embedder().embed_query(question), [DEMO_WORKSPACE_ID], limit=5)
    print(f"Question: {question}\n")
    for i, hit in enumerate(hits, start=1):
        print(f"{i}. [{hit.score:.3f}] {hit.chunk_id}  ({hit.document_title})")
        print(f"   {hit.text[:120]!r}")


if __name__ == "__main__":
    main()
