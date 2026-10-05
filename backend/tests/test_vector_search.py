from app.indexing import index_document
from app.ingest.models import ExtractedDocument, Section
from app.search import vector_search
from app.store import DEMO_WORKSPACE_ID


def add(db, embedder, workspace_id, title, text, year=None, page=None):
    doc = ExtractedDocument(title=title, source_type="pdf" if page else "md",
                            sections=[Section(text=text, page=page)], published_year=year)
    return index_document(db, embedder, workspace_id, doc)


def test_closest_chunk_comes_first(db, fake_embedder, workspace_id):
    add(db, fake_embedder, workspace_id, "Fruit", "Bananas and mangoes are tropical fruit.")
    add(db, fake_embedder, workspace_id, "Databases", "Postgres stores vectors with the pgvector extension.")
    add(db, fake_embedder, workspace_id, "Weather", "It rained heavily in Nairobi this week.")

    hits = vector_search(db, fake_embedder.embed_query("how does postgres store vectors"), [workspace_id])

    assert hits[0].document_title == "Databases"
    assert hits[0].chunk_id == "databases:c000"
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)          # best first


def test_other_workspaces_are_invisible(db, fake_embedder, workspace_id):
    stranger = db.execute("INSERT INTO workspaces DEFAULT VALUES RETURNING id").fetchone()[0]
    add(db, fake_embedder, stranger, "Secret plans", "Postgres vectors secret roadmap.")
    add(db, fake_embedder, workspace_id, "My notes", "Postgres vectors are useful.")

    hits = vector_search(db, fake_embedder.embed_query("postgres vectors"), [workspace_id])
    assert [h.document_title for h in hits] == ["My notes"]


def test_searches_own_workspace_plus_demo(db, fake_embedder, workspace_id):
    add(db, fake_embedder, DEMO_WORKSPACE_ID, "Demo doc", "Hybrid search with reciprocal rank fusion.")
    add(db, fake_embedder, workspace_id, "My doc", "Hybrid search with rerankers.")

    hits = vector_search(db, fake_embedder.embed_query("hybrid search"), [workspace_id, DEMO_WORKSPACE_ID])
    # The real demo collection may already hold documents (e.g. ones you indexed by hand),
    # so check that both of ours are found rather than that they are the only results.
    assert {"Demo doc", "My doc"} <= {h.document_title for h in hits}


def test_year_filter(db, fake_embedder, workspace_id):
    add(db, fake_embedder, workspace_id, "Report 2023", "Revenue grew strongly.", year=2023)
    add(db, fake_embedder, workspace_id, "Report 2024", "Revenue declined.", year=2024)

    hits = vector_search(db, fake_embedder.embed_query("revenue"), [workspace_id], year=2024)
    assert [h.document_title for h in hits] == ["Report 2024"]


def test_limit_and_citation_fields(db, fake_embedder, workspace_id):
    for i in range(5):
        add(db, fake_embedder, workspace_id, f"Annual report {i}", f"Page about revenue number {i}.", page=3)

    hits = vector_search(db, fake_embedder.embed_query("revenue"), [workspace_id], limit=2)
    assert len(hits) == 2
    assert hits[0].page == 3
    assert hits[0].source_type == "pdf"
    assert hits[0].chunk_id.endswith(":p3:c000")
