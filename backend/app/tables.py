"""Whole-table questions: "What is the total number of units?", "Which assets are overdue?"

A sum, count or "list every..." over a CSV needs *every* row, but search returns the few rows
that look most like the question, and a total looks like no row in particular (each one scores
about 0.001). When an aggregate word is followed closely by one of a small CSV's column names (or
a word of its title), as in "total number of *units*" or "every *asset*", every chunk of that CSV
is handed to the LLM instead. "How many dimensions can a vector have if I index it" mentions the
column "index", but not right after "how many", so it's an ordinary question.
"""

import re
from uuid import UUID

import psycopg

from app.search import HIT_COLUMNS, SearchHit

MAX_TABLE_CHUNKS = 12          # ~60 short rows; bigger tables would crowd out everything else
WINDOW = 4                     # the column must come within this many words of the aggregate word

_AGGREGATE = re.compile(
    r"\b(total|sum|average|mean|median|how many|count|number of|all|every|each|overall|across|"
    r"highest|lowest|most|least|largest|smallest|rank|ranking|list)\b", re.IGNORECASE)


def wants_whole_table(question: str) -> bool:
    return bool(_AGGREGATE.search(question))


def _aggregated_words(question: str) -> set[str]:
    """The words right after each aggregate word: what is being totalled, counted or listed."""
    words: set[str] = set()
    for match in _AGGREGATE.finditer(question):
        following = re.findall(r"[a-z0-9]+", question[match.end():].lower())[:WINDOW]
        words |= {_stem(w) for w in following if len(w) >= 3}
    return words


def _stem(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def _words(text: str) -> set[str]:
    return {_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 3}


def column_names(chunk_text: str) -> list[str]:
    """'asset_id: TG-101; units: 48' -> ['asset_id', 'units'] (chunks store rows as column: value)."""
    return re.findall(r"(?:^|; |\n)([^:;\n]{1,60}): ", chunk_text)


def whole_table_hits(conn: psycopg.Connection, question: str, workspace_ids: list[UUID]) -> list[SearchHit]:
    """Every chunk of each small CSV the question is about, in row order; [] if none."""
    if not wants_whole_table(question):
        return []
    rows = conn.execute(f"""
        SELECT {HIT_COLUMNS}, 1.0 AS score
        FROM chunks c JOIN documents d ON d.id = c.document_id
        WHERE d.workspace_id = ANY(%(ws)s) AND d.source_type = 'csv'
          AND (SELECT count(*) FROM chunks x WHERE x.document_id = d.id) <= %(max)s
        ORDER BY d.id, c.ord
    """, {"ws": list(workspace_ids), "max": MAX_TABLE_CHUNKS}).fetchall()
    asked = _aggregated_words(question)
    by_doc: dict[UUID, list[SearchHit]] = {}
    for row in rows:
        hit = SearchHit(*row)
        by_doc.setdefault(hit.document_id, []).append(hit)
    chosen: list[SearchHit] = []
    for hits in by_doc.values():
        names = {name for h in hits[:1] for name in column_names(h.text)}
        vocabulary = _words(" ".join(names).replace("_", " ")) | _words(hits[0].document_title)
        if asked & vocabulary:
            for hit in hits:
                hit.ranks = {"table": 1}
            chosen += hits
    return chosen


# --- Computed summary -------------------------------------------------------------------------
# LLMs add badly: given all ten rows of the tidal grid CSV, the model reported 512 units instead
# of 464, and missed which Ready asset had the most units. So alongside the rows, the LLM gets
# totals, extremes and per-group figures computed here, and is told they are exact.

MAX_GROUPS = 8                 # a column with more distinct values (or more than one per two rows)
                               # isn't a category to group by
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_rows(hits: list[SearchHit]) -> list[dict[str, str]]:
    """The table's rows as {column: value}, from chunks in row order; [] if a row looks cut off."""
    columns = column_names(hits[0].text.split("\n", 1)[0]) if hits else []
    rows: list[dict[str, str]] = []
    for hit in hits:
        for line in hit.text.split("\n"):
            row: dict[str, str] = {}
            key = None
            for piece in line.split("; "):
                name, sep, value = piece.partition(": ")
                if sep and name in columns and name not in row:
                    key, row[name] = name, value.strip()
                elif key is not None:          # "; " inside a value
                    row[key] += "; " + piece
            if row:
                rows.append(row)
    if not columns or any(list(r) != columns for r in rows):
        return []
    return rows


def _number(value: str) -> float | None:
    value = value.replace(",", "").strip()
    return float(value) if _NUMBER.fullmatch(value) else None


def _fmt(x: float) -> str:
    return f"{x:,.0f}" if x == int(x) else f"{x:,.2f}".rstrip("0").rstrip(".")


def summarize(rows: list[dict[str, str]]) -> str:
    """Exact figures over every row: totals and extremes of numeric columns, earliest and latest
    dates, and counts and totals per value of each category column. '' if nothing to compute."""
    if len(rows) < 2:
        return ""
    columns = list(rows[0])
    label_col = columns[0]                     # rows are named by their first column (TG-203)
    label = lambda r: r[label_col]             # noqa: E731
    numeric = [c for c in columns[1:] if all(_number(r[c]) is not None for r in rows if r[c])
               and any(r[c] for r in rows)]
    dates = [c for c in columns[1:] if c not in numeric and all(_DATE.fullmatch(r[c]) for r in rows if r[c])
             and any(r[c] for r in rows)]
    groups = [c for c in columns[1:] if c not in numeric and c not in dates
              and 2 <= len({r[c] for r in rows}) <= min(MAX_GROUPS, len(rows) // 2)]
    lines: list[str] = []
    for c in numeric:
        with_value = [r for r in rows if r[c]]
        values = [_number(r[c]) for r in with_value]
        low = min(with_value, key=lambda r: _number(r[c]))
        high = max(with_value, key=lambda r: _number(r[c]))
        lines.append(f"{c}: total {_fmt(sum(values))} over {len(values)} rows "
                     f"({' + '.join(_fmt(v) for v in values)}); average {_fmt(sum(values) / len(values))}; "
                     f"lowest {low[c]} ({label(low)}); highest {high[c]} ({label(high)})")
    for c in dates:
        with_value = sorted((r for r in rows if r[c]), key=lambda r: r[c])
        lines.append(f"{c}: earliest {with_value[0][c]} ({label(with_value[0])}); "
                     f"latest {with_value[-1][c]} ({label(with_value[-1])}); "
                     f"in order: {', '.join(f'{label(r)} {r[c]}' for r in with_value)}")
    for g in groups:
        for value in dict.fromkeys(r[g] for r in rows):
            members = [r for r in rows if r[g] == value]
            parts = [f"{len(members)} row{'s' if len(members) > 1 else ''} ({', '.join(label(r) for r in members)})"]
            for c in numeric:
                with_value = [r for r in members if r[c]]
                if with_value:
                    high = max(with_value, key=lambda r: _number(r[c]))
                    parts.append(f"{c} total {_fmt(sum(_number(r[c]) for r in with_value))}, "
                                 f"highest {high[c]} ({label(high)})")
            lines.append(f"{g} = {value}: " + "; ".join(parts))
    return "\n".join(lines)


def summary_hit(hits: list[SearchHit]) -> SearchHit | None:
    """A source holding the computed summary of one table's chunks, or None."""
    parsed = parse_rows(hits)
    text = summarize(parsed)
    if not text:
        return None
    first, rows = hits[0], len(parsed)
    return SearchHit(
        chunk_id=f"{first.document_id}:summary", document_id=first.document_id,
        document_title=first.document_title, source_type=first.source_type, source_uri=first.source_uri,
        text=f"Exact figures computed by SourceTrail from all {rows} rows of this table "
             f"(use these numbers rather than adding up the rows yourself):\n{text}",
        page=None, section=f"Computed summary of all {rows} rows", score=1.0, ranks={"table": 1})


def with_summaries(table: list[SearchHit]) -> list[SearchHit]:
    """Each table's chunks followed by its computed summary."""
    out: list[SearchHit] = []
    by_doc: dict[UUID, list[SearchHit]] = {}
    for hit in table:
        by_doc.setdefault(hit.document_id, []).append(hit)
    for hits in by_doc.values():
        summary = summary_hit(hits)
        out += hits + ([summary] if summary else [])
    return out
