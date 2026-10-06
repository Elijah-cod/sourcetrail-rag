import pytest

from app.query import parse_query


@pytest.mark.parametrize("question, year", [
    ("Why did revenue decline in 2024?", 2024),
    ("What changed since 2019", 2019),
    ("Show me the FY2023 results", 2023),
    ("What happened during 1998?", 1998),
    ("Sales for the year 2025", 2025),
    ("IN 2024 WHAT HAPPENED", 2024),                       # case doesn't matter
    ("What happened in 2024? And again in 2024?", 2024),   # same year twice is still one year
])
def test_extracts_a_year_after_a_time_word(question, year):
    assert parse_query(question).year == year


@pytest.mark.parametrize("question", [
    "How can I index embeddings with more than 2000 dimensions?",   # a number, not a year
    "The server listens on port 2020",
    "2024 annual report highlights",            # no time word before it: missed, which is harmless
    "Compare revenue in 2023 and in 2024",      # two years: a comparison, not a filter
    "What is pgvector version 0.8.0?",
    "In 1850 the company was founded",          # outside the plausible range for documents
])
def test_no_year_filter(question):
    assert parse_query(question).year is None


def test_text_is_kept_and_filters_are_reported():
    parsed = parse_query("  Why did revenue decline in 2024?  ")
    assert parsed.text == "Why did revenue decline in 2024?"
    assert parsed.filters == {"year": 2024}
    assert parse_query("no year here").filters == {}
