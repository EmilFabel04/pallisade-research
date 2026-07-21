from pallisade_core.rag.chunking import Chunk, chunk_pages, chunk_sheets
from pallisade_core.documents.parsers.xlsx import SheetText


def _pages(*pages: tuple[int, str]) -> list[tuple[int, str]]:
    return list(pages)


def test_short_pages_each_become_one_chunk_no_cross_page():
    pages = _pages((1, "Alpha beta gamma."), (2, "Delta epsilon zeta."))
    chunks = chunk_pages(pages, target_tokens=500, overlap_tokens=80)
    assert [c.page_from for c in chunks] == [1, 2]
    assert all(c.page_from == c.page_to for c in chunks)
    assert chunks[0].text.startswith("Alpha")
    assert chunks[1].text.startswith("Delta")


def test_oversized_single_page_splits_mid_page():
    big = "Sentence. " * 1000
    pages = _pages((1, big))
    chunks = chunk_pages(pages, target_tokens=200, overlap_tokens=40)
    assert len(chunks) > 1
    assert all(c.page_from == 1 and c.page_to == 1 for c in chunks)
    for c in chunks:
        assert c.token_count > 0
        assert c.chunk_index >= 0


def test_chunk_indices_are_sequential_from_zero():
    pages = _pages((1, "A. B. C."), (2, "D. E. F."), (3, "G. H. I."))
    chunks = chunk_pages(pages, target_tokens=500, overlap_tokens=80)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunk_sheets_one_chunk_per_small_sheet():
    sheets = [SheetText(sheet_name="A", text="[Sheet: A]\nA1: 1", row_count=1),
              SheetText(sheet_name="B", text="[Sheet: B]\nA1: 2", row_count=1)]
    chunks = chunk_sheets(sheets, target_tokens=1500)
    assert [c.sheet_name for c in chunks] == ["A", "B"]
    assert all(c.page_from is None for c in chunks)


def test_large_sheet_splits():
    big_body = "\n".join(f"A{i}: x" for i in range(5000))
    sheets = [SheetText(sheet_name="Big", text=f"[Sheet: Big]\n{big_body}", row_count=5000)]
    chunks = chunk_sheets(sheets, target_tokens=500)
    assert len(chunks) > 1
    assert all(c.sheet_name == "Big" for c in chunks)
