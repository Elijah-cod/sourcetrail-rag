from app.indexing import index_document
from app.ingest.models import ExtractedDocument, Section
from app.search import keyword_search


def add(db, embedder, workspace_id, title, text, heading=None, year=None):
    doc = ExtractedDocument(title=title, source_type="md",
                            sections=[Section(text=text, heading=heading)], published_year=year)
    return index_document(db, embedder, workspace_id, doc)


def titles(hits):
    return [h.document_title for h in hits]


def test_finds_exact_codes_and_rare_terms(db, fake_embedder, workspace_id):
    add(db, fake_embedder, workspace_id, "Errors", "If you see error E1234 the database is offline.")
    add(db, fake_embedder, workspace_id, "Other", "Nothing to see here.")
    assert titles(keyword_search(db, "what does E1234 mean", [workspace_id])) == ["Errors"]


def test_stemming_matches_word_forms(db, fake_embedder, workspace_id):
    add(db, fake_embedder, workspace_id, "Report", "Revenue declined because demand fell.")
    # "decline" and "declined" share the stem "declin"
    assert titles(keyword_search(db, "Why did revenue decline in 2024?", [workspace_id])) == ["Report"]


def test_more_matching_words_rank_higher(db, fake_embedder, workspace_id):
    add(db, fake_embedder, workspace_id, "Partial", "Postgres is a database.")
    add(db, fake_embedder, workspace_id, "Full", "Postgres full-text search ranks matching documents.")
    hits = keyword_search(db, "postgres full-text search ranking", [workspace_id])
    assert titles(hits) == ["Full", "Partial"]
    assert hits[0].score > hits[1].score


def test_heading_matches_count_more(db, fake_embedder, workspace_id):
    add(db, fake_embedder, workspace_id, "Body only", "Notes mention installation once.", heading="Misc")
    add(db, fake_embedder, workspace_id, "Heading", "Notes mention installation once.", heading="Installation")
    assert titles(keyword_search(db, "installation", [workspace_id]))[0] == "Heading"


def test_stop_words_only_returns_nothing(db, fake_embedder, workspace_id):
    add(db, fake_embedder, workspace_id, "Doc", "Some text.")
    assert keyword_search(db, "what is it?", [workspace_id]) == []


def test_respects_workspace_and_year(db, fake_embedder, workspace_id):
    stranger = db.execute("INSERT INTO workspaces DEFAULT VALUES RETURNING id").fetchone()[0]
    add(db, fake_embedder, stranger, "Not mine", "Quarterly revenue figures.", year=2024)
    add(db, fake_embedder, workspace_id, "Mine 2023", "Quarterly revenue figures.", year=2023)
    add(db, fake_embedder, workspace_id, "Mine 2024", "Quarterly revenue figures.", year=2024)

    assert set(titles(keyword_search(db, "revenue", [workspace_id]))) == {"Mine 2023", "Mine 2024"}
    assert titles(keyword_search(db, "revenue", [workspace_id], year=2024)) == ["Mine 2024"]


def test_odd_characters_are_safe(db, fake_embedder, workspace_id):
    add(db, fake_embedder, workspace_id, "Doc", "Search syntax with quotes.")
    # Characters that mean something in tsquery syntax must not cause SQL errors.
    for text in ["'quotes' & | ! ( ) :*", "search)) OR 1=1; --", "<->"]:
        keyword_search(db, text, [workspace_id])
