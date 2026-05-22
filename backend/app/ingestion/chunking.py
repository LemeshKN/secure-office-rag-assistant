from dataclasses import dataclass

from app.ingestion.loaders import TextBlock


@dataclass(frozen=True)
class ChunkCandidate:
    text: str
    chunk_index: int
    page_number: int | None = None
    char_start: int | None = None
    char_end: int | None = None


def split_text_blocks(
    blocks: list[TextBlock],
    chunk_size_chars: int = 3000,
    overlap_chars: int = 500,
) -> list[ChunkCandidate]:
    """Split extracted text into stable, overlapping chunks."""

    if chunk_size_chars <= 0:
        raise ValueError("chunk_size_chars must be positive")
    if overlap_chars >= chunk_size_chars:
        raise ValueError("overlap_chars must be smaller than chunk_size_chars")

    chunks: list[ChunkCandidate] = []
    chunk_index = 0
    step = chunk_size_chars - overlap_chars

    for block in blocks:
        text = _normalize_text(block.text)
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(start + chunk_size_chars, len(text))
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    ChunkCandidate(
                        text=chunk_text,
                        chunk_index=chunk_index,
                        page_number=block.page_number,
                        char_start=start,
                        char_end=end,
                    )
                )
                chunk_index += 1
            if end == len(text):
                break
            start += step
    return chunks


def _normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    compact_lines = [line for line in lines if line]
    return "\n".join(compact_lines)

