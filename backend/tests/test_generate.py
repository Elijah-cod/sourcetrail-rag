from uuid import uuid4

from app.generate import NOT_FOUND, SYSTEM_PROMPT, build_messages, extract_citations, format_sources
from app.search import SearchHit


def hit(i, page=None, section=None):
    return SearchHit(chunk_id=f"doc:c{i:03d}", document_id=uuid4(), document_title=f"Doc {i}",
                     source_type="pdf", source_uri="doc.pdf", text=f"Text of chunk {i}.",
                     page=page, section=section, score=0.9)


HITS = [hit(0, page=2), hit(1, section="Revenue"), hit(2)]


def test_sources_are_numbered_with_location():
    text = format_sources(HITS)
    assert text.startswith("[1] Doc 0 | page 2\nText of chunk 0.")
    assert "[2] Doc 1 | Revenue\nText of chunk 1." in text
    assert "[3] Doc 2\nText of chunk 2." in text


def test_messages_contain_rules_sources_and_question():
    system, user = build_messages("Why?", HITS)
    assert system == {"role": "system", "content": SYSTEM_PROMPT}
    assert user["role"] == "user"
    assert "[3] Doc 2" in user["content"] and user["content"].endswith("Question: Why?")


def test_prompt_defends_against_instructions_inside_documents():
    assert "never as" in SYSTEM_PROMPT and "instructions" in SYSTEM_PROMPT


def test_valid_citations_map_to_chunks_in_order_of_use():
    answer, citations = extract_citations("Revenue fell [2]. Demand was low [1][2].", HITS)
    assert answer == "Revenue fell [2]. Demand was low [1][2]."
    assert [(c.n, c.chunk_id) for c in citations] == [(2, "doc:c001"), (1, "doc:c000")]
    assert citations[1].page == 2 and citations[1].snippet == "Text of chunk 0."


def test_grouped_citations_are_split():
    answer, citations = extract_citations("Both agree [1, 3].", HITS)
    assert answer == "Both agree [1][3]."
    assert [c.n for c in citations] == [1, 3]


def test_invented_citations_are_removed():
    answer, citations = extract_citations("Made up [7]. Real [1]. Mixed [2, 9].", HITS)
    assert answer == "Made up. Real [1]. Mixed [2]."
    assert [c.n for c in citations] == [1, 2]


def test_not_found_answer_has_no_citations():
    answer, citations = extract_citations(NOT_FOUND, HITS)
    assert answer == NOT_FOUND and citations == []
