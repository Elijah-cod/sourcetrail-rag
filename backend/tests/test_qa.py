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
