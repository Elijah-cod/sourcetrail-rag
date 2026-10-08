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
    assert text.startswith("[1] Document: Doc 0 | Page: 2\nText of chunk 0.")
    assert "[2] Document: Doc 1 | Section: Revenue\nText of chunk 1." in text
    assert "[3] Document: Doc 2\nText of chunk 2." in text


def test_messages_contain_rules_sources_and_question():
    system, user = build_messages("Why?", HITS)
    assert system == {"role": "system", "content": SYSTEM_PROMPT}
    assert user["role"] == "user"
    assert "[3] Document: Doc 2" in user["content"] and user["content"].endswith("Question: Why?")


def test_prompt_guards_against_misattribution_overreach_and_stale_versions():
    assert "Never attribute one source's content to another source's name" in SYSTEM_PROMPT
    assert "say how many you have" in SYSTEM_PROMPT
    assert "latest version or effective date as current" in SYSTEM_PROMPT


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


# ---------- regression report, 8 Oct 2026 ----------

from dataclasses import replace as _replace

from app.generate import dedupe_list_items, generate_answer
from app.llm import LLMUnavailable
from app.modality import mismatches, restore

RFC = [_replace(hit(0), text="Applications SHOULD recognise .quayside names. Libraries MUST NOT forward them."),
       _replace(hit(1), text="Applications SHOULD NOT treat .sample names specially.")]


class ScriptedLLM:
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def complete(self, messages):
        self.calls.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def test_prompt_preserves_requirement_words_and_separates_inference():
    assert "MUST NOT, SHOULD, SHOULD NOT" in SYSTEM_PROMPT
    assert "infer" in SYSTEM_PROMPT
    assert "Never say a document doesn't contain" in SYSTEM_PROMPT


def test_strengthened_should_is_detected_but_matching_words_are_not():
    found = mismatches("Applications must recognise .quayside names [1]. Libraries must not forward them [1].",
                       [h.text for h in RFC])
    assert [(m.said, m.source_says) for m in found] == [("must", "SHOULD")]


def test_weakened_must_is_detected():
    found = mismatches("Libraries should not forward them [1].", [RFC[0].text])
    assert [(m.said, m.source_says) for m in found] == [("should not", "MUST NOT")]


def test_llm_is_asked_once_to_restore_the_words():
    llm = ScriptedLLM("Applications must not treat .sample names specially [2].",
                      "Applications SHOULD NOT treat .sample names specially [2].")
    text, citations = generate_answer(llm, "How are .sample names treated?", RFC)
    assert text == "Applications SHOULD NOT treat .sample names specially [1]."
    assert len(llm.calls) == 2 and 'says "SHOULD NOT"' in llm.calls[1][-1]["content"]


def test_words_are_swapped_in_place_if_the_rewrite_fails():
    llm = ScriptedLLM("Applications must recognise them [1], and must not treat .sample names specially [2].",
                      LLMUnavailable("quota"))
    text, _ = generate_answer(llm, "q", RFC)
    assert text == "Applications SHOULD recognise them [1], and SHOULD NOT treat .sample names specially [2]."


def test_restore_leaves_correct_sentences_alone():
    answer = "Libraries must not forward them [1]."
    assert restore(answer, [RFC[0].text]) == answer


def test_uncovered_parts_are_named_in_the_prompt():
    content = build_messages("q", HITS, uncovered=["the barge is in the chamber"])[1]["content"]
    assert 'no passage about "the barge is in the chamber"' in content


def test_duplicate_list_items_are_dropped_before_rendering():
    answer = ("Overdue assets:\n- **TG-102** (Buoy) [1]\n- **TG-202** (Sensor) [1]\n"
              "- **TG-202** (Sensor) (duplicate entry removed) [1]\n- TG-301 [2]\n- TG-102 (Buoy) [1]")
    assert dedupe_list_items(answer) == "Overdue assets:\n- **TG-102** (Buoy) [1]\n- **TG-202** (Sensor) [1]\n- TG-301 [2]"


def test_items_sharing_a_code_but_saying_different_things_are_kept():
    answer = "- TG-202: cable chafed [1]\n- TG-202: inspection overdue [1]\n- (duplicate keys are rejected) [2]"
    assert dedupe_list_items(answer) == answer


def test_words_after_the_last_citation_are_checked_against_it():
    answer = "Applications must recognise .quayside names [1] and must cache them."
    assert restore(answer, [RFC[0].text]) == "Applications SHOULD recognise .quayside names [1] and SHOULD cache them."


def test_prompt_forbids_carrying_a_rule_to_another_item():
    assert "Never carry a rule written for one" in SYSTEM_PROMPT
