"""Build demo/sources/sourcetrail-overview-2026.pdf (original text describing this project).

Run from backend/:  uv run --with reportlab python demo/make_overview_pdf.py
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

PAGES = [
    ("SourceTrail Architecture Overview", [
        "SourceTrail is a multi-source retrieval-augmented generation (RAG) knowledge base. "
        "Visitors upload PDF, DOCX, Markdown, TXT and CSV files or add web pages, then ask "
        "questions and receive grounded answers with inline citations such as [1] and [2].",
        "Every citation can be inspected: clicking it shows the document, page or section, and "
        "the exact chunk of text the answer relied on. Each chunk has a stable identifier built "
        "from the document slug, the page number and the chunk position, for example "
        "annual-report-2024:p47:c003.",
        "The system runs entirely on free infrastructure: a FastAPI service, PostgreSQL with the "
        "pgvector extension, CPU-only ONNX models from FastEmbed, and a hosted open-weight LLM.",
    ]),
    ("Ingestion pipeline", [
        "Each file type has its own extractor. PDFs are split into one section per page, Markdown "
        "and Word documents into one section per heading, and CSV files into one section per row. "
        "Web pages are fetched with strict safety checks and their main article text is extracted "
        "with trafilatura, which removes menus and footers.",
        "Sections are cut into chunks of about 1,000 characters with an overlap of 150 characters, "
        "preferring paragraph, then line, then sentence boundaries. CSV rows are grouped into "
        "chunks but a single row is never split.",
        "Chunks are embedded with the bge-small-en-v1.5 model, which produces 384-dimensional "
        "vectors. The document title and section heading are prepended before embedding so that "
        "each vector carries its context. Storage happens in a single transaction: a document is "
        "saved with all of its chunks or not at all.",
    ]),
    ("Retrieval and answering", [
        "Every question runs two searches. Vector search finds the 20 chunks closest in meaning "
        "using cosine distance on an HNSW index. Keyword search finds the 20 best word matches "
        "using PostgreSQL full-text search ranked with ts_rank_cd.",
        "The two ranked lists are merged with Reciprocal Rank Fusion. Each chunk receives "
        "1 / (60 + rank) points from every list it appears in, so chunks that both methods agree "
        "on rise to the top, and the different score scales of the two methods do not matter.",
        "The 30 best fused candidates are re-scored by a cross-encoder, ms-marco-MiniLM-L-6-v2, "
        "which reads the question and each chunk together. The top 6 chunks are sent to the LLM "
        "as numbered sources. Citation markers that point to sources that were not provided are "
        "removed before the answer is shown.",
    ]),
    ("Safety on a public site", [
        "SourceTrail has no logins. Each visitor receives an anonymous workspace identified by a "
        "random ID stored in an HTTP-only cookie. Searches cover the visitor's own workspace plus "
        "the shared demo collection, and no visitor can see another visitor's documents.",
        "Rate limits are keyed by a hash of the client IP address: 10 questions per minute and "
        "20 uploads per hour. Each workspace may hold 10 documents and 2,000 chunks. A site-wide "
        "cap of 800 AI answers per day keeps usage within the free LLM quota; when it is reached, "
        "visitors still see the most relevant passages.",
        "Visitor workspaces are deleted automatically 24 hours after their last activity. The "
        "system prompt instructs the model to treat uploaded documents as information and never "
        "as instructions, which defends against prompt injection.",
    ]),
]


def main() -> None:
    out = Path(__file__).parent / "sources" / "sourcetrail-overview-2026.pdf"
    styles = getSampleStyleSheet()
    story = []
    for i, (heading, paragraphs) in enumerate(PAGES):
        story.append(Paragraph(heading, styles["Heading1"]))
        for text in paragraphs:
            story += [Paragraph(text, styles["BodyText"]), Spacer(1, 8)]
        if i < len(PAGES) - 1:
            story.append(PageBreak())
    SimpleDocTemplate(str(out), pagesize=A4, title="SourceTrail Architecture Overview",
                      author="sourcetrail-rag").build(story)
    print("wrote", out)


if __name__ == "__main__":
    main()
