"""Regenerate tests/fixtures/structured.pdf: a 3-page PDF laid out like a real handbook.

It has the things a reader relies on and pypdf loses: a big title, numbered section headings,
a bold subheading, wrapped paragraphs (one with a hyphenated word), a bullet list, a running
header and page numbers on every page, and the placeholder metadata title "untitled".

Run with:  uv run --with reportlab python tests/fixtures/make_structured_pdf.py
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer

out = Path(__file__).with_name("structured.pdf")
styles = getSampleStyleSheet()
body = ParagraphStyle("body", parent=styles["BodyText"], fontName="Helvetica", fontSize=10, leading=13, spaceAfter=8)
h1 = ParagraphStyle("h1", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, spaceAfter=12)
h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=18, spaceAfter=6)
h3 = ParagraphStyle("h3", parent=body, fontName="Helvetica-Bold", fontSize=10, spaceAfter=4)


def header_and_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.drawString(72, A4[1] - 40, "Aurora Operations Handbook")
    canvas.drawRightString(A4[0] - 72, 30, str(doc.page))
    canvas.restoreState()


filler = ("The platform team reviews this policy every quarter and publishes changes to all customers "
          "through the status page and the monthly newsletter. ")
story = [
    Paragraph("Aurora Operations Handbook", h1),
    Paragraph("1. Service Availability", h2),
    Paragraph("Aurora targets 99.9 percent monthly availability for the Business plan. Planned "
              "maintenance is excluded from the calculation when customers are notified in advance. " + filler * 2, body),
    Paragraph("Maintenance windows", h3),
    Paragraph("Maintenance happens on Sundays between 02:00 and 04:00 UTC. " + filler, body),
    ListFlowable([ListItem(Paragraph(t, body)) for t in (
        "Customers receive notice at least 72 hours ahead.",
        "Emergency fixes may happen at any time.",
        "Each window is announced on the status page.",
    )], bulletType="bullet", start="•"),
    PageBreak(),
    Paragraph("2. Incident Response", h2),
    Paragraph("A critical incident is an event that causes a major disruption to a production service. " + filler * 3, body),
    PageBreak(),
    Paragraph("Recovery objectives", h3),
    Paragraph("A recovery time objective describes the target time for restoring a service. " + filler, body),
]
doc = SimpleDocTemplate(str(out), pagesize=A4, title="untitled")
doc.build(story, onFirstPage=header_and_page_number, onLaterPages=header_and_page_number)
print("wrote", out)
