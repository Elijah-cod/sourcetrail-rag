from uuid import uuid4

import pytest

from app.indexing import index_document
from app.ingest.models import ExtractedDocument, Section
from app.retrieve import retrieve, rrf_fuse
from app.search import SearchHit

DOC = uuid4()


def hit(chunk_id: str, score: float = 0.5) -> SearchHit:
    return SearchHit(chunk_id=chunk_id, document_id=DOC, document_title="T", source_type="md",
                     source_uri=None, text=chunk_id, page=None, section=None, score=score)


# ---------- rrf_fuse: pure logic, no database needed ----------

def test_rrf_score_is_sum_of_reciprocal_ranks():
    fused = rrf_fuse({"vector": [hit("a")], "keyword": [hit("a")]}, k=60)
    assert fused[0].score == pytest.approx(1 / 61 + 1 / 61)
    assert fused[0].ranks == {"vector": 1, "keyword": 1}


def test_agreement_beats_a_single_first_place():
    # "a" is first in one list only; "b" is second in both lists.
    fused = rrf_fuse({"vector": [hit("a"), hit("b")], "keyword": [hit("c"), hit("b")]})
    assert fused[0].chunk_id == "b"                          # 2/62 > 1/61
    assert fused[0].ranks == {"vector": 2, "keyword": 2}


def test_raw_scores_are_ignored():
    # Huge keyword scores must not drown out vector results: only positions count.
    fused = rrf_fuse({"vector": [hit("v", score=0.7)], "keyword": [hit("k", score=999.0)]})
    assert fused[0].score == fused[1].score


def test_ties_break_deterministically():
    fused = rrf_fuse({"vector": [hit("v")], "keyword": [hit("k")]})
    assert [h.chunk_id for h in fused] == ["k", "v"]         # same score, same best rank -> by id


def test_limit_and_empty_lists():
    many = [hit(f"c{i:02d}") for i in range(50)]
    assert len(rrf_fuse({"vector": many}, limit=30)) == 30
    assert rrf_fuse({"vector": [], "keyword": []}) == []


def test_original_hits_are_not_modified():
    original = hit("a", score=0.9)
    rrf_fuse({"vector": [original]})
    assert original.score == 0.9 and original.ranks == {}


def test_same_chunk_id_in_different_documents_stays_separate():
    other = SearchHit(chunk_id="a", document_id=uuid4(), document_title="Other", source_type="md",
                      source_uri=None, text="a", page=None, section=None, score=0.5)
    assert len(rrf_fuse({"vector": [hit("a"), other]})) == 2


# ---------- retrieve: end to end against the database ----------

def add(db, embedder, workspace_id, title, text):
    doc = ExtractedDocument(title=title, source_type="md", sections=[Section(text=text)])
    index_document(db, embedder, workspace_id, doc)


def test_retrieve_modes(db, fake_embedder, workspace_id):
    add(db, fake_embedder, workspace_id, "Errors", "Error E1234 means the database is offline.")
    add(db, fake_embedder, workspace_id, "Search", "Hybrid search merges vector and keyword results.")
    question = "what does error E1234 mean"

    hybrid = retrieve(db, fake_embedder, question, [workspace_id], mode="hybrid")
    assert hybrid[0].document_title == "Errors"
    assert set(hybrid[0].ranks) == {"vector", "keyword"}        # found by both methods

    keyword_only = retrieve(db, fake_embedder, question, [workspace_id], mode="keyword")
    assert all(set(h.ranks) == {"keyword"} for h in keyword_only)

    vector_only = retrieve(db, fake_embedder, question, [workspace_id], mode="vector")
    assert all(set(h.ranks) == {"vector"} for h in vector_only)


def test_unknown_mode_is_rejected(db, fake_embedder, workspace_id):
    with pytest.raises(ValueError):
        retrieve(db, fake_embedder, "q", [workspace_id], mode="magic")
