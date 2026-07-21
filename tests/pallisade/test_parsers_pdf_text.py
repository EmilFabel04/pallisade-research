from pathlib import Path
from pallisade_core.documents.parsers.pdf_text import extract_text_pages

FIXTURE = Path(__file__).parent / "fixtures" / "text_cim.pdf"


def test_extracts_two_pages():
    pages = extract_text_pages(FIXTURE.read_bytes())
    assert len(pages) == 2
    assert pages[0][0] == 1
    assert "Falcon" in pages[0][1]
    assert pages[1][0] == 2
    assert "EBITDA" in pages[1][1]


def test_returns_empty_text_for_empty_pdf(tmp_path):
    # An empty bytes input should not crash — return [] so callers can re-route.
    pages = extract_text_pages(b"%PDF-1.4\n%%EOF\n")
    assert pages == [] or all(text == "" for _, text in pages)
