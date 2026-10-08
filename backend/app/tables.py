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
