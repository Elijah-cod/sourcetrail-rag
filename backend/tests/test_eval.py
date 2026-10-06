"""Tests for the evaluation harness and the quality of the evaluation data itself."""

from pathlib import Path
from uuid import uuid4

import pytest

from app.chunking import chunk_document, slugify
from app.ingest import extract_file
from app.search import SearchHit
from app.seed_demo import DEMO_SOURCES, seed
from app.store import DEMO_WORKSPACE_ID
from eval.run_eval import (ModeResult, Question, evaluate, first_relevant_rank, is_relevant,
                           load_questions, normalize)

QUESTIONS = load_questions()


def hit(source, text):
    return SearchHit(chunk_id="x", document_id=uuid4(), document_title="T", source_type="md",
                     source_uri=source, text=text, page=None, section=None, score=0.5)


# ---------- the evaluation data ----------

def test_question_ids_are_unique_and_mix_answerable_and_not():
    assert len({q.id for q in QUESTIONS}) == len(QUESTIONS)
    assert sum(q.answerable for q in QUESTIONS) >= 30
    assert sum(not q.answerable for q in QUESTIONS) >= 5


@pytest.fixture(scope="module")
def corpus_chunks() -> dict[str, list[str]]:
    """Every demo file run through the real extractor + chunker (no database or model needed)."""
    chunks = {}
    for path in DEMO_SOURCES.iterdir():
        doc = extract_file(path.name, path.read_bytes())
        chunks[path.name] = [normalize(c.text) for c in chunk_document(doc, slugify(doc.title))]
    return chunks


@pytest.mark.parametrize("question", [q for q in QUESTIONS if q.answerable], ids=lambda q: q.id)
def test_every_expected_answer_exists_in_some_chunk(question, corpus_chunks):
    # A typo in questions.jsonl would silently make every mode look worse. Catch it here.
    found = [r for r in question.relevant
             if any(normalize(r["contains"]) in chunk for chunk in corpus_chunks.get(r["source"], []))]
    assert found, f"{question.id}: none of {question.relevant} appears in a chunk"


# ---------- the metrics ----------

def test_relevance_needs_right_source_and_phrase():
    q = Question("t", "q", [{"source": "a.md", "contains": "Forty By Default"}])
    assert is_relevant(hit("a.md", "it is forty\nby   default"), q)       # case/whitespace-insensitive
    assert not is_relevant(hit("b.md", "forty by default"), q)            # wrong source
    assert not is_relevant(hit("a.md", "sixteen by default"), q)          # wrong phrase


def test_rank_and_metrics():
    q = Question("t", "q", [{"source": "a.md", "contains": "answer"}])
    assert first_relevant_rank([hit("a.md", "no"), hit("a.md", "the answer")], q) == 2
    assert first_relevant_rank([hit("a.md", "no")], q) is None

    r = ModeResult("demo", ranks=[1, 2, None, 6], precision_at_5=[0.2, 0.2, 0.0, 0.0], seconds=[0.1] * 4)
    assert r.recall_at(1) == 0.25 and r.recall_at(5) == 0.5 and r.recall_at(10) == 0.75
    assert r.mrr == pytest.approx((1 + 0.5 + 1 / 6) / 4)
    assert r.precision5 == pytest.approx(0.1)


def test_seed_and_evaluate_end_to_end(db, fake_embedder, fake_reranker, tmp_path):
    (tmp_path / "guide.md").write_text("# Guide\n\nThe answer is forty-two.\n")
    loaded = seed(db, fake_embedder, sources=tmp_path)
    assert loaded == [("guide.md", 1)]
    # Re-seeding replaces rather than duplicates.
    seed(db, fake_embedder, sources=tmp_path)
    assert db.execute("SELECT count(*) FROM documents WHERE workspace_id = %s",
                      (DEMO_WORKSPACE_ID,)).fetchone()[0] == 1

    questions = [Question("q1", "what is the answer", [{"source": "guide.md", "contains": "forty-two"}]),
                 Question("u1", "zebras", [])]
    results, top_scores = evaluate(db, fake_embedder, fake_reranker, questions)
    assert [r.mode for r in results] == ["vector", "keyword", "hybrid", "hybrid_rerank"]
    assert all(r.recall_at(1) == 1.0 for r in results)
    assert len(top_scores["answerable"]) == 1 and len(top_scores["unanswerable"]) == 1
