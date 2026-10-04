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
