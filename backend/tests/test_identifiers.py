"""Identifier lookups: SEC-014-style codes are found exactly, lookalikes are dropped,
cross-references are followed, and a code no document contains is reported as absent.

The test handbook mimics a template-built document: every "Data Quality" section has the same
text, so only the identifier tells them apart — exactly where meaning-based search fails.
"""

from app.identifiers import boundary, find_identifiers, is_document_code, references
from app.indexing import index_document
from app.ingest.models import ExtractedDocument, Section
from app.qa import ask
from tests.test_qa import FakeLLM

BODY = "Pipelines should validate schema, completeness and ranges before data reaches consumers."


def add_handbook(db, embedder, workspace_id):
    sections = []
    for n, ref in [(4, 21), (14, 31), (24, 41), (34, 51), (117, 14)]:
        sections.append(Section(
            heading=f"SEC-{n:03d}: Data Quality",
            text=f"## SEC-{n:03d}: Data Quality\n\n{BODY}\n\nThe unique evaluation marker for this section is "
                 f"EVAL-{n * 37:05d}.\n\nCross-reference: SEC-{ref:03d}.",
            page=n))
    doc = ExtractedDocument(title="Handbook", source_type="pdf", sections=sections)
    index_document(db, embedder, workspace_id, doc)


def sources(result):
    return [h.section.split(":")[0] for h in result.sources]


# ---------- pure functions ----------

def test_identifiers_are_found_and_normalised():
    assert find_identifiers("what does sec-014 say about EVAL-00518, v2 and Q3?") == ["SEC-014", "EVAL-00518"]


def test_identifier_match_is_whole_word():
    pattern = boundary("SEC-014")
    assert pattern.search("Cross-reference: SEC-014.") and pattern.search("(sec-014)")
    assert not pattern.search("SEC-0140") and not pattern.search("SEC-014-A")


def test_only_dashed_codes_can_be_declared_absent():
    assert is_document_code("SEC-014") and is_document_code("CVE-2024-1234")
    assert not is_document_code("MP3") and not is_document_code("ISO27001")


# ---------- the pipeline ----------

def test_named_section_comes_first_and_lookalikes_are_dropped(db, fake_embedder, fake_reranker, workspace_id):
    add_handbook(db, fake_embedder, workspace_id)
    result = ask(db, fake_embedder, fake_reranker, FakeLLM("It validates data [1]."),
                 "What does SEC-014 say?", [workspace_id])
    # SEC-014 itself, then SEC-117 (which mentions it). SEC-004/024/034 have the same text: gone.
    assert sources(result) == ["SEC-014", "SEC-117"]


def test_marker_lookup_finds_its_section(db, fake_embedder, fake_reranker, workspace_id):
    add_handbook(db, fake_embedder, workspace_id)
    result = ask(db, fake_embedder, fake_reranker, FakeLLM("SEC-024 [1]."),
                 "Which section has the evaluation marker EVAL-00888?", [workspace_id])
    assert sources(result) == ["SEC-024"]


def test_cross_reference_is_followed(db, fake_embedder, fake_reranker, workspace_id):
    add_handbook(db, fake_embedder, workspace_id)
    llm = FakeLLM("SEC-117 cross-references SEC-014 [1], whose marker is EVAL-00518 [2].")
    result = ask(db, fake_embedder, fake_reranker, llm,
                 "What is the evaluation marker of the section that SEC-117 cross-references?", [workspace_id])
    assert sources(result)[:2] == ["SEC-117", "SEC-014"]
    assert "EVAL-00518" in llm.calls[0][1]["content"]          # the second hop reached the model


def test_missing_code_is_reported_as_absent_not_guessed(db, fake_embedder, fake_reranker, workspace_id):
    add_handbook(db, fake_embedder, workspace_id)
    llm = FakeLLM()
    result = ask(db, fake_embedder, fake_reranker, llm, "What does SEC-999 say?", [workspace_id])
    assert result.status == "not_found"
    assert result.answer == "None of the documents mention SEC-999."
    assert llm.calls == []                                      # no lookalike was passed off as SEC-999


def test_references_skip_the_passage_own_id(db, fake_embedder, fake_reranker, workspace_id):
    add_handbook(db, fake_embedder, workspace_id)
    result = ask(db, fake_embedder, fake_reranker, FakeLLM("x [1]."), "What does SEC-117 say?", [workspace_id])
    sec117 = next(h for h in result.sources if h.section.startswith("SEC-117"))
    assert references([sec117], exclude=["SEC-117"]) == ["EVAL-04329", "SEC-014"]
