"""Search over stored chunks: vector (semantic) search and keyword (full-text) search.

To try searches from the terminal, see app/retrieve.py.
"""

from dataclasses import dataclass, field
from uuid import UUID

import psycopg

from app.store import to_pgvector


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
    # Filled in by fusion: this chunk's position in each list, e.g. {"vector": 1, "keyword": 4}
    ranks: dict[str, int] = field(default_factory=dict)


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


def keyword_search(conn: psycopg.Connection, query_text: str, workspace_ids: list[UUID],
                   limit: int = 20, year: int | None = None) -> list[SearchHit]:
    """The `limit` chunks that best match the question's words (Postgres full-text search).

    Catches what vectors miss: exact names, codes and rare terms like "E1234" or "pgvector".
    """
    sql = f"""
        WITH q AS (
            -- plainto_tsquery: lowercase, drop stop words ("why", "did", "in"), stem
            -- ("decline" -> "declin"), and join the words with AND (&).
            -- AND is too strict for questions (every word must appear), so swap & for OR (|):
            -- a chunk matching some words is found; one matching more words ranks higher.
            SELECT replace(plainto_tsquery('english', %(text)s)::text, ' & ', ' | ')::tsquery AS query
        )
        SELECT {HIT_COLUMNS},
               ts_rank_cd(c.tsv, q.query, 32) AS score   -- 32: squash the score into 0..1
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        CROSS JOIN q
        WHERE c.tsv @@ q.query                              -- "@@" = does the chunk match?
          AND d.workspace_id = ANY(%(workspaces)s)
          AND (%(year)s::int IS NULL OR d.published_year = %(year)s::int)
        ORDER BY score DESC, c.id                            -- c.id breaks ties consistently
        LIMIT %(limit)s
    """
    if not has_search_terms(conn, query_text):
        return []      # e.g. "what is it?" is all stop words: nothing to look for
    rows = conn.execute(sql, {"text": query_text, "workspaces": list(workspace_ids),
                              "year": year, "limit": limit}).fetchall()
    return [SearchHit(*row) for row in rows]


def has_search_terms(conn: psycopg.Connection, query_text: str) -> bool:
    """False when the text has no searchable words left after removing stop words."""
    row = conn.execute("SELECT plainto_tsquery('english', %s)::text <> ''", (query_text,)).fetchone()
    return bool(row[0])

