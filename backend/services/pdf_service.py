"""
Servicio de extracción de PDF a texto.

Estrategia (con fallback):
  1. pdfplumber  – rápido, alta fidelidad para PDFs basados en texto.
  2. PyMuPDF     – segundo intento para diseños complejos.
  3. Visión LLM  – último recurso (maneja documentos escaneados o con OCR pobre).
"""

import re
import os
from pathlib import Path
from typing import Optional

from config.settings import settings
from services.llm_service import extract_content_with_vision
from utils.logger import logger


# ── E2B Sandbox (Seguridad y Aislamiento) ────────────────────────────────────
async def _extract_with_e2b_sandbox(path: str) -> Optional[str]:
    """
    Usa el E2B Code Interpreter para extraer texto de un PDF en un sandbox seguro.
    Este método es el más seguro para tratar con archivos de origen desconocido.
    """
    api_key = settings.e2b_api_key
    if not api_key:
        logger.debug("E2B_API_KEY no detectada. Saltando Sandbox.")
        return None

    try:
        from e2b_code_interpreter import Sandbox
        
        logger.info("Iniciando Sandbox de E2B para extracción segura...")
        
        # El context manager asegura que el sandbox se cierre al terminar
        with Sandbox.create(api_key=api_key) as sandbox:
            logger.info("Sandbox creado exitosamente. Subiendo archivo: {}", path)
            # Subir el PDF al entorno aislado
            remote_path = "/home/user/cv_to_process.pdf"
            with open(path, "rb") as f:
                sandbox.files.write(remote_path, f)
            
            logger.info("Archivo subido. Instalando dependencias en el Sandbox...")
            sandbox.commands.run("pip install pypdf")
            
            logger.info("Dependencias listas. Ejecutando código de extracción...")
            # Ejecutar script de extracción dentro del sandbox
            code = f"""
import pypdf
import os

pdf_path = "{remote_path}"
if not os.path.exists(pdf_path):
    print("Error: El archivo no se subió correctamente.")
else:
    try:
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\\n"
        print(text.strip())
    except Exception as e:
        print(f"Error en pypdf: {{e}}")
"""
            execution = sandbox.run_code(code)
            
            if execution.error:
                logger.warning("Error en ejecución dentro del Sandbox: {}", execution.error)
                return None
            
            # Extraer el resultado del stdout (que es una lista de líneas)
            extracted_text = "\n".join(execution.logs.stdout).strip()
            
            if not extracted_text:
                logger.warning("El Sandbox devolvió un texto vacío. Logs: {}", execution.logs.stdout)
                return None
                
            logger.info("Extracción exitosa desde Sandbox.")
            return extracted_text

    except Exception as exc:
        logger.error("Fallo crítico en E2B Sandbox: {}", exc)
        import traceback
        logger.error(traceback.format_exc())
        return None


# ── pdfplumber ────────────────────────────────────────────────────────────────
def _extract_with_pdfplumber(path: str) -> Optional[str]:
    """Intenta extraer texto usando pdfplumber."""
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
        logger.warning("pdfplumber falló: {}", exc)
        return None


# ── PyMuPDF ───────────────────────────────────────────────────────────────────
def _extract_with_pymupdf(path: str) -> Optional[str]:
    """Intenta extraer texto usando PyMuPDF (fitz)."""
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
        logger.warning("PyMuPDF falló: {}", exc)
        return None


# ── Visión LLM (Avanzado) ─────────────────────────────────────────────────────
async def _extract_with_vision_llm(path: str) -> Optional[str]:
    """
    Convierte la primera página del PDF en imagen y usa un LLM 
    para extraer el texto estructurado.
    """
    try:
        import fitz  # type: ignore
        from pathlib import Path

        doc = fitz.open(path)
        if len(doc) == 0:
            return None
        
        # Renderizamos la primera página (suele ser la más importante/densa)
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Zoom 2x para mejor OCR
        
        temp_img = Path(path).with_suffix(".temp_page.jpg")
        pix.save(str(temp_img))
        doc.close()

        prompt = (
            "Eres un experto en reclutamiento IT. Analiza la imagen de este CV "
            "y extrae TODO el texto relevante de forma estructurada. "
            "Mantén el orden cronológico de la experiencia y la lista de habilidades."
        )
        
        # Llamada al servicio LLM con capacidad de visión
        text = await extract_content_with_vision(str(temp_img), prompt)
        
        # Limpieza del archivo temporal
        if temp_img.exists():
            temp_img.unlink()
            
        return text if text else None
    except Exception as exc:
        logger.warning("La extracción por Visión LLM falló: {}", exc)
        return None


# ── Limpieza de texto ─────────────────────────────────────────────────────────
def _clean_text(text: str) -> str:
    """Elimina ruidos y normaliza el texto extraído del PDF."""
    # Colapsar 3+ saltos de línea consecutivos → doble salto de línea (párrafo)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Eliminar caracteres no imprimibles (manteniendo tildes y caracteres latinos comunes)
    text = re.sub(r"[^\x20-\x7E\n\t\u00C0-\u024F\u0370-\u03FF]", " ", text)
    # Colapsar espacios excesivos
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


# ── API Pública ───────────────────────────────────────────────────────────────
async def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extrae texto limpio de un archivo PDF usando el mejor extractor disponible.
    Incluye soporte para visión mediante LLM como último recurso.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise ValueError(f"Archivo PDF no encontrado: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Se esperaba un archivo .pdf, se obtuvo: {path.suffix}")

    logger.info("Extrayendo texto del PDF: {}", path.name)

    # 1. Prioridad 0: Sandbox de E2B (Máxima seguridad y aislamiento)
    # Intentamos primero el Sandbox si las credenciales están presentes.
    text = await _extract_with_e2b_sandbox(str(path))
    if text and len(text.strip()) > 100:
        cleaned = _clean_text(text)
        logger.info("Extraídos {} caracteres usando E2B Sandbox", len(cleaned))
        return cleaned

    # 2. Intentamos los métodos rápidos y tradicionales (Fallback local)
    for extractor_fn in (
        _extract_with_pdfplumber,
        _extract_with_pymupdf,
    ):
        text = extractor_fn(str(path))
        if text and len(text.strip()) > 300: # Si extraemos un texto sustancial, paramos
            cleaned = _clean_text(text)
            logger.info("Extraídos {} caracteres usando {}", len(cleaned), extractor_fn.__name__)
            return cleaned

    # 2. Si los anteriores fallan o el texto es pobre, usamos el fallback de Visión
    logger.info("Los extractores rápidos devolvieron resultados pobres. Intentando Visión LLM...")
    text = await _extract_with_vision_llm(str(path))
    if text:
        cleaned = _clean_text(text)
        logger.info("Extraídos {} caracteres usando Visión LLM", len(cleaned))
        return cleaned

    raise ValueError(
        "Todos los extractores de PDF fallaron o el documento no contiene texto extraíble."
    )
