"""Shared data shapes for extraction: what every extractor returns."""

import re
from dataclasses import dataclass, field


class ExtractionError(ValueError):
    """The file could not be turned into text (unsupported, corrupt or empty)."""


@dataclass
class Section:
    """A piece of a document plus where it came from."""

    text: str
    page: int | None = None      # PDF page number (1-based)
    heading: str | None = None   # Markdown/DOCX heading the text sits under
    row: int | None = None       # CSV row number (1-based, header excluded)


@dataclass
class ExtractedDocument:
    title: str
    source_type: str             # pdf | docx | md | txt | csv | url
    sections: list[Section] = field(default_factory=list)
    published_year: int | None = None
    # How extraction went, e.g. {"extractor": "trafilatura", "retained_chars": 5120}. Not stored yet.
    diagnostics: dict = field(default_factory=dict)


_YEAR = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")


def guess_year(text: str) -> int | None:
    """Find a year like 2024 in a filename or title, e.g. 'annual-report-2024.pdf' -> 2024."""
    match = _YEAR.search(text)
    return int(match.group(1)) if match else None


def clean_text(text: str) -> str:
    """Normalise whitespace so every extractor hands back tidy text."""
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)        # trailing spaces at line ends
    text = re.sub(r"[ \t]{2,}", " ", text)         # runs of spaces/tabs
    text = re.sub(r"\n{3,}", "\n\n", text)         # 3+ blank lines -> one blank line
    return text.strip()
