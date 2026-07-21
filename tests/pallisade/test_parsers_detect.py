from pallisade_core.documents.parsers.detect import (
    SourceKind, UnsupportedType, classify_bytes, classify_pdf_text_density,
)
import pytest


def test_classify_xlsx_from_content_type():
    kind = classify_bytes(
        filename="m.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        head=b"PK\x03\x04",
    )
    assert kind == SourceKind.XLSX


def test_classify_pdf_by_magic_bytes():
    kind = classify_bytes(filename="x.pdf", content_type="application/octet-stream",
                          head=b"%PDF-1.7\n...")
    # PDFs require a second classify pass on extracted text; first pass returns PDF (unknown type yet).
    assert kind == SourceKind.PDF_UNKNOWN


def test_unsupported_type_rejected():
    with pytest.raises(UnsupportedType):
        classify_bytes(filename="x.txt", content_type="text/plain", head=b"hello")


def test_text_density_threshold_routes_to_scan_below_100_per_page():
    assert classify_pdf_text_density(per_page_chars=[50, 0, 30]) == SourceKind.PDF_SCAN


def test_text_density_threshold_routes_to_text_above_100_per_page():
    assert classify_pdf_text_density(per_page_chars=[500, 800, 1200]) == SourceKind.PDF_TEXT
