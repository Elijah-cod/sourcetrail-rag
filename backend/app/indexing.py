"""The ingestion pipeline's last mile: chunk -> embed -> store, all-or-nothing."""

from dataclasses import dataclass
from uuid import UUID

import psycopg

from app import store
from app.chunking import Chunk, chunk_document, slugify
from app.embed import Embedder
from app.ingest.models import ExtractedDocument


@dataclass
class IndexResult:
    document_id: UUID
    slug: str
    chunk_count: int


def text_for_embedding(doc: ExtractedDocument, chunk: Chunk) -> str:
    """What we feed the embedding model: the chunk plus its context.

    A chunk saying "It grew 12%" is vague alone; with "Annual Report 2024 — Revenue"
    in front, its vector knows what "it" is about.
    """
    context = " — ".join(part for part in (doc.title, chunk.section) if part)
    return f"{context}\n\n{chunk.text}" if context else chunk.text


def index_document(conn: psycopg.Connection, embedder: Embedder, workspace_id: UUID,
                   doc: ExtractedDocument, source_uri: str | None = None) -> IndexResult:
    with conn.transaction():   # everything below is saved together, or not at all
        slug = store.unique_slug(conn, workspace_id, slugify(doc.title))
        chunks = chunk_document(doc, slug)
        embeddings = embedder.embed_documents([text_for_embedding(doc, c) for c in chunks])
        document_id = store.insert_document(conn, workspace_id, slug, doc, source_uri)
        store.insert_chunks(conn, document_id, chunks, embeddings)
    return IndexResult(document_id=document_id, slug=slug, chunk_count=len(chunks))
