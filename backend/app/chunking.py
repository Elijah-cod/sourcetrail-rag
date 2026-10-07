"""Cut extracted documents into small, overlapping chunks with stable IDs.

Why chunk at all? Search and the LLM both work best on short, focused passages.
A whole 80-page PDF can't be compared to a question; a 1,000-character piece can.
"""

import re
from dataclasses import dataclass

from app.ingest.models import ExtractedDocument

MAX_CHARS = 1000      # ~250 words: small enough to be focused, big enough to make sense alone
OVERLAP_CHARS = 150   # repeat the end of one chunk at the start of the next

# Where we prefer to cut, best first: paragraph, line, sentence, word.
SEPARATORS = ["\n\n", "\n", ". ", " "]


@dataclass
class Chunk:
    id: str               # stable ID, e.g. "annual-report-2024:p47:c003"
    ord: int              # position within the document (0, 1, 2, ...)
    text: str
    page: int | None = None
    section: str | None = None


def slugify(text: str, max_length: int = 60) -> str:
    """'Annual Report (2024).pdf' -> 'annual-report-2024-pdf'."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_length].rstrip("-") or "document"


def _split_into_units(text: str, max_chars: int, separators: list[str]) -> list[str]:
    """Break text into pieces no longer than max_chars, cutting at the nicest boundary available."""
    if len(text) <= max_chars:
        return [text]
    if not separators:
        # No boundary left (e.g. one enormous "word"): hard cut.
        return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]

    separator, finer = separators[0], separators[1:]
    parts = text.split(separator)
    if len(parts) == 1:                       # this separator doesn't occur; try a finer one
        return _split_into_units(text, max_chars, finer)

    units: list[str] = []
    for i, part in enumerate(parts):
        piece = part + separator if i < len(parts) - 1 else part   # keep the separator attached
        units.extend(_split_into_units(piece, max_chars, finer))
    return [u for u in units if u.strip()]


def _merge_units(units: list[str], max_chars: int, overlap_chars: int) -> list[str]:
    """Glue small units back together into chunks of up to max_chars, with overlap."""
    chunks: list[str] = []
    current: list[str] = []
    size = 0

    for unit in units:
        if current and size + len(unit) > max_chars:
            chunks.append("".join(current).strip())
            # Start the next chunk with the last few units of this one (the overlap).
            tail: list[str] = []
            tail_size = 0
            for previous in reversed(current):
                if tail_size + len(previous) > overlap_chars:
                    break
                tail.insert(0, previous)
                tail_size += len(previous)
            # Never let the overlap push the new chunk over the limit.
            while tail and tail_size + len(unit) > max_chars:
                tail_size -= len(tail.pop(0))
            current, size = tail, tail_size
        current.append(unit)
        size += len(unit)

    if current:
        chunks.append("".join(current).strip())
    return [c for c in chunks if c]


def split_text(text: str, max_chars: int = MAX_CHARS, overlap_chars: int = OVERLAP_CHARS) -> list[str]:
    """Split one block of text into overlapping chunks."""
    return _merge_units(_split_into_units(text, max_chars, SEPARATORS), max_chars, overlap_chars)


def chunk_document(doc: ExtractedDocument, slug: str, max_chars: int = MAX_CHARS,
                   overlap_chars: int = OVERLAP_CHARS) -> list[Chunk]:
    """Turn an ExtractedDocument into Chunks. CSV rows are grouped, never split."""
    pieces: list[tuple[str, int | None, str | None]] = []   # (text, page, section)

    if doc.source_type == "csv":
        group: list = []
        for section in doc.sections:
            group_size = sum(len(s.text) + 1 for s in group)
            if group and group_size + len(section.text) > max_chars:
                pieces.append(_csv_piece(group))
                group = []
            group.append(section)
        if group:
            pieces.append(_csv_piece(group))
    else:
        for section in doc.sections:
            cursor = 0
            for text in split_text(section.text, max_chars, overlap_chars):
                start = section.text.find(text[:80], cursor)
                cursor = max(start, cursor) + 1
                pieces.append((text, section.page, _heading_at(section.text, start, section.heading)))

    chunks = []
    for ord_, (text, page, section_name) in enumerate(pieces):
        location = f":p{page}" if page is not None else ""
        chunks.append(Chunk(id=f"{slug}{location}:c{ord_:03d}", ord=ord_, text=text,
                            page=page, section=section_name))
    return chunks


_HEADING_LINE = re.compile(r"^#{1,6} (.+)$", re.MULTILINE)


def _heading_at(text: str, position: int, default: str | None) -> str | None:
    """The heading a chunk falls under: the last Markdown heading at or before where it starts.
    (PDF pages are stored as Markdown, so a chunk on page 37 gets "3.6 Statelessness and state".)"""
    heading = default
    for match in _HEADING_LINE.finditer(text):
        if position < 0 or match.start() > position:
            break
        heading = match.group(1).strip()
    return heading


def _csv_piece(rows: list) -> tuple[str, None, str]:
    first, last = rows[0].row, rows[-1].row
    label = f"Row {first}" if first == last else f"Rows {first}–{last}"
    return "\n".join(r.text for r in rows), None, label
