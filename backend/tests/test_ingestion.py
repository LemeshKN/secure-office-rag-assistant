from app.ingestion.chunking import split_text_blocks
from app.ingestion.loaders import TextBlock


def test_chunking_creates_overlapping_chunks() -> None:
    text = "A" * 20 + " " + "B" * 20 + " " + "C" * 20
    chunks = split_text_blocks([TextBlock(text=text, page_number=3)], chunk_size_chars=30, overlap_chars=10)
    assert len(chunks) >= 2
    assert chunks[0].page_number == 3
    assert chunks[1].char_start == 20
    assert chunks[0].chunk_index == 0


def test_chunking_rejects_invalid_overlap() -> None:
    try:
        split_text_blocks([TextBlock(text="hello")], chunk_size_chars=10, overlap_chars=10)
    except ValueError as exc:
        assert "overlap" in str(exc)
    else:
        raise AssertionError("Expected ValueError")

