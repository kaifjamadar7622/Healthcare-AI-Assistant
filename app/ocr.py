"""Optional OCR ingestion helpers for scanned documents."""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import suppress
from pathlib import Path
from typing import Iterable


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
PDF_EXTENSION = ".pdf"
TEXT_EXTENSIONS = {".txt", ".md"}


@dataclass(frozen=True, slots=True)
class OCRDocument:
    """Text extracted from an OCR-capable source file."""

    id: str
    title: str
    text: str
    source_path: str
    tags: list[str]


def discover_ocr_sources(root: Path) -> list[Path]:
    """Return supported files under the OCR source directory."""

    if not root.exists():
        return []

    supported: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS | {PDF_EXTENSION} | TEXT_EXTENSIONS:
            supported.append(path)
    return sorted(supported)


def extract_documents_from_path(path: Path) -> list[OCRDocument]:
    """Extract one or more OCR documents from a file path."""

    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        return [
            OCRDocument(
                id=path.stem,
                title=path.stem.replace("_", " ").replace("-", " ").title(),
                text=text,
                source_path=str(path),
                tags=["ocr", "text"],
            )
        ] if text else []

    if suffix in IMAGE_EXTENSIONS:
        return _extract_from_image(path)

    if suffix == PDF_EXTENSION:
        return _extract_from_pdf(path)

    return []


def extract_documents(paths: Iterable[Path]) -> list[OCRDocument]:
    documents: list[OCRDocument] = []
    for path in paths:
        documents.extend(extract_documents_from_path(path))
    return documents


def _extract_from_image(path: Path) -> list[OCRDocument]:
    try:
        from PIL import Image  # type: ignore
        import pytesseract  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency guard
        raise RuntimeError(
            "OCR image extraction requires Pillow and pytesseract. Install them and ensure the Tesseract binary is available."
        ) from exc

    image = Image.open(path)
    text = pytesseract.image_to_string(image).strip()
    if not text:
        return []

    return [
        OCRDocument(
            id=path.stem,
            title=path.stem.replace("_", " ").replace("-", " ").title(),
            text=text,
            source_path=str(path),
            tags=["ocr", "image"],
        )
    ]


def _extract_from_pdf(path: Path) -> list[OCRDocument]:
    try:
        import fitz  # type: ignore
        from PIL import Image  # type: ignore
        import pytesseract  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency guard
        raise RuntimeError(
            "PDF OCR ingestion requires PyMuPDF, Pillow, and pytesseract."
        ) from exc

    documents: list[OCRDocument] = []
    pdf = fitz.open(str(path))
    for page_number in range(pdf.page_count):
        page = pdf.load_page(page_number)
        text = (page.get_text("text") or "").strip()

        if not text:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
            with suppress(Exception):
                text = pytesseract.image_to_string(image).strip()

        if text:
            documents.append(
                OCRDocument(
                    id=f"{path.stem}-page-{page_number + 1}",
                    title=f"{path.stem.replace('_', ' ').replace('-', ' ').title()} page {page_number}",
                    text=text,
                    source_path=str(path),
                    tags=["ocr", "pdf", f"page-{page_number + 1}"],
                )
            )
    return documents