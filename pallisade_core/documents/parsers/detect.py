from __future__ import annotations

from enum import Enum


class SourceKind(str, Enum):
    PDF_TEXT = "pdf_text"
    PDF_SCAN = "pdf_scan"
    PDF_UNKNOWN = "pdf_unknown"    # pre-text-density classification
    XLSX = "xlsx"


class UnsupportedType(Exception):
    pass


_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_PDF_MAGIC = b"%PDF-"


def classify_bytes(*, filename: str, content_type: str, head: bytes) -> SourceKind:
    """First-pass classification from MIME + magic bytes.

    Returns PDF_UNKNOWN for PDFs — the caller must run text-density classification
    after attempting text extraction.
    """
    name = filename.lower()
    if content_type == _XLSX_MIME or name.endswith(".xlsx"):
        return SourceKind.XLSX
    if head.startswith(_PDF_MAGIC) or content_type == "application/pdf" or name.endswith(".pdf"):
        return SourceKind.PDF_UNKNOWN
    raise UnsupportedType(f"unsupported file type: filename={filename} content_type={content_type}")


def classify_pdf_text_density(*, per_page_chars: list[int]) -> SourceKind:
    """Decide pdf_text vs pdf_scan from the first N pages' extracted char count.

    Threshold: <100 chars/page mean ⇒ pdf_scan (likely image-only).
    """
    if not per_page_chars:
        return SourceKind.PDF_SCAN
    mean = sum(per_page_chars) / len(per_page_chars)
    return SourceKind.PDF_TEXT if mean >= 100 else SourceKind.PDF_SCAN
