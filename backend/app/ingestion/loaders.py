from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TextBlock:
    text: str
    page_number: int | None = None


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown", ".csv"}


def load_document(path: str | Path) -> list[TextBlock]:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix}")
    if suffix == ".pdf":
        return _load_pdf(file_path)
    if suffix == ".docx":
        return _load_docx(file_path)
    if suffix in {".txt", ".md", ".markdown"}:
        return _load_text(file_path)
    if suffix == ".csv":
        return _load_csv(file_path)
    raise ValueError(f"Unsupported file type: {suffix}")


def _load_pdf(path: Path) -> list[TextBlock]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    blocks: list[TextBlock] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            blocks.append(TextBlock(text=text, page_number=index))
    return blocks


def _load_docx(path: Path) -> list[TextBlock]:
    from docx import Document

    doc = Document(str(path))
    paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
    return [TextBlock(text="\n".join(paragraphs))]


def _load_text(path: Path) -> list[TextBlock]:
    return [TextBlock(text=path.read_text(encoding="utf-8", errors="ignore"))]


def _load_csv(path: Path) -> list[TextBlock]:
    import pandas as pd

    frame = pd.read_csv(path)
    blocks: list[TextBlock] = []
    for row_number, row in frame.iterrows():
        values = [f"{column}: {row[column]}" for column in frame.columns]
        blocks.append(TextBlock(text=f"row {row_number + 1}\n" + "\n".join(values)))
    return blocks

