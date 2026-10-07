"""Extract text + structure from uploaded files: PDF, DOCX, Markdown, TXT, CSV."""

import csv
import io
import re
from pathlib import PurePath

import docx
from app.ingest.pdf_layout import read_pdf

from app.ingest.models import ExtractedDocument, ExtractionError, Section, clean_text, guess_year


def extract_file(filename: str, data: bytes) -> ExtractedDocument:
    """Pick the right extractor from the file extension and run it."""
    suffix = PurePath(filename).suffix.lower()
    extractors = {
        ".pdf": extract_pdf,
        ".docx": extract_docx,
        ".md": extract_markdown,
        ".markdown": extract_markdown,
        ".txt": extract_txt,
        ".csv": extract_csv,
    }
    extractor = extractors.get(suffix)
    if extractor is None:
        raise ExtractionError(f"Unsupported file type '{suffix or filename}'. Use PDF, DOCX, MD, TXT or CSV.")

    doc = extractor(filename, data)
    doc.sections = [s for s in doc.sections if s.text]   # drop empty sections
    if not doc.sections:
        raise ExtractionError(f"No text could be extracted from '{filename}'.")
    if doc.published_year is None:
        doc.published_year = guess_year(filename)
    return doc


def _stem(filename: str) -> str:
    """'annual_report-2024.pdf' -> 'annual report 2024' (fallback title).
    Browsers sometimes save files with '+' for spaces ('Writing+Skills.pdf'), so those go too."""
    stem = re.sub(r"\s*\(\d+\)$", "", PurePath(filename).stem)           # "report (8)" -> "report"
    return re.sub(r"\s+", " ", re.sub(r"[_+]+|(?<=\w)-(?=\w)|\s-\s", " ", stem)).strip() or filename


# Placeholder titles that programs write into PDF metadata: never a real title.
_JUNK_TITLE = re.compile(r"^(untitled|document\d*|title|presentation|slide \d+|microsoft word|powerpoint)\b"
                         r"|\.(docx?|pdf|pptx?|odt|rtf)$", re.IGNORECASE)


def _usable_title(title: str | None) -> str | None:
    title = (title or "").strip()
    return title if len(title) >= 3 and not _JUNK_TITLE.search(title) else None


def _decode(data: bytes) -> str:
    """Bytes -> str. Try UTF-8 first, fall back to Latin-1 (never fails)."""
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def extract_pdf(filename: str, data: bytes) -> ExtractedDocument:
    """One section per page, as Markdown that keeps the PDF's headings and lists (see pdf_layout)."""
    try:
        layout = read_pdf(data)
    except Exception as exc:  # the PDF parser raises many different error types
        raise ExtractionError(f"Could not read PDF '{filename}': {exc}") from exc

    sections = []
    heading = None      # the heading in force where each page starts (it carries over page breaks)
    for number, markdown in enumerate(layout.pages, start=1):
        sections.append(Section(text=clean_text(markdown), page=number, heading=heading))
        page_headings = re.findall(r"^#{1,6} (.+)$", markdown, flags=re.MULTILINE)
        heading = page_headings[-1] if page_headings else heading
    if not any(s.text for s in sections):
        raise ExtractionError(f"'{filename}' has no extractable text (scanned PDFs need OCR, which isn't supported yet).")

    # Metadata title if it's real, else the big heading on page 1, else the file name.
    title = _usable_title(layout.metadata_title) or _usable_title(layout.title) or _stem(filename)
    return ExtractedDocument(title=title, source_type="pdf", sections=sections)


def extract_docx(filename: str, data: bytes) -> ExtractedDocument:
    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:
        raise ExtractionError(f"Could not read DOCX '{filename}': {exc}") from exc

    sections: list[Section] = []
    heading: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            sections.append(Section(text=clean_text("\n\n".join(buffer)), heading=heading))
            buffer.clear()

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        if paragraph.style is not None and paragraph.style.name.lower().startswith(("heading", "title")):
            flush()                # a new heading closes the previous section
            heading = text
        else:
            buffer.append(text)
    flush()

    title = (document.core_properties.title or "").strip() or _stem(filename)
    return ExtractedDocument(title=title, source_type="docx", sections=sections)


_MD_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


def split_markdown(text: str) -> tuple[str | None, list[Section]]:
    """Split Markdown text into sections at headings. Returns (title, sections).

    Shared by Markdown files and web pages (which trafilatura turns into Markdown).
    """
    sections: list[Section] = []
    heading: str | None = None
    title: str | None = None
    buffer: list[str] = []
    in_code_block = False

    def flush() -> None:
        section_text = clean_text("\n".join(buffer))
        if section_text:
            sections.append(Section(text=section_text, heading=heading))
        buffer.clear()

    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block   # '#' inside code is not a heading
        match = None if in_code_block else _MD_HEADING.match(line)
        if match:
            flush()
            heading = match.group(2)
            if title is None and len(match.group(1)) == 1:
                title = heading          # first "# Heading" becomes the title
        else:
            buffer.append(line)
    flush()
    return title, sections


def extract_markdown(filename: str, data: bytes) -> ExtractedDocument:
    title, sections = split_markdown(_decode(data))
    return ExtractedDocument(title=title or _stem(filename), source_type="md", sections=sections)


def extract_txt(filename: str, data: bytes) -> ExtractedDocument:
    return ExtractedDocument(
        title=_stem(filename), source_type="txt", sections=[Section(text=clean_text(_decode(data)))]
    )


def extract_csv(filename: str, data: bytes) -> ExtractedDocument:
    """Each row becomes its own section, written as 'column: value; column: value'."""
    reader = csv.DictReader(io.StringIO(_decode(data)))
    if not reader.fieldnames:
        raise ExtractionError(f"'{filename}' has no header row.")

    sections = []
    for number, row in enumerate(reader, start=1):
        parts = [f"{column}: {value.strip()}" for column, value in row.items()
                 if column and value and value.strip()]
        if parts:
            sections.append(Section(text="; ".join(parts), row=number))
    return ExtractedDocument(title=_stem(filename), source_type="csv", sections=sections)
