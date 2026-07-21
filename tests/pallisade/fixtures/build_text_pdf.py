"""Run once: `python tests/pallisade/fixtures/build_text_pdf.py`.

Generates `text_cim.pdf` deterministically using reportlab.
"""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


def build(out: Path) -> None:
    c = canvas.Canvas(str(out), pagesize=letter)
    c.drawString(72, 720, "Project Falcon — Confidential Information Memorandum")
    c.drawString(72, 700, "Section 1 — Executive Summary")
    c.drawString(72, 680, "Falcon is a vertically integrated SaaS platform serving SMB dental clinics.")
    c.showPage()
    c.drawString(72, 720, "Section 2 — Financial Highlights")
    c.drawString(72, 700, "FY24 revenue: $42.3M. FY24 EBITDA margin: 21.2%.")
    c.drawString(72, 680, "Management projects FY26 EBITDA margin of 24.5%.")
    c.showPage()
    c.save()


if __name__ == "__main__":
    out = Path(__file__).parent / "text_cim.pdf"
    build(out)
    print(f"wrote {out}")
