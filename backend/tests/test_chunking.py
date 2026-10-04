from app.chunking import chunk_document, slugify, split_text
from app.ingest.models import ExtractedDocument, Section


def sentences(n: int) -> str:
    return " ".join(f"Sentence number {i} talks about retrieval." for i in range(n))


def test_short_text_is_one_chunk():
    assert split_text("Just a short note.") == ["Just a short note."]


def test_long_text_respects_max_size():
    chunks = split_text(sentences(200), max_chars=300, overlap_chars=60)
    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)


def test_consecutive_chunks_overlap():
    chunks = split_text(sentences(50), max_chars=300, overlap_chars=100)
    for first, second in zip(chunks, chunks[1:]):
        # The last sentence of one chunk reappears at the start of the next.
        last_sentence = first.rsplit(". ", 1)[-1]
        assert last_sentence.rstrip(".") in second[:150]


def test_prefers_paragraph_boundaries():
    para_a = "A" * 200
    para_b = "B" * 200
    chunks = split_text(f"{para_a}\n\n{para_b}", max_chars=250, overlap_chars=0)
    assert chunks == [para_a, para_b]


def test_hard_cut_when_no_boundary_exists():
    chunks = split_text("x" * 2500, max_chars=1000, overlap_chars=0)
    assert [len(c) for c in chunks] == [1000, 1000, 500]


def test_pdf_chunks_get_page_based_ids():
    doc = ExtractedDocument(title="Report", source_type="pdf", sections=[
        Section(text="Page one text.", page=1),
        Section(text="Page two text.", page=2),
    ])
    chunks = chunk_document(doc, slug="annual-report-2024")
    assert [c.id for c in chunks] == ["annual-report-2024:p1:c000", "annual-report-2024:p2:c001"]
    assert [c.page for c in chunks] == [1, 2]
    assert [c.ord for c in chunks] == [0, 1]


def test_markdown_chunks_keep_their_heading():
    doc = ExtractedDocument(title="Guide", source_type="md", sections=[
        Section(text=sentences(40), heading="Install"),
    ])
    chunks = chunk_document(doc, slug="guide", max_chars=300, overlap_chars=50)
    assert len(chunks) > 1
    assert all(c.section == "Install" for c in chunks)
    assert chunks[0].id == "guide:c000"


def test_csv_rows_are_grouped_and_never_split():
    rows = [Section(text=f"product: Item{i}; revenue: {i * 10}", row=i) for i in range(1, 51)]
    doc = ExtractedDocument(title="Sales", source_type="csv", sections=rows)
    chunks = chunk_document(doc, slug="sales", max_chars=200)
    assert len(chunks) > 1
    assert chunks[0].section.startswith("Rows 1–")
    for chunk in chunks:
        assert len(chunk.text) <= 200
        for line in chunk.text.split("\n"):
            assert line.startswith("product: Item")      # every line is a whole row


def test_slugify():
    assert slugify("Annual Report (2024).pdf") == "annual-report-2024-pdf"
    assert slugify("!!!") == "document"
    assert len(slugify("word " * 50)) <= 60
