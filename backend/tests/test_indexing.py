import pytest

from app import store
from app.chunking import Chunk
from app.indexing import index_document, text_for_embedding
from app.ingest.models import ExtractedDocument, Section


def make_doc(title="Search Guide", body="Hybrid search combines vectors and keywords. " * 60):
    return ExtractedDocument(title=title, source_type="md", sections=[Section(text=body, heading="Overview")])


def test_index_document_stores_document_and_chunks(db, fake_embedder, workspace_id):
    result = index_document(db, fake_embedder, workspace_id, make_doc(), source_uri="guide.md")

    assert result.slug == "search-guide"
    assert result.chunk_count > 1

    title, uri = db.execute("SELECT title, source_uri FROM documents WHERE id = %s",
                            (result.document_id,)).fetchone()
    assert (title, uri) == ("Search Guide", "guide.md")

    rows = db.execute(
        "SELECT id, section, vector_dims(embedding) FROM chunks WHERE document_id = %s ORDER BY ord",
        (result.document_id,),
    ).fetchall()
    assert len(rows) == result.chunk_count
    assert rows[0][0] == "search-guide:c000"
    assert all(section == "Overview" and dims == 384 for _, section, dims in rows)


def test_keyword_index_is_filled_automatically(db, fake_embedder, workspace_id):
    result = index_document(db, fake_embedder, workspace_id, make_doc())
    hits = db.execute(
        "SELECT count(*) FROM chunks WHERE document_id = %s AND tsv @@ websearch_to_tsquery('english', 'keyword')",
        (result.document_id,),
    ).fetchone()[0]
    assert hits == result.chunk_count      # "keywords" matches "keyword" (stemming)


def test_same_title_twice_gets_a_new_slug(db, fake_embedder, workspace_id):
    first = index_document(db, fake_embedder, workspace_id, make_doc())
    second = index_document(db, fake_embedder, workspace_id, make_doc())
    assert (first.slug, second.slug) == ("search-guide", "search-guide-2")


def test_two_workspaces_can_use_the_same_slug_and_chunk_ids(db, fake_embedder, workspace_id):
    other_workspace = db.execute("INSERT INTO workspaces DEFAULT VALUES RETURNING id").fetchone()[0]
    a = index_document(db, fake_embedder, workspace_id, make_doc(body="Short text."))
    b = index_document(db, fake_embedder, other_workspace, make_doc(body="Short text."))
    assert a.slug == b.slug == "search-guide"      # allowed thanks to migration 002


def test_failure_saves_nothing(db, workspace_id):
    class BrokenEmbedder:
        dim = 384

        def embed_documents(self, texts):
            raise RuntimeError("model crashed")

    with pytest.raises(RuntimeError):
        index_document(db, BrokenEmbedder(), workspace_id, make_doc())
    assert db.execute("SELECT count(*) FROM documents WHERE workspace_id = %s",
                      (workspace_id,)).fetchone()[0] == 0


def test_delete_document_removes_chunks_and_respects_workspace(db, fake_embedder, workspace_id):
    result = index_document(db, fake_embedder, workspace_id, make_doc())
    other_workspace = db.execute("INSERT INTO workspaces DEFAULT VALUES RETURNING id").fetchone()[0]

    assert store.delete_document(db, other_workspace, result.document_id) is False   # not yours
    assert store.delete_document(db, workspace_id, result.document_id) is True
    assert db.execute("SELECT count(*) FROM chunks WHERE document_id = %s",
                      (result.document_id,)).fetchone()[0] == 0


def test_text_for_embedding_adds_title_and_section():
    doc = make_doc(title="Annual Report 2024")
    chunk = Chunk(id="x:c000", ord=0, text="It grew 12%.", section="Revenue")
    assert text_for_embedding(doc, chunk) == "Annual Report 2024 — Revenue\n\nIt grew 12%."


def test_to_pgvector_format():
    assert store.to_pgvector([0.5, -1.0, 0.123456789]) == "[0.5,-1,0.1234568]"
