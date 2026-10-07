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


def test_citations_are_renumbered_in_order_of_first_use():
    # The model cited source 2 first, then source 1: the reader sees [1] then [2].
    answer, citations = extract_citations("Revenue fell [2]. Demand was low [1][2].", HITS)
    assert answer == "Revenue fell [1]. Demand was low [2][1]."
    assert [(c.n, c.chunk_id) for c in citations] == [(1, "doc:c001"), (2, "doc:c000")]
    assert citations[1].page == 2 and citations[1].snippet == "Text of chunk 0."


def test_only_citing_a_later_source_becomes_1():
    answer, citations = extract_citations("Only the third source helps [3].", HITS)
    assert answer == "Only the third source helps [1]."
    assert [(c.n, c.chunk_id) for c in citations] == [(1, "doc:c002")]


def test_grouped_citations_are_split_and_deduplicated():
    answer, citations = extract_citations("Both agree [1, 3]. Again [3, 3].", HITS)
    assert answer == "Both agree [1][2]. Again [2]."
    assert [(c.n, c.chunk_id) for c in citations] == [(1, "doc:c000"), (2, "doc:c002")]


def test_invented_citations_are_removed():
    answer, citations = extract_citations("Made up [7]. Real [1]. Mixed [2, 9].", HITS)
    assert answer == "Made up. Real [1]. Mixed [2]."
    assert [c.n for c in citations] == [1, 2]


def test_not_found_answer_has_no_citations():
    answer, citations = extract_citations(NOT_FOUND, HITS)
    assert answer == NOT_FOUND and citations == []


def test_gpt_oss_style_citations_are_understood():
    # Real output from openai/gpt-oss-120b: full-width brackets with line ranges.
    raw = "A user-agent sends requests 【1†L1-L4】 【2†L1-L4】. Browsers are one 【1†L1-L3】."
    answer, citations = extract_citations(raw, HITS)
    assert answer == "A user-agent sends requests [1][2]. Browsers are one [1]."
    assert [(c.n, c.chunk_id) for c in citations] == [(1, "doc:c000"), (2, "doc:c001")]


def test_full_width_and_dagger_variants():
    answer, citations = extract_citations("Proxies forward 【3】. Some change it [2†L5]. Both 【1, 2】.", HITS)
    assert answer == "Proxies forward [1]. Some change it [2]. Both [3][2]."
    assert [c.chunk_id for c in citations] == ["doc:c002", "doc:c001", "doc:c000"]


def test_unreadable_markers_are_dropped():
    answer, citations = extract_citations("Something 【source】 happened [1].", HITS)
    assert answer == "Something happened [1]." and len(citations) == 1


def test_repeated_neighbouring_citations_are_merged():
    # Two line ranges of the same source, back to back, used to show as [1][1].
    answer, citations = extract_citations("Proxies cache 【1†L1-L4】【1†L5-L9】. Both [2] [2][1].", HITS)
    assert answer == "Proxies cache [1]. Both [2][1]."
    assert [c.chunk_id for c in citations] == ["doc:c000", "doc:c001"]
