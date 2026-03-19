"""
Agent 1 – PDF Parser

Input  : state["pdf_path"]
Output : state["cv_text"]
"""

from __future__ import annotations

from typing import Any, Dict

from services.pdf_service import extract_text_from_pdf
from utils.logger import logger


def pdf_parser_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: extract raw text from a PDF file.

    Updates state with:
      - cv_text        : extracted and cleaned text
      - current_step   : "pdf_parser"
      - errors         : list (appended on failure)
    """
    logger.info("[PDFParser] Starting PDF extraction for session %s", state.get("session_id"))

    pdf_path: str = state.get("pdf_path", "")
    errors: list = list(state.get("errors", []))

    if not pdf_path:
        error_msg = "pdf_path is missing from state."
        logger.error("[PDFParser] %s", error_msg)
        errors.append(error_msg)
        return {
            "cv_text": "",
            "errors": errors,
            "current_step": "pdf_parser",
        }

    try:
        cv_text = extract_text_from_pdf(pdf_path)
        logger.info(
            "[PDFParser] Successfully extracted %d characters.", len(cv_text)
        )
        return {
            "cv_text": cv_text,
            "errors": errors,
            "current_step": "pdf_parser",
        }
    except Exception as exc:
        error_msg = f"PDF extraction failed: {exc}"
        logger.error("[PDFParser] %s", error_msg)
        errors.append(error_msg)
        return {
            "cv_text": "",
            "errors": errors,
            "current_step": "pdf_parser",
        }
