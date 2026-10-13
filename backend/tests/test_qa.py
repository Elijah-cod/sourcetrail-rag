from app.generate import NOT_FOUND
from app.indexing import index_document
from app.ingest.models import ExtractedDocument, Section
from app.llm import LLMUnavailable
from app.qa import ask


class FakeLLM:
    def __init__(self, reply="Revenue declined because of lower demand [1].", error=None):
        self.reply, self.error, self.calls = reply, error, []

    def complete(self, messages):
        self.calls.append(messages)
        if self.error:
            raise self.error
        return self.reply


def add_report(db, embedder, workspace_id):
    doc = ExtractedDocument(title="Annual Report", source_type="pdf", sections=[
        Section(text="Revenue declined in 2024 because of lower demand.", page=2),
        Section(text="The company opened a new office.", page=5),
    ])
    index_document(db, embedder, workspace_id, doc)


def test_answer_with_citation(db, fake_embedder, fake_reranker, workspace_id):
    add_report(db, fake_embedder, workspace_id)
    llm = FakeLLM()
    result = ask(db, fake_embedder, fake_reranker, llm, "Why did revenue decline?", [workspace_id])

    assert result.status == "answered"
    assert result.answer == "Revenue declined because of lower demand [1]."
    assert result.citations[0].chunk_id == "annual-report:p2:c000"
    assert result.citations[0].page == 2
    assert "Revenue declined in 2024" in llm.calls[0][1]["content"]     # the source was sent


def test_no_documents_means_no_llm_call(db, fake_embedder, fake_reranker, workspace_id):
    llm = FakeLLM()
    result = ask(db, fake_embedder, fake_reranker, llm, "Anything?", [workspace_id])
    assert result.status == "not_found" and result.answer == NOT_FOUND
    assert llm.calls == []


def test_irrelevant_sources_skip_the_llm(db, fake_embedder, fake_reranker, workspace_id):
    add_report(db, fake_embedder, workspace_id)
    llm = FakeLLM()
    # FakeReranker scores 0 shared words -> sigmoid(0) = 0.5, so use a strict threshold here.
    result = ask(db, fake_embedder, fake_reranker, llm, "zebras giraffes", [workspace_id], min_relevance=0.6)
    assert result.status == "not_found"
    assert llm.calls == []


def test_llm_failure_still_returns_sources(db, fake_embedder, fake_reranker, workspace_id):
    add_report(db, fake_embedder, workspace_id)
    llm = FakeLLM(error=LLMUnavailable("The LLM's free quota is used up for now."))
    result = ask(db, fake_embedder, fake_reranker, llm, "Why did revenue decline?", [workspace_id])
    assert result.status == "llm_unavailable"
    assert "quota" in result.answer
    assert result.sources and result.citations == []


def test_model_saying_not_found(db, fake_embedder, fake_reranker, workspace_id):
    add_report(db, fake_embedder, workspace_id)
    result = ask(db, fake_embedder, fake_reranker, FakeLLM(reply=NOT_FOUND), "Who is the CEO?", [workspace_id])
    assert result.status == "not_found"


def test_year_in_question_filters_documents(db, fake_embedder, fake_reranker, workspace_id):
    for year in (2023, 2024):
        index_document(db, fake_embedder, workspace_id, ExtractedDocument(
            title=f"Report {year}", source_type="pdf", published_year=year,
            sections=[Section(text=f"Revenue changed in {year} because of demand.", page=1)]))
    llm = FakeLLM()
    result = ask(db, fake_embedder, fake_reranker, llm, "Why did revenue change in 2024?", [workspace_id])
    assert result.filters == {"year": 2024}
    assert {s.document_title for s in result.sources} == {"Report 2024"}


def test_answer_claiming_a_gap_gets_one_targeted_search(db, fake_embedder, fake_reranker, workspace_id):
    """Regression report, 8 Oct 2026: 'not retrieved' was reported as 'not in the document'."""
    from app.qa import missing_parts
    sections = [Section(text="Close the upper paddles when the pump fails.", heading="Pump failure")]
    sections += [Section(text=f"Routine {w} notes for the {w} crew.", heading=w) for w in
                 ("mowing", "painting", "fencing", "signage", "licences", "training", "fees", "moorings")]
    sections.append(Section(text="Secure the barge with two lines fore and aft.", heading="Barge in chamber"))
    index_document(db, fake_embedder, workspace_id, ExtractedDocument(title="Guide", source_type="md",
                                                                     sections=sections))
    llm = FakeLLM()
    llm.reply = "Close the upper paddles [1]. The passages I was given don't cover securing the barge."
    replies = iter([llm.reply, "Close the upper paddles [1] and secure the barge with two lines [2]."])
    llm.complete = lambda messages: (llm.calls.append(messages), next(replies))[1]

    result = ask(db, fake_embedder, fake_reranker, llm, "What do I do when the pump fails?", [workspace_id],
                 top_k=1)
    assert missing_parts(llm.reply) == ["The passages I was given don't cover securing the barge."]
    assert len(llm.calls) == 2
    assert "two lines fore and aft" in llm.calls[1][1]["content"]       # the found passage was sent
    assert result.answer.endswith("secure the barge with two lines [2].")
    assert {c.section for c in result.citations} == {"Pump failure", "Barge in chamber"}


def test_no_second_call_when_the_answer_claims_no_gap(db, fake_embedder, fake_reranker, workspace_id):
    add_report(db, fake_embedder, workspace_id)
    llm = FakeLLM()
    ask(db, fake_embedder, fake_reranker, llm, "Why did revenue decline?", [workspace_id])
    assert len(llm.calls) == 1


def test_passage_pointing_back_brings_the_rule_it_points_to(db, fake_embedder, fake_reranker, workspace_id):
    """RFC 6761: '.localhost' authoritative servers handle names 'as described above for caching
    DNS servers'. The model needs that earlier rule, not another domain's."""
    from app.qa import gather_sources
    caching = ("Caching DNS servers SHOULD recognize localhost names as special and SHOULD NOT attempt to "
               "look up NS records for them. They generate an immediate positive response for address "
               "queries and an immediate negative response for other queries. ") * 4
    authoritative = "Authoritative DNS servers SHOULD recognize localhost names as special and handle them as described above for caching DNS servers."
    index_document(db, fake_embedder, workspace_id, ExtractedDocument(title="RFC", source_type="url", sections=[
        Section(text=caching + "\n\n" + authoritative, heading="6.3. Domain Name Reservation Considerations for localhost"),
        Section(text="Authoritative DNS servers SHOULD generate immediate negative responses for all such queries.",
                heading="6.4. Domain Name Reservation Considerations for invalid")]))
    found = gather_sources(db, fake_embedder, fake_reranker, "What do authoritative servers do with localhost "
                           "names as described above?", [workspace_id], top_k=1)
    texts = [h.text for h in found.hits]
    assert any("handle them as described above" in t for t in texts)
    pointer = next(i for i, t in enumerate(texts) if "handle them as described above" in t)
    assert pointer > 0 and "immediate positive response" in texts[pointer - 1]


def test_an_answer_that_only_declines_is_not_found(db, fake_embedder, fake_reranker, workspace_id):
    """'The passages I was given don't cover the price or the salaries.' is a refusal."""
    add_report(db, fake_embedder, workspace_id)
    llm = FakeLLM()
    llm.reply = "The passages I was given don’t cover the land price or the employee salaries."
    result = ask(db, fake_embedder, fake_reranker, llm, "Why did revenue decline?", [workspace_id])
    assert result.status == "not_found"
    assert "don't cover the land price" in result.answer


def test_curly_apostrophe_gap_is_still_searched():
    from app.qa import missing_parts
    assert missing_parts("Travel time: the passages don’t cover it.") == ["Travel time: the passages don’t cover it."]


def _tram(db, embedder, workspace_id):
    index_document(db, embedder, workspace_id, ExtractedDocument(title="Ridge", source_type="docx", sections=[
        Section(text="The tram Vesper leaves Lower Station at 05:55 and arrives after 47 minutes.",
                heading="Transit Schedule")]))


def test_gap_already_in_a_sent_source_gets_a_second_reading(db, fake_embedder, fake_reranker, workspace_id):
    """Live run, 8 Oct 2026: 'The passages you were given don't cover its travel time', with
    'arrives after 47 minutes' in the source the answer cited."""
    _tram(db, fake_embedder, workspace_id)
    llm = FakeLLM()
    replies = iter(["The Vesper leaves at 05:55 [1]. The passages I was given don't cover its travel time.",
                    "The Vesper leaves at 05:55 and the trip takes 47 minutes [1]."])
    llm.complete = lambda messages: (llm.calls.append(messages), next(replies))[1]
    result = ask(db, fake_embedder, fake_reranker, llm, "When does the Vesper tram leave, and how long is "
                 "the trip?", [workspace_id])
    assert len(llm.calls) == 2
    assert "earlier draft of this answer said" in llm.calls[1][1]["content"]
    assert "47 minutes" in result.answer and result.status == "answered"


def test_second_reading_that_still_finds_nothing_keeps_the_first_answer(db, fake_embedder, fake_reranker,
                                                                         workspace_id):
    _tram(db, fake_embedder, workspace_id)
    llm = FakeLLM("The Vesper leaves at 05:55 [1]. The passages I was given don't cover the fare.")
    result = ask(db, fake_embedder, fake_reranker, llm, "When does the Vesper tram leave, and what is the "
                 "fare?", [workspace_id])
    assert len(llm.calls) == 2
    assert result.answer.startswith("The Vesper leaves at 05:55 [1].")


def test_a_pure_decline_is_not_read_again(db, fake_embedder, fake_reranker, workspace_id):
    _tram(db, fake_embedder, workspace_id)
    llm = FakeLLM("The passages I was given don't cover the fare.")
    result = ask(db, fake_embedder, fake_reranker, llm, "What is the Vesper tram fare?", [workspace_id])
    assert len(llm.calls) == 1 and result.status == "not_found"


def test_figure_in_no_source_is_reported_with_the_answer(db, fake_embedder, fake_reranker, workspace_id):
    add_report(db, fake_embedder, workspace_id)
    llm = FakeLLM("Revenue declined by 37% in 2024 because of lower demand [1].")
    result = ask(db, fake_embedder, fake_reranker, llm, "Why did revenue decline?", [workspace_id])
    assert len(llm.calls) == 2                       # one correction was asked for
    assert result.unverified == ["37"]               # FakeLLM repeats itself, so it stays
    assert "2024" not in result.unverified


def test_progress_reports_each_stage_as_it_starts(db, fake_embedder, fake_reranker, workspace_id):
    add_report(db, fake_embedder, workspace_id)
    stages = []
    ask(db, fake_embedder, fake_reranker, FakeLLM(), "Why did revenue decline and where is the new office?",
        [workspace_id], progress=lambda stage, **details: stages.append((stage, details)))
    assert [s for s, _ in stages] == ["search", "parts", "parts", "write", "check"]
    assert [d for s, d in stages if s == "parts"] == [{"count": 2, "done": 1}, {"count": 2, "done": 2}]
    assert stages[3][1]["sources"] >= 1


def test_no_write_stage_when_nothing_is_found(db, fake_embedder, fake_reranker, workspace_id):
    stages = []
    ask(db, fake_embedder, fake_reranker, FakeLLM(), "Anything?", [workspace_id],
        progress=lambda stage, **details: stages.append(stage))
    assert stages == ["search"]


def test_a_part_answered_by_a_sent_passage_is_not_reported_uncovered():
    """'its travel time' scores nothing on its own; with the question's names it matches the
    passage already sent, so the answer isn't told that part has no passage."""
    from app.qa import _answered_by_sent
    from app.search import SearchHit

    class NameAware:
        def score(self, question, passages):
            return [5.0 if "Vesper" in question and "Vesper" in p else -5.0 for p in passages]

    sent = [SearchHit(chunk_id="c1", document_id=None, document_title="Field Manual", source_type="docx",
                      source_uri="m.docx", text="The tram Vesper reaches Summit Gate after 47 minutes.", page=None,
                      section="Transit Schedule", score=0.9)]
    question = "When does the Vesper depart, and what is its travel time?"
    assert _answered_by_sent(NameAware(), "its travel time", question, sent, 0.3)
    assert not _answered_by_sent(NameAware(), "its travel time", "what is its travel time?", sent, 0.3)


def test_every_part_keeps_its_source_when_a_table_is_added(db, fake_embedder, fake_reranker, workspace_id):
    """The live six-document question: its CSV part brought in the whole table, and trimming
    back to six sources dropped the other parts' passages, so the answer said they weren't covered."""
    from app.ingest import extract_file

    facts = {"Cedar Lantern": "The Cedar Lantern project keeps field samples for 17 days.",
             "Quartz Harbor": "Quartz Harbor locks an account after 7 failed login attempts.",
             "Silver Meridian": "The Silver Meridian relay window opens at 06:40 UTC.",
             "Moss Echo": "The Moss Echo beacon transmits on 144.725 MHz.",
             "Example Domains": "Example domains are maintained for documentation purposes."}
    for title, text in facts.items():
        index_document(db, fake_embedder, workspace_id,
                       ExtractedDocument(title=title, source_type="txt", sections=[Section(text=text)]))
    index_document(db, fake_embedder, workspace_id,
                   extract_file("source test.csv", b"call_sign,team,count\nBlue Heron,Team Juniper,42\nAmber Kite,Team Saffron,19\n"))
    llm = FakeLLM("Answer [1].")
    result = ask(db, fake_embedder, fake_reranker, llm,
                 "Using all six sources, answer: How long does the Cedar Lantern project keep field samples? "
                 "After how many failed login "
                 "attempts does Quartz Harbor lock an account? Which team and count belong to Blue Heron? When "
                 "does the Silver Meridian relay window open? What frequency does the Moss Echo beacon use? "
                 "Why are example domains maintained?", [workspace_id])
    assert {*facts, "source test"} <= {h.document_title for h in result.sources}
