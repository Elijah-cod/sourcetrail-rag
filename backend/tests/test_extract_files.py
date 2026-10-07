import io
from pathlib import Path

import docx
import pytest

from app.ingest import ExtractionError, extract_file
from app.ingest.models import clean_text, guess_year

FIXTURES = Path(__file__).parent / "fixtures"


def test_pdf_gives_one_section_per_page():
    doc = extract_file("annual-report-2024.pdf", (FIXTURES / "sample.pdf").read_bytes())
    assert doc.source_type == "pdf"
    assert doc.title == "Sample Annual Report"          # from PDF metadata
    assert [s.page for s in doc.sections] == [1, 2]
    assert "declined in 2024" in doc.sections[1].text
    assert doc.published_year == 2024                    # guessed from the filename


def test_markdown_splits_on_headings_and_ignores_code_blocks():
    md = b"# Guide\nIntro text.\n\n## Install\nRun it.\n```\n# not a heading\n```\n## Usage\nUse it."
    doc = extract_file("guide.md", md)
    assert doc.title == "Guide"
    assert [s.heading for s in doc.sections] == ["Guide", "Install", "Usage"]
    assert "# not a heading" in doc.sections[1].text


def test_docx_groups_paragraphs_under_headings():
    document = docx.Document()
    document.add_heading("Overview", level=1)
    document.add_paragraph("First paragraph.")
    document.add_paragraph("Second paragraph.")
    document.add_heading("Details", level=1)
    document.add_paragraph("More detail.")
    buffer = io.BytesIO()
    document.save(buffer)

    doc = extract_file("notes.docx", buffer.getvalue())
    assert [s.heading for s in doc.sections] == ["Overview", "Details"]
    assert doc.sections[0].text == "First paragraph.\n\nSecond paragraph."


def test_csv_makes_one_section_per_row():
    data = b"product,revenue,year\nWidget,100,2023\nGadget,,2024\n"
    doc = extract_file("sales.csv", data)
    assert [s.row for s in doc.sections] == [1, 2]
    assert doc.sections[0].text == "product: Widget; revenue: 100; year: 2023"
    assert doc.sections[1].text == "product: Gadget; year: 2024"   # empty cells skipped


def test_txt_falls_back_to_latin1():
    doc = extract_file("old_notes.txt", "Caf\xe9 menu".encode("latin-1"))
    assert doc.title == "old notes"
    assert doc.sections[0].text == "Café menu"


def test_unsupported_type_is_rejected():
    with pytest.raises(ExtractionError, match="Unsupported"):
        extract_file("picture.png", b"\x89PNG")


def test_empty_file_is_rejected():
    with pytest.raises(ExtractionError, match="No text"):
        extract_file("empty.txt", b"   \n\n ")


def test_corrupt_pdf_is_rejected():
    with pytest.raises(ExtractionError, match="Could not read PDF"):
        extract_file("broken.pdf", b"this is not a pdf")


def test_helpers():
    assert guess_year("report_2019_final.pdf") == 2019
    assert guess_year("v12345.pdf") is None
    assert clean_text("a  b \r\n\n\n\nc\x00") == "a b\n\nc"


# ---------- PDF structure (tests/fixtures/structured.pdf, see make_structured_pdf.py) ----------

def structured():
    return extract_file("handbook (2).pdf", (FIXTURES / "structured.pdf").read_bytes())


def test_pdf_placeholder_metadata_title_is_ignored():
    # The metadata says "untitled"; the big heading on page 1 is the real title.
    assert structured().title == "Aurora Operations Handbook"


def test_pdf_headings_lists_and_paragraphs_are_kept():
    page1 = structured().sections[0].text
    assert page1.startswith("# Aurora Operations Handbook\n\n## 1. Service Availability\n\n")
    assert "\n\n### Maintenance windows\n\n" in page1
    assert ("- Customers receive notice at least 72 hours ahead.\n"
            "- Emergency fixes may happen at any time.\n") in page1
    # Wrapped lines are joined back into one paragraph.
    assert "Planned maintenance is excluded from the calculation when customers are notified in advance." in page1


def test_pdf_running_header_and_page_numbers_are_dropped():
    for section in structured().sections:
        assert "Aurora Operations Handbook" not in section.text.replace("# Aurora Operations Handbook", "")
        assert not any(line.strip().isdigit() for line in section.text.splitlines())


def test_pdf_heading_carries_over_page_breaks():
    pages = structured().sections
    assert [p.heading for p in pages] == [None, "Maintenance windows", "2. Incident Response"]


def test_file_name_fallback_title_is_readable():
    from app.ingest.files import _stem
    assert _stem("BSR+110+-+Theological+Writing+Skills (8).pdf") == "BSR 110 - Theological Writing Skills"
    assert _stem("annual_report-2024.pdf") == "annual report 2024"


def test_hyphenated_line_breaks_are_rejoined():
    from app.ingest.pdf_layout import _join
    assert _join("planned main-", "tenance") == "planned maintenance"
    assert _join("state-of-the-", "Art") == "state-of-the- Art"      # capital: a real hyphen, keep it
