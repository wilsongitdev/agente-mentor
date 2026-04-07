"""
Agente 2: Extracción de Habilidades (Skill Extraction Agent)

Este agente se encarga de procesar el texto plano extraído de un CV para identificar
habilidades actuales, sugerir habilidades faltantes según el objetivo profesional,
y analizar el nivel de seniority y experiencia total.

Input: state["cv_text"], state["professional_objective"]
Output: state["current_skills"], state["suggested_skills"], state["seniority_level"], etc.
"""

from __future__ import annotations
import json
import re
from datetime import datetime
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential

from prompts.skill_extraction import SKILL_EXTRACTION_HUMAN, SKILL_EXTRACTION_SYSTEM
from services.llm_service import get_llm
from utils.logger import logger


def _parse_llm_json(raw: str) -> dict:
    """
    Extrae y parsea el primer objeto JSON encontrado en una cadena de texto.
    
    Args:
        raw (str): Raw string response from the LLM.
        
    Returns:
        dict: El objeto JSON parseado.
        
    Raises:
        ValueError: Si no se encuentra un JSON válido en la respuesta.
    """
    # Elimina marcas de bloque de código markdown if present (cleaning the response)
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    # Busca el primer bloque que empiece con { y termine con } (Regex for JSON extraction)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No se encontró ningún objeto JSON en la respuesta del LLM.")
    return json.loads(match.group())


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _call_llm(cv_text: str, professional_objective: str) -> dict:
    """
    Realiza la llamada asíncrona al LLM para la extracción de información.
    
    Args:
        cv_text (str): Texto completo del CV.
        professional_objective (str): Meta profesional del candidato.
        
    Returns:
        dict: Diccionario con los datos extraídos del LLM (skills, seniority, etc).
    """
    llm = get_llm()
    current_date = datetime.now().strftime("%B %Y")
    
    # Prepare messages using standard templates
    messages = [
        SystemMessage(content=SKILL_EXTRACTION_SYSTEM),
        HumanMessage(content=SKILL_EXTRACTION_HUMAN.format(
            cv_text=cv_text, 
            professional_objective=professional_objective,
            current_date=current_date
        )),
    ]
    
    # Executing the LLM invocation
    response = await llm.ainvoke(messages)
    return _parse_llm_json(response.content)


async def skill_extraction_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nodo de LangGraph: coordina la lógica de extracción de habilidades.
    
    Este nodo valida la entrada, llama al LLM y formatea la salida para el
    siguiente paso en el flujo de trabajo (State Management).

    Args:
        state (Dict[str, Any]): Estado actual del flujo de LangGraph.
        
    Returns:
        Dict[str, Any]: Estado actualizado con la información extraída.
    """
    session_id = state.get("session_id", "unknown")
    logger.info("[SkillExtractor] Iniciando para la sesión {}", session_id)

    cv_text: str = state.get("cv_text", "")
    professional_objective: str = state.get("professional_objective", "No especificado")
    errors: list = list(state.get("errors", []))

    # --- DIAGNÓSTICO DE ENTRADA ---
    logger.debug("[SkillExtractor] Entrada -> Texto del CV: {} caracteres.", len(cv_text))

    if not cv_text.strip():
        error_msg = "El texto del CV está vacío – no se pueden extraer habilidades."
        logger.error("[SkillExtractor] {}", error_msg)
        errors.append(error_msg)
        return {
            "current_skills": [],
            "suggested_skills": [],
            "seniority_level": "unknown",
            "candidate_name": None,
            "years_total_experience": None,
            "profile_summary": "",
            "errors": errors,
            "current_step": "skill_extractor",
        }

    try:
        result = await _call_llm(cv_text, professional_objective)
        
        # --- DIAGNÓSTICO DE SALIDA ---
        logger.info(
            "[SkillExtractor] Éxito. Extraídas {} habilidades, {} sugerencias. Seniority: {}",
            len(result.get("current_skills", [])),
            len(result.get("suggested_skills", [])),
            result.get("seniority_level", "unknown"),
        )
        logger.debug("[SkillExtractor] Salida JSON: {}", json.dumps(result, indent=2, ensure_ascii=False))

        return {
            "candidate_name": result.get("candidate_name"),
            "seniority_level": result.get("seniority_level", "unknown"),
            "years_total_experience": result.get("years_total_experience"),
            "current_skills": result.get("current_skills", []),
            "suggested_skills": result.get("suggested_skills", []),
            "profile_summary": result.get("summary", ""),
            "errors": errors,
            "current_step": "skill_extractor",
        }
    except Exception as exc:
        error_msg = f"Fallo en la llamada al LLM para extraer habilidades: {exc}"
        logger.error("[SkillExtractor] {}", error_msg)
        errors.append(error_msg)
        return {
            "current_skills": [],
            "suggested_skills": [],
            "seniority_level": "unknown",
            "candidate_name": None,
            "years_total_experience": None,
            "profile_summary": "",
            "errors": errors,
            "current_step": "skill_extractor",
        }
