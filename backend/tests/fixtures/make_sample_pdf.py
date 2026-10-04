"""Regenerate tests/fixtures/sample.pdf (a 2-page PDF with known text).

Run with:  uv run --with reportlab python tests/fixtures/make_sample_pdf.py
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

out = Path(__file__).with_name("sample.pdf")
pdf = canvas.Canvas(str(out), pagesize=A4)
pdf.setTitle("Sample Annual Report")
pdf.drawString(72, 750, "Revenue grew 12 percent in 2023.")
pdf.showPage()
pdf.drawString(72, 750, "Revenue declined in 2024 because of lower demand.")
pdf.showPage()
pdf.save()
print("wrote", out)
