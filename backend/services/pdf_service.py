"""
PDF-to-text extraction service.

Strategy (with fallback):
  1. pdfplumber  – fast, high fidelity for text-based PDFs
  2. PyMuPDF     – second try for tricky layouts
  3. unstructured – last resort (handles scanned / OCR docs)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from utils.logger import logger


# ── pdfplumber ────────────────────────────────────────────────────────────────
def _extract_with_pdfplumber(path: str) -> Optional[str]:
    try:
        import pdfplumber  # type: ignore

        pages_text: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text(x_tolerance=3, y_tolerance=3)
                if text:
                    pages_text.append(text)

        if not pages_text:
            return None

        return "\n\n".join(pages_text)
    except Exception as exc:
        logger.warning("pdfplumber failed: %s", exc)
        return None


# ── PyMuPDF ───────────────────────────────────────────────────────────────────
def _extract_with_pymupdf(path: str) -> Optional[str]:
    try:
        import fitz  # type: ignore  (PyMuPDF)

        doc = fitz.open(path)
        pages_text: list[str] = []
        for page in doc:
            text = page.get_text("text")
            if text.strip():
                pages_text.append(text)
        doc.close()

        return "\n\n".join(pages_text) if pages_text else None
    except Exception as exc:
        logger.warning("PyMuPDF failed: %s", exc)
        return None


# ── unstructured ──────────────────────────────────────────────────────────────
def _extract_with_unstructured(path: str) -> Optional[str]:
    try:
        from unstructured.partition.pdf import partition_pdf  # type: ignore

        elements = partition_pdf(filename=path)
        text = "\n".join(str(el) for el in elements if str(el).strip())
        return text if text else None
    except Exception as exc:
        logger.warning("unstructured failed: %s", exc)
        return None


# ── Text cleaning ─────────────────────────────────────────────────────────────
def _clean_text(text: str) -> str:
    """Remove noise from extracted PDF text."""
    # Collapse 3+ consecutive newlines → double newline (paragraph break)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove non-printable characters
    text = re.sub(r"[^\x20-\x7E\n\t\u00C0-\u024F\u0370-\u03FF]", " ", text)
    # Collapse excessive spaces
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


# ── Public API ────────────────────────────────────────────────────────────────
def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract clean text from a PDF file using the best available parser.

    Raises:
        ValueError: If the file does not exist or all parsers fail.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise ValueError(f"PDF file not found: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {path.suffix}")

    logger.info("Extracting text from PDF: %s", path.name)

    for extractor_fn in (
        _extract_with_pdfplumber,
        _extract_with_pymupdf,
        _extract_with_unstructured,
    ):
        text = extractor_fn(str(path))
        if text and len(text.strip()) > 50:
            cleaned = _clean_text(text)
            logger.info(
                "Extracted %d characters using %s",
                len(cleaned),
                extractor_fn.__name__,
            )
            return cleaned

    raise ValueError(
        "All PDF parsers failed or the document contains no extractable text."
    )
