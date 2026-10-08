"""Compound questions (regression report, 8 Oct 2026): every part gets a supporting passage."""

from app.facets import split_facets
from app.indexing import index_document
from app.ingest.models import ExtractedDocument, Section
from app.qa import gather_sources
from app.tables import wants_whole_table, whole_table_hits


def test_compound_question_is_split_into_its_parts():
    question = ("During a water conservation order, the Heron back-pump fails and an amber alert is raised "
                "while a barge is inside the lock chamber. What should the lock keeper do?")
    assert split_facets(question) == ["During a water conservation order", "the Heron back-pump fails",
                                      "an amber alert is raised", "a barge is inside the lock chamber"]


def test_two_requests_in_one_question():
    assert split_facets("What is the daily observation schedule, and what is on the opening checklist?") == [
        "What is the daily observation schedule", "what is on the opening checklist"]


def test_simple_questions_are_not_split():
    assert split_facets("How long is Heron Lock?") == []
    assert split_facets("It is Monday and the reserve is low?") == []       # "It is Monday": no topic


def canal(db, embedder, workspace_id):
    filler = [Section(text=f"The {w} rules cover routine {w} work on the towpath.", heading=w.title())
              for w in ("mowing", "painting", "fencing", "signage", "moorings", "licences", "training", "fees")]
    sections = [
        Section(text="During a conservation order, limit the lock to 12 cycles a day.", heading="Conservation"),
        *filler[:4],
        Section(text="If the back-pump fails, start the standby pump within 20 minutes.", heading="Pump failure"),
        *filler[4:],
        Section(text="An amber alert means stop all leisure lockings.", heading="Alert levels"),
    ]
    index_document(db, embedder, workspace_id, ExtractedDocument(title="Canal guide", source_type="md",
                                                                 sections=sections))


def test_every_part_of_a_compound_question_reaches_the_llm(db, fake_embedder, fake_reranker, workspace_id):
    canal(db, fake_embedder, workspace_id)
    found = gather_sources(db, fake_embedder, fake_reranker,
                           "During a conservation order, the back-pump fails and an amber alert is raised. "
                           "What should the keeper do?", [workspace_id], top_k=2)
    texts = " ".join(h.text for h in found.hits)
    assert "12 cycles" in texts and "standby pump" in texts and "amber alert" in texts
    assert found.final is None and found.uncovered == []


def test_unsupported_part_is_reported_as_uncovered(db, fake_embedder, fake_reranker, workspace_id):
    canal(db, fake_embedder, workspace_id)
    found = gather_sources(db, fake_embedder, fake_reranker,
                           "The back-pump fails, and what zebra giraffe quota applies?", [workspace_id],
                           min_relevance=0.6)
    assert "standby pump" in " ".join(h.text for h in found.hits)
    assert found.uncovered == ["what zebra giraffe quota applies"]


# ---------- whole-table questions ----------

def grid(db, embedder, workspace_id):
    rows = [("TG-101", "Buoy", "48"), ("TG-102", "Buoy", "52"), ("TG-201", "Sensor", "30"), ("TG-202", "Sensor", "36")]
    sections = [Section(text=f"asset_id: {a}; category: {c}; units: {u}", row=n) for n, (a, c, u) in enumerate(rows, 1)]
    index_document(db, embedder, workspace_id, ExtractedDocument(title="tidal grid", source_type="csv",
                                                                 sections=sections))


def test_total_over_a_csv_gets_every_row(db, fake_embedder, fake_reranker, workspace_id):
    grid(db, fake_embedder, workspace_id)
    found = gather_sources(db, fake_embedder, fake_reranker, "What is the total number of units?", [workspace_id])
    texts = " ".join(h.text for h in found.hits)
    assert found.final is None
    assert all(code in texts for code in ("TG-101", "TG-102", "TG-201", "TG-202"))


def test_column_name_far_from_the_aggregate_word_is_not_a_table_question(db, fake_embedder, workspace_id):
    grid(db, fake_embedder, workspace_id)
    assert wants_whole_table("How many dimensions can a vector have if I want units?")
    assert whole_table_hits(db, "How many dimensions can a vector have if I want units?", [workspace_id]) == []
    assert whole_table_hits(db, "List every asset in the North zone", [workspace_id])


def test_instructions_about_the_answer_are_not_searched_as_parts():
    """'Preserve accented characters' has nothing to find; searching it made the answer say the
    passages 'don't cover' it."""
    parts = split_facets("According to the Mont Rivière log, what are the inspection date and station code? "
                         "Preserve accented characters.")
    assert not any("accented" in p for p in parts)
    assert not any("arithmetic" in p for p in split_facets(
        "Calculate the total units and the units by zone. Show the arithmetic totals."))


def test_parts_that_only_say_what_kind_of_answer_are_not_searched():
    """'What exact ordered actions are required' has no topic; reported as uncovered, it made the
    answer decline a part it had answered."""
    assert split_facets("Lightning is detected during an Amber warning while the hangar door is open. "
                        "What exact ordered actions are required?") == [
        "Lightning is detected during an Amber warning", "the hangar door is open"]
    assert "how many units is that" not in split_facets("Which zone has the most units, and how many units is that?")


def test_earliest_and_fewest_ask_for_the_whole_table():
    from app.tables import _aggregated_words
    assert {"inspection", "unit"} <= _aggregated_words("Which asset has the earliest inspection date, and which "
                                                       "category has the fewest units?")
