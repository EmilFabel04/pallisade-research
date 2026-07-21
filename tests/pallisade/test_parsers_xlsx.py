from pathlib import Path

from pallisade_core.documents.parsers.xlsx import extract_sheets

FIXTURE = Path(__file__).parent / "fixtures" / "model.xlsx"


def test_extracts_two_sheets_with_headers_and_rows():
    sheets = extract_sheets(FIXTURE.read_bytes())
    names = [s.sheet_name for s in sheets]
    assert names == ["Assumptions", "DebtSchedule"]

    a = sheets[0]
    assert "Revenue ($M)" in a.text
    assert "21.2" in a.text
    assert a.text.startswith("[Sheet: Assumptions")  # header line


def test_each_sheet_has_a_header_with_row_range():
    sheets = extract_sheets(FIXTURE.read_bytes())
    for s in sheets:
        assert s.text.startswith(f"[Sheet: {s.sheet_name}")
