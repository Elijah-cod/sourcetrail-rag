import pytest
from fastapi.testclient import TestClient

from app import deps
from app.embed import get_embedder
from app.indexing import index_document
from app.ingest import web
from app.ingest.models import ExtractedDocument, Section
from app.llm import get_llm
from app.main import app
from app.rerank import get_reranker
from app.store import DEMO_WORKSPACE_ID

REPORT_MD = b"# Annual Report\n\n## Revenue\n\nRevenue declined in 2024 because of lower demand.\n"


class FakeLLM:
    def complete(self, messages):
        return "Revenue declined because of lower demand [1]."


@pytest.fixture
def client(db, fake_embedder, fake_reranker):
    """A TestClient wired to the rolled-back test DB and fake models."""
    app.dependency_overrides[deps.get_conn] = lambda: db
    app.dependency_overrides[deps.get_usage_conn] = lambda: db
    app.dependency_overrides[get_embedder] = lambda: fake_embedder
    app.dependency_overrides[get_reranker] = lambda: fake_reranker
    app.dependency_overrides[get_llm] = lambda: FakeLLM()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def new_client():
    """A second browser: same app and overrides, but its own (empty) cookie jar."""
    return TestClient(app)


def upload(client, name="report.md", data=REPORT_MD):
    return client.post("/documents", files={"file": (name, data, "text/markdown")})


def test_upload_creates_workspace_cookie_and_document(client):
    response = upload(client)
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Annual Report" and body["chunk_count"] == 1
    assert deps.COOKIE_NAME in client.cookies

    docs = client.get("/documents").json()
    mine = [d for d in docs if not d["is_demo"]]
    assert [d["title"] for d in mine] == ["Annual Report"]


def test_second_upload_reuses_the_same_workspace(client):
    upload(client)
    first_cookie = client.cookies[deps.COOKIE_NAME]
    upload(client, name="notes.md", data=b"# Notes\n\nSome notes.")
    assert client.cookies[deps.COOKIE_NAME] == first_cookie
    assert len([d for d in client.get("/documents").json() if not d["is_demo"]]) == 2


def test_other_visitors_cannot_see_my_documents(client):
    upload(client)
    stranger = new_client()
    assert [d for d in stranger.get("/documents").json() if not d["is_demo"]] == []


def test_query_returns_cited_answer(client):
    document_id = upload(client).json()["document_id"]
    response = client.post("/query", json={"question": "Why did revenue decline?"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["answer"].endswith("[1].")
    citation = body["citations"][0]
    assert citation["document_id"] == document_id and citation["section"] == "Revenue"
    assert body["sources"][0]["ranks"]["rerank"] == 1

    # Source inspection: follow the citation to the exact chunk.
    chunk = client.get(f"/documents/{document_id}/chunks/{citation['chunk_id']}")
    assert chunk.status_code == 200
    assert "lower demand" in chunk.json()["text"]


def test_query_without_cookie_uses_demo_only_and_creates_no_workspace(client, db, fake_embedder):
    doc = ExtractedDocument(title="Demo Guide", source_type="md",
                            sections=[Section(text="Hybrid search combines vectors and keywords.")])
    index_document(db, fake_embedder, DEMO_WORKSPACE_ID, doc)
    before = db.execute("SELECT count(*) FROM workspaces").fetchone()[0]

    body = client.post("/query", json={"question": "What is hybrid search?"}).json()
    assert "Demo Guide" in {s["document_title"] for s in body["sources"]}
    assert db.execute("SELECT count(*) FROM workspaces").fetchone()[0] == before
    assert deps.COOKIE_NAME not in client.cookies


def test_bad_uploads(client):
    assert upload(client, name="photo.png", data=b"\x89PNG").status_code == 422
    assert upload(client, name="empty.txt", data=b"   ").status_code == 422


def test_too_large_upload(client, monkeypatch):
    monkeypatch.setattr(deps.get_settings(), "max_upload_mb", 0)   # any non-empty file is "too large"
    assert upload(client).status_code == 413


def test_add_url(client, monkeypatch):
    doc = ExtractedDocument(title="FastAPI Docs", source_type="url",
                            sections=[Section(text="FastAPI is a web framework.", heading="Intro")])
    monkeypatch.setattr("app.api.extract_url", lambda url: doc)
    response = client.post("/sources/url", json={"url": "https://example.com/docs"})
    assert response.status_code == 201 and response.json()["title"] == "FastAPI Docs"
    listed = [d for d in client.get("/documents").json() if not d["is_demo"]]
    assert listed[0]["source_uri"] == "https://example.com/docs"


def test_add_url_rejects_bad_input(client, monkeypatch):
    assert client.post("/sources/url", json={"url": "not a url"}).status_code == 422

    def refuse(url):
        raise web.ExtractionError("That URL points to a private or local address, which isn't allowed.")

    monkeypatch.setattr("app.api.extract_url", refuse)
    response = client.post("/sources/url", json={"url": "http://127.0.0.1/admin"})
    assert response.status_code == 422 and "private" in response.json()["detail"]


def test_delete_own_document_but_not_demo(client, db, fake_embedder):
    document_id = upload(client).json()["document_id"]
    assert client.delete(f"/documents/{document_id}").status_code == 204
    assert client.delete(f"/documents/{document_id}").status_code == 404     # already gone

    demo = index_document(db, fake_embedder, DEMO_WORKSPACE_ID,
                          ExtractedDocument(title="Demo", source_type="md", sections=[Section(text="x")]))
    assert client.delete(f"/documents/{demo.document_id}").status_code == 404


def test_cannot_inspect_another_visitors_chunks(client):
    document_id = upload(client).json()["document_id"]
    stranger = new_client()
    assert stranger.get(f"/documents/{document_id}/chunks/annual-report:c000").status_code == 404


def test_forged_cookies_are_not_trusted(client, db):
    # Pretending to own the demo workspace must not grant write access to it.
    forged = new_client()
    forged.cookies.set(deps.COOKIE_NAME, str(DEMO_WORKSPACE_ID))
    response = forged.post("/documents", files={"file": ("x.md", b"# Forged\n\nHello.", "text/markdown")})
    assert response.status_code == 201
    new_cookie = response.cookies[deps.COOKIE_NAME]                       # server issued a fresh one
    assert new_cookie != str(DEMO_WORKSPACE_ID)
    assert db.execute("SELECT count(*) FROM documents WHERE workspace_id = %s AND title = 'Forged'",
                      (DEMO_WORKSPACE_ID,)).fetchone()[0] == 0           # nothing landed in demo

    garbage = new_client()
    garbage.cookies.set(deps.COOKIE_NAME, "not-a-uuid")
    assert garbage.get("/documents").status_code == 200


def test_question_validation(client):
    assert client.post("/query", json={"question": ""}).status_code == 422
    assert client.post("/query", json={"question": "x" * 1001}).status_code == 422
    assert client.post("/query", json={"question": "ok", "mode": "magic"}).status_code == 422


# ---------- step 12: public-site protection ----------

def test_queries_are_rate_limited(client, monkeypatch):
    monkeypatch.setattr(deps.get_settings(), "queries_per_minute", 2)
    for _ in range(2):
        assert client.post("/query", json={"question": "hello"}).status_code == 200
    blocked = client.post("/query", json={"question": "hello"})
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1


def test_rate_limit_applies_even_without_cookies(client, monkeypatch):
    # A bot that drops cookies gets a new workspace each time, but the same IP key.
    monkeypatch.setattr(deps.get_settings(), "uploads_per_hour", 2)
    codes = [new_client().post("/documents", files={"file": ("a.md", b"# A\n\nText.", "text/markdown")}
                               ).status_code for _ in range(3)]
    assert codes == [201, 201, 429]


def test_failed_uploads_still_count(client, monkeypatch):
    monkeypatch.setattr(deps.get_settings(), "uploads_per_hour", 2)
    assert upload(client, name="junk.png", data=b"x").status_code == 422
    assert upload(client, name="junk.png", data=b"x").status_code == 422
    assert upload(client).status_code == 429


def test_document_cap_per_workspace(client, monkeypatch):
    monkeypatch.setattr(deps.get_settings(), "max_documents_per_workspace", 2)
    assert upload(client, name="a.md", data=b"# A\n\nOne.").status_code == 201
    assert upload(client, name="b.md", data=b"# B\n\nTwo.").status_code == 201
    full = upload(client, name="c.md", data=b"# C\n\nThree.")
    assert full.status_code == 413 and "Delete one" in full.json()["detail"]


def test_chunk_budget_per_workspace(client, monkeypatch):
    monkeypatch.setattr(deps.get_settings(), "max_chunks_per_workspace", 3)
    big = ("# Big\n\n" + "A sentence about limits. " * 400).encode()      # many chunks
    response = upload(client, name="big.md", data=big)
    assert response.status_code == 413 and "only has room for 3" in response.json()["detail"]
    assert [d for d in client.get("/documents").json() if not d["is_demo"]] == []   # nothing saved


def test_daily_llm_cap_falls_back_to_sources(client, monkeypatch):
    upload(client)
    monkeypatch.setattr(deps.get_settings(), "llm_calls_per_day", 1)
    first = client.post("/query", json={"question": "Why did revenue decline?"}).json()
    second = client.post("/query", json={"question": "Why did revenue decline?"}).json()
    assert first["status"] == "answered"
    assert second["status"] == "llm_unavailable" and "daily" in second["answer"]
    assert second["sources"]                                     # still shows the passages


def test_query_reports_applied_filters(client):
    upload(client)
    assert client.post("/query", json={"question": "What happened in 2024?"}).json()["filters"] == {"year": 2024}
    assert client.post("/query", json={"question": "What happened?"}).json()["filters"] == {}
