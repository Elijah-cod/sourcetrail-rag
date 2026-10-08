"""Computed table summaries: exact totals the LLM can quote instead of adding up rows itself."""

from uuid import uuid4

from app.search import SearchHit
from app.tables import parse_rows, summarize, with_summaries

ROWS = [
    "asset_id: TG-201; zone: North; units: 48; inspected: 2026-09-12; status: Ready; note: Stable; no change",
    "asset_id: TG-202; zone: East; units: 35; inspected: 2026-08-28; status: Overdue; note: Calibrate",
    "asset_id: TG-203; zone: North; units: 64; inspected: 2026-10-02; status: Ready; note: Reserve",
    "asset_id: TG-204; zone: East; units: 18; inspected: 2026-07-19; status: Overdue; note: Gasket",
]


def _hits(lines_per_chunk: list[list[str]]) -> list[SearchHit]:
    doc = uuid4()
    return [SearchHit(str(i), doc, "Tidal grid", "csv", "grid.csv", "\n".join(lines), None, f"Rows {i}", 1.0)
            for i, lines in enumerate(lines_per_chunk)]


def test_parse_rows_keeps_semicolons_inside_values():
    rows = parse_rows(_hits([ROWS[:2], ROWS[2:]]))
    assert len(rows) == 4
    assert rows[0]["note"] == "Stable; no change"
    assert rows[3]["units"] == "18"


def test_parse_rows_gives_up_on_a_cut_off_row():
    assert parse_rows(_hits([ROWS[:2], ["asset_id: TG-203; zone: North; units: 64"]])) == []


def test_summary_totals_extremes_and_groups():
    text = summarize(parse_rows(_hits([ROWS])))
    assert "units: total 165 over 4 rows (48 + 35 + 64 + 18)" in text
    assert "lowest 18 (TG-204); highest 64 (TG-203)" in text
    assert "inspected: earliest 2026-07-19 (TG-204); latest 2026-10-02 (TG-203)" in text
    assert "status = Ready: 2 rows (TG-201, TG-203); units total 112, highest 64 (TG-203)" in text
    assert "zone = East: 2 rows (TG-202, TG-204); units total 53" in text
    assert "note =" not in text            # every value differs: not a category


def test_with_summaries_appends_one_summary_per_table():
    hits = _hits([ROWS[:2], ROWS[2:]])
    out = with_summaries(hits)
    assert out[:2] == hits
    assert out[2].section == "Computed summary of all 4 rows"
    assert out[2].chunk_id.endswith(":summary") and "use these numbers" in out[2].text
