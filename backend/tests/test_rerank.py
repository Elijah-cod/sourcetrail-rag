from uuid import uuid4

import pytest

from app.config import get_settings
from app.indexing import index_document
from app.ingest.models import ExtractedDocument, Section
from app.rerank import passage_text, rerank, sigmoid
from app.retrieve import retrieve
from app.search import SearchHit


def hit(text, title="Doc", section=None, ranks=None):
    return SearchHit(chunk_id=text[:10], document_id=uuid4(), document_title=title, source_type="md",
                     source_uri=None, text=text, page=None, section=section, score=0.03,
                     ranks=ranks or {})


def test_rerank_reorders_and_keeps_top_k(fake_reranker):
    hits = [
        hit("Bananas are yellow.", ranks={"vector": 1}),
        hit("Install the package with pip install sourcetrail.", ranks={"vector": 2, "keyword": 1}),
        hit("Weather report for Tuesday.", ranks={"keyword": 2}),
    ]
    result = rerank(fake_reranker, "how do I install the package", hits, top_k=2)

    assert len(result) == 2
    assert result[0].text.startswith("Install")
    assert result[0].ranks == {"vector": 2, "keyword": 1, "rerank": 1}   # earlier ranks kept
    assert all(0.0 <= h.score <= 1.0 for h in result)
    assert result[0].score > result[1].score


def test_rerank_does_not_modify_input(fake_reranker):
    original = hit("Install guide", ranks={"vector": 1})
    rerank(fake_reranker, "install", [original])
    assert original.score == 0.03 and original.ranks == {"vector": 1}


def test_rerank_empty_list(fake_reranker):
    assert rerank(fake_reranker, "anything", []) == []


def test_ties_keep_previous_order(fake_reranker):
    hits = [hit("alpha one"), hit("alpha two"), hit("alpha three")]
    result = rerank(fake_reranker, "alpha", hits)
    assert [h.text for h in result] == ["alpha one", "alpha two", "alpha three"]


def test_passage_text_and_sigmoid():
    assert passage_text(hit("Body.", title="Guide", section="Install")) == "Guide — Install\n\nBody."
    assert sigmoid(0) == 0.5
    assert sigmoid(10) > 0.99 and sigmoid(-10) < 0.01


def test_retrieve_with_reranker_end_to_end(db, fake_embedder, fake_reranker, workspace_id):
    for title, text in [("Install", "Install the package with pip and run the setup command."),
                        ("Fruit", "Bananas and mangoes are fruit."),
                        ("Search", "Search the package index for packages.")]:
        index_document(db, fake_embedder, workspace_id,
                       ExtractedDocument(title=title, source_type="md", sections=[Section(text=text)]))

    hits = retrieve(db, fake_embedder, "how do I install the package", [workspace_id],
                    mode="hybrid_rerank", reranker=fake_reranker, top_k=2)
    assert len(hits) == 2
    assert hits[0].document_title == "Install"
    assert "rerank" in hits[0].ranks


def test_hybrid_rerank_requires_a_reranker(db, fake_embedder, workspace_id):
    with pytest.raises(ValueError, match="needs a reranker"):
        retrieve(db, fake_embedder, "q", [workspace_id], mode="hybrid_rerank")


# ---------- the real model (skipped if it can't be downloaded) ----------

@pytest.fixture(scope="module")
def real_reranker():
    try:
        from app.rerank import FastEmbedReranker

        s = get_settings()
        return FastEmbedReranker(s.reranker_model, s.model_cache_dir)
    except Exception as exc:
        pytest.skip(f"reranker model unavailable: {exc}")


def test_real_reranker_prefers_the_answer(real_reranker):
    question = "Why did revenue fall in 2024?"
    answer = "Revenue declined in 2024 because of lower demand."
    distractor = "Revenue grew 12 percent in 2023."
    hits = rerank(real_reranker, question, [hit(distractor), hit(answer)])
    assert hits[0].text == answer
