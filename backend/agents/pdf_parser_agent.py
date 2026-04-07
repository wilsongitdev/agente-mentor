"""
Agente 1: Lector de PDF (PDF Parser Agent)

Este agente es el punto de entrada al procesamiento de CVs.
Se encarga de recibir una ruta de archivo local, llamar al servicio de extracción
y devolver el texto plano para los siguientes nodos.

Input: state["pdf_path"]
Output: state["cv_text"], state["current_step"], state["errors"]
"""

from __future__ import annotations
import json
from typing import Any, Dict

from services.pdf_service import extract_text_from_pdf
from utils.logger import logger


async def pdf_parser_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nodo de LangGraph: coordina la extracción de texto bruto de un archivo PDF.
    
    Valida la existencia de la ruta del archivo y delega la extracción al
    servicio correspondiente, manejando posibles excepciones de lectura.

    Args:
        state (Dict[str, Any]): Estado actual de la sesión.
        
    Returns:
        Dict[str, Any]: Estado actualizado con el texto extraído del CV.
    """
    session_id = state.get("session_id", "unknown")
    logger.info("[PDFParser] Iniciando extracción para la sesión {}", session_id)
    
    # --- VISUALIZACIÓN DE ENTRADA ---
    logger.debug("[PDFParser] Entrada -> pdf_path: {}", state.get("pdf_path"))

    pdf_path: str = state.get("pdf_path", "")
    errors: list = list(state.get("errors", []))

    if not pdf_path:
        error_msg = "Falta el campo pdf_path en el estado."
        logger.error("[PDFParser] {}", error_msg)
        errors.append(error_msg)
        return {
            "cv_text": "",
            "errors": errors,
            "current_step": "pdf_parser",
        }

    try:
        cv_text = await extract_text_from_pdf(pdf_path)
        
        # --- VISUALIZACIÓN DE SALIDA ---
        logger.info("[PDFParser] Éxito. Extraídos {} caracteres.", len(cv_text))
        
        return {
            "cv_text": cv_text,
            "errors": errors,
            "current_step": "pdf_parser",
        }
    except Exception as exc:
        error_msg = f"Fallo en la extracción del PDF: {exc}"
        logger.error("[PDFParser] {}", error_msg)
        errors.append(error_msg)
        return {
            "cv_text": "",
            "errors": errors,
            "current_step": "pdf_parser",
        }
