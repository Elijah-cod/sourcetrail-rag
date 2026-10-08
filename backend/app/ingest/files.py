"""Extract text + structure from uploaded files: PDF, DOCX, Markdown, TXT, CSV."""

import csv
import io
import re
from pathlib import PurePath

import docx
import docx.table
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
# ReportLab writes "(anonymous)", Word "Untitled", converters "unknown"; brackets are optional.
_JUNK_TITLE = re.compile(r"^[(\[]?\s*(untitled|anonymous|unknown|unspecified|none|null|no title|document\d*|title"
                         r"|presentation|slide \d+|microsoft word|powerpoint)\b"
                         r"|\.(docx?|pdf|pptx?|odt|rtf)$", re.IGNORECASE)


def _usable_title(title: str | None) -> str | None:
    title = (title or "").strip()
    return title if len(title) >= 3 and not _JUNK_TITLE.search(title) else None


def _first_line_title(text: str) -> str | None:
    """A short first line that reads like a title ("Aurora Quay Berth Plan"), not a sentence.
    Skipped when it's a Markdown heading: those were already considered (and possibly rejected
    as a section heading, like "SEC-001: ..." in a handbook)."""
    line = next((l.strip() for l in text.splitlines() if l.strip()), "")
    if line.startswith(("#", "-", "*")) or line.endswith((".", ",", ":", ";")):
        return None
    return _usable_title(line) if len(line) <= 100 and 2 <= len(line.split()) <= 12 else None


def _capitalise(heading: str) -> str:
    """'MONT RIVIÈRE UPPER-AIR STATION' -> 'Mont Rivière Upper-Air Station' (all-caps only)."""
    if heading != heading.upper():
        return heading
    return " ".join("-".join(part[:1] + part[1:].lower() for part in word.split("-")) for word in heading.split())


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

    # Metadata title if it's real, else the big heading on page 1, else a title-like first line,
    # else the file name.
    title = (_usable_title(layout.metadata_title) or _usable_title(layout.title)
             or _first_line_title(layout.pages[0] if layout.pages else "") or _stem(filename))
    return ExtractedDocument(title=title, source_type="pdf", sections=sections)


def _cell_texts(row) -> list[str]:
    """Cell texts of a table row. Merged cells come back once per grid column, so drop repeats."""
    texts: list[str] = []
    previous = None
    for cell in row.cells:
        if previous is not None and cell._tc is previous:
            continue
        previous = cell._tc
        texts.append(re.sub(r"\s+", " ", cell.text).strip())
    return texts


def _docx_table(table, number: int) -> str:
    """A Word table as text, one line per row: 'Table 2, row 1: Item: Lamp oil; Qty: 4'.
    With a header row, each value is labelled with its column like a CSV row; without one, cells
    are joined with ' | '."""
    rows = [_cell_texts(row) for row in table.rows]
    rows = [r for r in rows if any(r)]
    if not rows:
        return ""
    header = rows[0]
    has_header = (len(rows) > 1 and all(header) and len(set(header)) == len(header)
                  and not any(_NUMBERISH.match(h) for h in header))
    lines = []
    if has_header:
        lines.append(f"Table {number} columns: " + " | ".join(header))
        for index, row in enumerate(rows[1:], start=1):
            parts = [f"{name}: {value}" for name, value in zip(header, row) if value]
            parts += [value for value in row[len(header):] if value]
            lines.append(f"Table {number}, row {index}: " + "; ".join(parts))
    else:
        for index, row in enumerate(rows, start=1):
            lines.append(f"Table {number}, row {index}: " + " | ".join(value for value in row if value))
    return "\n".join(lines)


def _docx_header_footer_text(document) -> tuple[list[str], list[str]]:
    """Unique page header and footer texts across the document's sections."""
    headers: list[str] = []
    footers: list[str] = []
    for section in document.sections:
        for part, found in ((section.header, headers), (section.footer, footers)):
            if part.is_linked_to_previous:
                continue
            texts = [p.text.strip() for p in part.paragraphs if p.text.strip()]
            texts += [_docx_table(t, n) for n, t in enumerate(part.tables, start=1)]
            text = "\n".join(t for t in texts if t)
            if text and text not in found:
                found.append(text)
    return headers, footers


def extract_docx(filename: str, data: bytes) -> ExtractedDocument:
    """Body paragraphs and tables in document order, split at Heading/Title styles; then page
    headers and footers as their own labelled sections."""
    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:
        raise ExtractionError(f"Could not read DOCX '{filename}': {exc}") from exc

    sections: list[Section] = []
    heading: str | None = None
    buffer: list[str] = []
    tables = 0
    title_style: str | None = None     # the first paragraph in Word's "Title" style

    def flush() -> None:
        if buffer:
            sections.append(Section(text=clean_text("\n\n".join(buffer)), heading=heading))
            buffer.clear()

    for block in document.iter_inner_content():
        if isinstance(block, docx.table.Table):
            tables += 1
            flush()                # a table is its own section, so rows aren't cut mid-paragraph
            text = _docx_table(block, tables)
            if text:
                sections.append(Section(text=clean_text(text), heading=heading))
            continue
        text = block.text.strip()
        if not text:
            continue
        if block.style is not None and block.style.name.lower().startswith(("heading", "title")):
            flush()                # a new heading closes the previous section
            heading = text
            if title_style is None and block.style.name.lower().startswith("title"):
                title_style = text
        else:
            buffer.append(text)
    flush()

    headers, footers = _docx_header_footer_text(document)
    sections += [Section(text=clean_text(t), heading="Page header") for t in headers]
    sections += [Section(text=clean_text(t), heading="Page footer") for t in footers]

    title = _usable_title(document.core_properties.title) or _usable_title(title_style) or _stem(filename)
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


# Plain-text sectioning. A TXT file used to be one big section, so the chunker packed several
# unrelated rules ("if the beam fails..." / "if fuel runs low...") into one passage and the LLM
# blended them. Now: headings start sections, and a paragraph with a condition in it stands alone.
TXT_GROUP_CHARS = 600     # plain paragraphs under one heading are grouped up to this size
_TXT_UNDERLINE = re.compile(r"^\s*(=+|-+)\s*$")
_TXT_NUMBERED_HEADING = re.compile(r"^(\d+(\.\d+)*\.?|[IVX]+\.|section \d+|part \d+|chapter \d+)\s+\S", re.IGNORECASE)
_CONDITIONAL = re.compile(r"\b(if|when|whenever|unless|until|in case|in the event|otherwise|only after)\b", re.IGNORECASE)


def _txt_heading(line: str) -> str | None:
    """The heading text if this line, standing alone, reads like a heading."""
    text = line.strip().lstrip("#").strip()
    if not text or len(text) > 80 or len(text.split()) > 10:
        return None
    if text.endswith((".", ",", ";", "!", "?")) or not (text[0].isupper() or text[0].isdigit()):
        return None
    letters = [c for c in text if c.isalpha()]
    if letters and all(c.isupper() for c in letters) and len(letters) >= 3:
        return text.rstrip(":").strip()                   # "WARNINGS" / "SAFETY RULES:"
    if line.lstrip().startswith("#") or _TXT_NUMBERED_HEADING.match(text):
        return text.rstrip(":").strip()                   # "# Lamps" / "2. Fuel" / "Section 4 Storms"
    if text.endswith(":"):
        return None                                       # "Do the following:" introduces a list
    words = text.split()
    # "Lantern Care" / "Night watch duties": short, title-ish, no verb-y sentence punctuation.
    return text if len(words) <= 6 and sum(w[0].isupper() for w in words) * 2 >= len(words) else None


def split_txt(text: str) -> list[Section]:
    """Split plain text into sections at heading-like lines and around conditional paragraphs."""
    paragraphs = [p.strip("\n") for p in re.split(r"\n\s*\n", text) if p.strip()]
    sections: list[Section] = []
    heading: str | None = None
    group: list[str] = []

    def flush() -> None:
        if group:
            sections.append(Section(text=clean_text("\n\n".join(group)), heading=heading))
            group.clear()

    pending_intro: str | None = None      # "If the lamp fails:" belongs with the list after it
    for index, paragraph in enumerate(paragraphs):
        lines = paragraph.splitlines()
        is_last = index == len(paragraphs) - 1
        # A heading underlined with === or ---, or a lone heading-like line.
        if len(lines) >= 2 and _TXT_UNDERLINE.match(lines[1]) and _txt_heading(lines[0]) is not None:
            title, lines = lines[0].strip(), lines[2:]
        elif _txt_heading(lines[0]) is not None and (len(lines) > 1 and lines[0].strip().isupper()
                                                     or len(lines) == 1 and not is_last):
            title, lines = _txt_heading(lines[0]), lines[1:]
        else:
            title = None
        if title is not None:
            flush()
            if pending_intro:
                sections.append(Section(text=clean_text(pending_intro), heading=heading))
                pending_intro = None
            heading = title
        body = "\n".join(lines).strip()
        if not body:
            continue
        if pending_intro:
            body, pending_intro = f"{pending_intro}\n{body}", None
        if body.rstrip().endswith(":") and len(body) < 300:
            pending_intro = body                              # keep it with what follows
            continue
        if _CONDITIONAL.search(body):
            flush()                                           # a rule is its own passage
            sections.append(Section(text=clean_text(body), heading=heading))
            continue
        if group and sum(len(g) for g in group) + len(body) > TXT_GROUP_CHARS:
            flush()
        group.append(body)
    if pending_intro:
        group.append(pending_intro)
    flush()
    return sections


def extract_txt(filename: str, data: bytes) -> ExtractedDocument:
    text = _decode(data)
    sections = split_txt(text)
    # A heading on the file's very first line is its title ("MONT RIVIÈRE UPPER-AIR STATION").
    first_line = next((l.strip() for l in text.splitlines() if l.strip()), "")
    heading = sections[0].heading if sections else None
    title = _usable_title(_capitalise(heading)) if heading and heading == _txt_heading(first_line) else None
    return ExtractedDocument(title=title or _stem(filename), source_type="txt", sections=sections)


_TITLE_COLUMN = re.compile(r"^(title|name|subject|heading|topic)$", re.IGNORECASE)
MAX_HEADER_CHARS = 100
# Values that are data, never column names: numbers, money, percentages, dates.
_NUMBERISH = re.compile(r"^[-+(]?[$€£¥]?\s*\d[\d,. ]*%?\)?$")
_DATEISH = re.compile(r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}$")


def _shape(value: str) -> str:
    """'RG-X1' -> 'A-A9': letters/digits collapsed to their class, so 'RG-X1' and 'RG-X2' match."""
    return re.sub(r"[A-Z]+", "A", re.sub(r"[a-z]+", "a", re.sub(r"\d+", "9", value)))


def _looks_like_code(header: str, column_values: list[str]) -> bool:
    """A code like 'RG-X1' over a column of 'RG-X2', 'RG-X3': same shape and it contains a digit.
    Column names almost never look like that, so this alone means the first row is data."""
    values = [v for v in column_values if v]
    return bool(values) and any(c.isdigit() for c in header) and _shape(header) == _shape(values[0])


def _repeats_a_value(header: str, column_values: list[str]) -> bool:
    """Header 'Ready' over a status column of Ready/Overdue. Weak alone ('Name' could be a name)."""
    return any(v.lower() == header.lower() for v in column_values if v)


def validate_csv_header(filename: str, header: list[str], rows: list[list[str]]) -> None:
    """Refuse a CSV whose first row isn't a real header. Otherwise its first data row silently
    becomes the field names and every answer cites nonsense like 'North pier: East Lock'."""
    if not rows:
        raise ExtractionError(f"'{filename}' needs a header row and at least one data row.")
    names = [h.strip() for h in header]
    if any(not name for name in names):
        raise ExtractionError(f"'{filename}' has an empty column name in its header row "
                              f"(column {names.index('') + 1}). Every column needs a name.")
    seen: set[str] = set()
    for name in names:
        if name.lower() in seen:
            raise ExtractionError(f"'{filename}' has the column name '{name}' more than once.")
        seen.add(name.lower())
    for name in names:
        if len(name) > MAX_HEADER_CHARS:
            raise ExtractionError(f"'{filename}' has a column name longer than {MAX_HEADER_CHARS} "
                                  "characters, so its first row is probably data, not a header.")
        if _NUMBERISH.match(name) or _DATEISH.match(name):
            raise ExtractionError(f"'{filename}' has '{name}' as a column name. The first row looks "
                                  "like data: add a header row with a name for each column.")
    columns = [[row[i].strip() if i < len(row) else "" for row in rows] for i in range(len(names))]
    for name, values in zip(names, columns):
        if _looks_like_code(name, values):
            raise ExtractionError(f"'{filename}' has '{name}' as a column name, but it looks like the "
                                  "values below it. Add a header row with a name for each column.")
    repeated = [name for name, values in zip(names, columns) if _repeats_a_value(name, values)]
    if len(repeated) * 2 >= len(names):
        raise ExtractionError(f"'{filename}' doesn't seem to have a header row: these header cells also appear "
                              f"as values in their columns: {', '.join(repr(n) for n in repeated)}. "
                              "Add a header row with a name for each column.")


def extract_csv(filename: str, data: bytes) -> ExtractedDocument:
    """Each row becomes its own section, written as 'column: value; column: value'."""
    try:
        records = list(csv.reader(io.StringIO(_decode(data))))
    except csv.Error as exc:
        raise ExtractionError(f"Could not read CSV '{filename}': {exc}") from exc
    records = [r for r in records if any(cell.strip() for cell in r)]       # skip blank lines
    if not records:
        raise ExtractionError(f"'{filename}' has no header row.")
    header, rows = records[0], records[1:]
    # A trailing comma on every line makes an unnamed, empty last column: drop it, don't reject.
    while header and not header[-1].strip() and not any(len(r) >= len(header) and r[len(header) - 1].strip() for r in rows):
        header = header[:-1]
    validate_csv_header(filename, header, rows)

    names = [h.strip() for h in header]
    sections = []
    for number, row in enumerate(rows, start=1):
        cells = list(zip(names, (cell.strip() for cell in row)))
        parts = [f"{column}: {value}" for column, value in cells if value]
        if parts:
            # A "title"/"name" column labels the row, e.g. citations read "Row 19: Support Policy".
            label = next((v for c, v in cells if v and _TITLE_COLUMN.match(c)), None)
            sections.append(Section(text="; ".join(parts), row=number, heading=label))
    return ExtractedDocument(title=_stem(filename), source_type="csv", sections=sections)
