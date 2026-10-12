"""Rebuild a PDF's structure (headings, paragraphs, bullet lists) as light Markdown.

pypdf only gives us the words. pdfplumber also tells us each word's font size, font name and
position on the page, which is enough to see the structure a reader sees:

- text noticeably bigger than the body text (or a short line that's all bold) is a heading;
- lines starting with •, -, 1. etc. are list items;
- a bigger vertical gap than usual starts a new paragraph;
- text repeated at the top or bottom of most pages (page numbers, running titles) is
  clutter, so it's dropped.

The result for each page is Markdown such as:
    ## 3.6 Statelessness and state
    A stateless server keeps no per-client data between requests...
    - any instance can serve any request
"""

import io
import re
from collections import Counter
from dataclasses import dataclass

import pdfplumber

_BOLD_FONT = re.compile(r"bold|black|heavy|semibold|demi", re.IGNORECASE)
# "(cid:127)" is how the parser reports a symbol it can't name — in practice, a bullet.
# Symbols may touch the text ("•Item"); "-", "1." and "a)" need a space, so "1.5 percent" isn't a list.
_BULLET = re.compile(r"^(?:(?:[•▪◦●○■□➢►‣∙·]|\(cid:\d+\))\s*|(?:[*–-]|\(?\d{1,2}[.)]|\(?[a-z][.)])\s+)(?=\S)")
_UNKNOWN_GLYPH = re.compile(r"\(cid:\d+\)")
_ONLY_NUMBER = re.compile(r"^(?:page\s*)?\d+(?:\s*(?:of|/)\s*\d+)?$", re.IGNORECASE)
MARGIN = 0.08            # top and bottom 8% of the page: where headers and footers live


@dataclass
class Line:
    text: str
    size: float          # the font size most of the line is written in
    bold: bool           # most of the line is in a bold font
    top: float
    bottom: float
    x0: float


@dataclass
class PdfLayout:
    pages: list[str]                 # Markdown per page
    title: str | None                # the biggest heading on page 1, if there is one
    metadata_title: str | None       # what the PDF's own metadata says (often junk)


MAX_PAGES = 300     # reading a page costs CPU and memory; a visitor's file shouldn't tie up the server


def read_pdf(data: bytes) -> PdfLayout:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        if len(pdf.pages) > MAX_PAGES:
            raise ValueError(f"it has {len(pdf.pages)} pages; the limit is {MAX_PAGES}")
        metadata_title = (pdf.metadata or {}).get("Title")
        page_lines = [(_lines(page), page.height) for page in pdf.pages]

    page_lines = _drop_repeated_margins(page_lines)
    body = _body_size([line for lines in page_lines for line in lines])

    pages, headings = [], []
    for number, lines in enumerate(page_lines, start=1):
        markdown, page_headings = _to_markdown(lines, body)
        pages.append(markdown)
        headings += [(number, size, text) for size, text in page_headings]
    return PdfLayout(pages=pages, title=_title(headings), metadata_title=str(metadata_title).strip() if metadata_title else None)


def _title(headings: list[tuple[int, float, str]]) -> str | None:
    """The biggest heading on page 1 is the document's title only if no other heading in the
    document is as big. In a handbook where every section starts with a same-size heading
    ("SEC-001: Architecture", "SEC-002: Caching"...), the first one is a section, not a title."""
    first_page = [h for h in headings if h[0] == 1]
    if not first_page:
        return None
    _, size, text = max(first_page, key=lambda h: h[1])
    return text if sum(1 for h in headings if h[1] >= size) == 1 else None


# ---------- words -> lines ----------

def _lines(page) -> list[Line]:
    words = page.extract_words(extra_attrs=["size", "fontname"], use_text_flow=True, x_tolerance=1.5, y_tolerance=3)
    lines: list[list[dict]] = []
    for word in words:
        # Same line if it sits at (almost) the same height as the previous word.
        if lines and abs(word["top"] - lines[-1][-1]["top"]) <= max(2.0, word["size"] * 0.4):
            lines[-1].append(word)
        else:
            lines.append([word])
    return [_make_line(ws) for ws in lines]


def _make_line(words: list[dict]) -> Line:
    sizes = Counter()
    bold_chars = 0
    for w in words:
        sizes[round(w["size"] * 2) / 2] += len(w["text"])      # weight by characters
        if _BOLD_FONT.search(w.get("fontname", "")):
            bold_chars += len(w["text"])
    total = sum(len(w["text"]) for w in words)
    text = " ".join(w["text"] for w in words)
    if not _BULLET.match(text):
        text = _UNKNOWN_GLYPH.sub("", text).strip()        # stray unknown symbols mid-line
    return Line(text=text, size=sizes.most_common(1)[0][0],
                bold=bold_chars >= 0.6 * total, top=min(w["top"] for w in words),
                bottom=max(w["bottom"] for w in words), x0=min(w["x0"] for w in words))


def _drop_repeated_margins(page_lines: list[tuple[list[Line], float]]) -> list[list[Line]]:
    """Remove page numbers, and headers/footers that repeat on at least half of the pages."""
    def in_margin(line: Line, height: float) -> bool:
        return line.top < height * MARGIN or line.bottom > height * (1 - MARGIN)

    def key(text: str) -> str:            # "Chapter 3 — page 12" and "... page 13" look the same
        return re.sub(r"\d+", "#", text.lower()).strip()

    counts = Counter()
    for lines, height in page_lines:
        counts.update({key(line.text) for line in lines if in_margin(line, height)})
    repeated = {k for k, n in counts.items() if len(page_lines) >= 3 and n >= max(2, len(page_lines) / 2)}

    kept = []
    for lines, height in page_lines:
        kept.append([line for line in lines
                     if not (in_margin(line, height) and (key(line.text) in repeated or _ONLY_NUMBER.match(line.text)))])
    return kept


def _body_size(lines: list[Line]) -> float:
    """The font size most of the text is written in."""
    sizes = Counter()
    for line in lines:
        sizes[line.size] += len(line.text)
    return sizes.most_common(1)[0][0] if sizes else 10.0


# ---------- lines -> Markdown ----------

def _heading_level(line: Line, body: float) -> int | None:
    text = line.text.strip()
    if len(text) > 150 or not re.search(r"[A-Za-z]", text):
        return None
    # Size decides first, so "1. Service Availability" in big type is a heading, not a list item.
    if line.size >= body * 1.5:
        return 1
    if line.size >= body * 1.2:
        return 2
    short_and_bold = (line.bold and len(text) <= 100 and not text.endswith((".", ",", ";"))
                      and not _BULLET.match(text))
    if line.size >= body * 1.08 or short_and_bold:
        return 3
    return None


def _join(previous: str, nxt: str) -> str:
    """Join wrapped lines; undo hyphenation ("avail-" + "ability" -> "availability")."""
    if previous.endswith("-") and len(previous) > 1 and previous[-2].isalpha() and nxt[:1].islower():
        return previous[:-1] + nxt
    return f"{previous} {nxt}"


def _to_markdown(lines: list[Line], body: float) -> tuple[str, list[tuple[float, str]]]:
    blocks: list[tuple[str, str]] = []        # (kind, text): kind is "h1".."h3", "item" or "p"
    headings: list[tuple[float, str]] = []     # (font size, text)
    previous: Line | None = None
    item_x0 = 0.0

    for line in lines:
        text = line.text.strip()
        if not text:
            continue
        gap = line.top - previous.bottom if previous else 0.0
        new_paragraph = previous is None or gap > (previous.bottom - previous.top) * 0.5
        level = _heading_level(line, body)

        if level:
            kind = f"h{level}"
            if blocks and blocks[-1][0] == kind and not new_paragraph:      # a heading wrapped onto 2 lines
                blocks[-1] = (kind, f"{blocks[-1][1]} {text}")
                headings[-1] = (line.size, blocks[-1][1])
            else:
                blocks.append((kind, text))
                headings.append((line.size, text))
        elif bullet := _BULLET.match(text):
            marker = "" if bullet.group(0).startswith("(cid") else bullet.group(0).strip().strip("()").rstrip(".)")
            rest = text[bullet.end():]
            # "1." / "a." keep their number or letter; •, -, ▪ ... all become "- ".
            blocks.append(("item", f"{marker}. {rest}" if marker[:1].isalnum() else f"- {rest}"))
            item_x0 = line.x0
        elif blocks and blocks[-1][0] == "item" and line.x0 > item_x0 + 2 and gap < (previous.bottom - previous.top):
            blocks[-1] = ("item", _join(blocks[-1][1], text))           # an indented continuation of the item
        elif blocks and blocks[-1][0] == "p" and not new_paragraph:
            blocks[-1] = ("p", _join(blocks[-1][1], text))
        else:
            blocks.append(("p", text))
        previous = line

    out = []
    for i, (kind, text) in enumerate(blocks):
        rendered = f"{'#' * int(kind[1])} {text}" if kind.startswith("h") else text
        # List items stay on consecutive lines; everything else is separated by a blank line.
        joiner = "\n" if i and kind == "item" and blocks[i - 1][0] == "item" else "\n\n"
        out.append(rendered if i == 0 else joiner + rendered)
    return "".join(out), headings
