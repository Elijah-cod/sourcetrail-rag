"""Exact lookups for identifiers like SEC-014, EVAL-01850 or ISO-27001.

Why: meaning-based search is the wrong tool for codes. Two sections can have identical
text and differ only in their ID (SEC-004 and SEC-014 in a handbook built from templates),
so vector search and the reranker can't tell them apart — and Postgres full-text search
splits "SEC-014" into "sec" and "-014". When a question names an identifier, we look it up
literally instead:

- the passage that *defines* it (the ID is its heading) is the best source;
- passages that only *mention* it (e.g. "Cross-reference: SEC-014") come next;
- lookalike passages without the ID are dropped — they are noise, however similar;
- if no document contains the ID at all, we can say so for certain, which is different
  from "the search didn't find anything relevant".

`references()` supports one extra hop: "the section SEC-117 cross-references" -> SEC-014.
"""

import re
from uuid import UUID

import psycopg

from app.search import HIT_COLUMNS, SearchHit

# Letters, then a dash/underscore (optional), then a digit, then more letters/digits/dashes:
# SEC-014, EVAL-01850, RAG-LARGE-001, ISO27001, CVE-2024-1234. Needs 2+ letters, so "v2" or
# "Q3" don't count (versions and quarters aren't lookups).
_ID = re.compile(r"(?<![\w-])([A-Za-z]{2,}(?:[-_][A-Za-z]+)*[-_]?\d[\w-]*)(?![\w-])")

# Words that mean "follow the reference": "the section SEC-117 cross-references", "linked to"...
_FOLLOW = re.compile(r"\b(refer\w*|cross[- ]?ref\w*|link\w*|points? to|mention\w*|see also|related)\b", re.IGNORECASE)

MAX_MATCHES = 20
MAX_FOLLOWED = 2


def find_identifiers(text: str) -> list[str]:
    """Identifiers in a question, upper-cased, in order: "what does sec-014 say" -> ["SEC-014"]."""
    found: list[str] = []
    for match in _ID.finditer(text):
        ident = match.group(1).rstrip("-_").upper()
        if any(c.isdigit() for c in ident) and ident not in found:
            found.append(ident)
    return found


def is_document_code(ident: str) -> bool:
    """Codes like SEC-014 or CVE-2024-1234 (letters, a separator, digits) name one specific thing,
    so if no document contains one, it's safe to say so. Looser tokens like MP3 or ISO27001 are
    only used to boost matches, never to refuse."""
    return bool(re.match(r"^[A-Z]{2,}(?:[-_][A-Z]+)*[-_]\d", ident))


def wants_reference_followed(question: str) -> bool:
    return bool(_FOLLOW.search(question))


def boundary(ident: str) -> re.Pattern:
    """Whole-identifier match: SEC-014 must not match SEC-0140 or XSEC-014."""
    return re.compile(rf"(?<![\w-]){re.escape(ident)}(?!\w|-\w)", re.IGNORECASE)


def defines(hit: SearchHit, ident: str) -> bool:
    """True if this passage is *about* the identifier: it's in the section heading, or the
    passage opens with it ("## SEC-014: Data Quality", or "SEC-014: ..." in older plain-text PDFs)."""
    pattern = boundary(ident)
    first_line = hit.text.lstrip().split("\n", 1)[0].lstrip("# ")
    return bool(pattern.search(hit.section or "")) or bool(pattern.match(first_line))


def exact_matches(conn: psycopg.Connection, idents: list[str], workspace_ids: list[UUID]) -> list[SearchHit]:
    """Passages containing any of `idents`, defining passages first, in document order."""
    if not idents:
        return []
    # ILIKE narrows the rows quickly; the regex check below enforces whole-identifier matches.
    rows = conn.execute(
        f"""
        SELECT {HIT_COLUMNS}, 1.0 AS score
        FROM chunks c JOIN documents d ON d.id = c.document_id
        WHERE d.workspace_id = ANY(%(workspaces)s)
          AND (c.text ILIKE ANY(%(likes)s) OR c.section ILIKE ANY(%(likes)s))
        ORDER BY d.title, c.ord
        LIMIT 200
        """,
        {"workspaces": list(workspace_ids), "likes": [f"%{i}%" for i in idents]},
    ).fetchall()
    hits = [SearchHit(*row) for row in rows]
    hits = [h for h in hits if any(boundary(i).search(f"{h.section or ''}\n{h.text}") for i in idents)]
    defining = [h for h in hits if any(defines(h, i) for i in idents)]
    mentioning = [h for h in hits if h not in defining]
    for h in defining:
        h.ranks["exact"] = 1
    for h in mentioning:
        h.ranks["exact"] = 2
    return (defining + mentioning)[:MAX_MATCHES]


def references(hits: list[SearchHit], exclude: list[str]) -> list[str]:
    """Identifiers mentioned in these passages (in order) that aren't already being looked up,
    and aren't the passage's own ID. "Cross-reference: SEC-014." inside SEC-117 -> ["SEC-014"]."""
    found: list[str] = []
    for hit in hits:
        own = set(find_identifiers(hit.section or ""))
        for ident in find_identifiers(hit.text):
            if ident not in exclude and ident not in own and ident not in found:
                found.append(ident)
    return found
