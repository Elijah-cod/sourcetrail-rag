"""All SQL for documents and chunks lives here, so the rest of the app never writes SQL."""

from uuid import UUID

import psycopg

from app.chunking import Chunk
from app.ingest.models import ExtractedDocument

# The shared demo collection (created by migrations/001_init.sql).
DEMO_WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000001")


def to_pgvector(vector: list[float]) -> str:
    """Python list -> pgvector's text format '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{x:.7g}" for x in vector) + "]"


def unique_slug(conn: psycopg.Connection, workspace_id: UUID, base: str) -> str:
    """'report' -> 'report', or 'report-2', 'report-3'... if taken in this workspace."""
    rows = conn.execute(
        "SELECT slug FROM documents WHERE workspace_id = %s AND (slug = %s OR slug LIKE %s)",
        (workspace_id, base, f"{base}-%"),
    ).fetchall()
    taken = {row[0] for row in rows}
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def insert_document(conn: psycopg.Connection, workspace_id: UUID, slug: str,
                    doc: ExtractedDocument, source_uri: str | None) -> UUID:
    row = conn.execute(
        """
        INSERT INTO documents (workspace_id, slug, title, source_type, source_uri, published_year)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (workspace_id, slug, doc.title, doc.source_type, source_uri, doc.published_year),
    ).fetchone()
    return row[0]


def insert_chunks(conn: psycopg.Connection, document_id: UUID, chunks: list[Chunk],
                  embeddings: list[list[float]]) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO chunks (id, document_id, ord, text, page, section, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
            """,
            [
                (c.id, document_id, c.ord, c.text, c.page, c.section, to_pgvector(e))
                for c, e in zip(chunks, embeddings, strict=True)
            ],
        )


def delete_document(conn: psycopg.Connection, workspace_id: UUID, document_id: UUID) -> bool:
    """Delete a document (its chunks go too, via ON DELETE CASCADE). True if something was deleted."""
    cur = conn.execute(
        "DELETE FROM documents WHERE id = %s AND workspace_id = %s", (document_id, workspace_id)
    )
    return cur.rowcount > 0


# ---------- reading ----------

def list_documents(conn: psycopg.Connection, workspace_ids: list[UUID]) -> list[dict]:
    """Documents visible to a visitor (their own + demo), newest first, with chunk counts."""
    rows = conn.execute(
        """
        SELECT d.id, d.title, d.source_type, d.source_uri, d.published_year, d.created_at,
               d.workspace_id = %(demo)s AS is_demo,
               (SELECT count(*) FROM chunks c WHERE c.document_id = d.id) AS chunk_count
        FROM documents d
        WHERE d.workspace_id = ANY(%(workspaces)s)
        ORDER BY is_demo, d.created_at DESC
        """,
        {"demo": DEMO_WORKSPACE_ID, "workspaces": list(workspace_ids)},
    ).fetchall()
    keys = ("id", "title", "source_type", "source_uri", "published_year", "created_at",
            "is_demo", "chunk_count")
    return [dict(zip(keys, row)) for row in rows]


def get_chunk(conn: psycopg.Connection, workspace_ids: list[UUID], document_id: UUID,
              chunk_id: str) -> dict | None:
    """One chunk with its document's details, or None if missing / not visible to this visitor."""
    row = conn.execute(
        """
        SELECT c.id, c.document_id, d.title, d.source_type, d.source_uri, c.ord, c.page,
               c.section, c.text
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.document_id = %s AND c.id = %s AND d.workspace_id = ANY(%s)
        """,
        (document_id, chunk_id, list(workspace_ids)),
    ).fetchone()
    if row is None:
        return None
    keys = ("chunk_id", "document_id", "document_title", "source_type", "source_uri", "ord",
            "page", "section", "text")
    return dict(zip(keys, row))
