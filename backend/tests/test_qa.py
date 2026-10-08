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
