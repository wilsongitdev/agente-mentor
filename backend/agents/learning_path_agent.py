"""
Agente 4: Generador de Rutas de Aprendizaje (Learning Path Generator)

Este agente toma las habilidades detectadas y los cursos filtrados (Matched Courses)
para construir una ruta de aprendizaje pedagógica, lógica y personalizada.
Utiliza un LLM para organizar los cursos en fases y generar una justificación (Rationale)
para cada paso.

Input: Estado completo del flujo de LangGraph.
Output: state["learning_path"] (Diccionario con fases, cursos, duración y resumen).
"""

from __future__ import annotations
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential

from prompts.learning_path import LEARNING_PATH_HUMAN, LEARNING_PATH_SYSTEM
from services.firebase_service import save_learning_path
from services.llm_service import get_llm
from utils.logger import logger


def _parse_llm_json(raw: str) -> dict:
    """
    Extrae y limpia el objeto JSON de la respuesta del LLM.
    
    Args:
        raw (str): Cadena de texto cruda devuelta por el LLM.
        
    Returns:
        dict: Diccionario parseado.
        
    Raises:
        ValueError: Si no se encuentra un formato JSON válido.
    """
    # Cleaning markdown and finding the JSON block
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No se encontró ningún objeto JSON en la respuesta del LLM.")
    return json.loads(match.group())


def _format_skills_list(skills: List[Dict[str, Any]]) -> str:
    """Formatea la lista de habilidades para el prompt."""
    lines = [
        f"  - {s['name']} ({s.get('level', 'desconocido')})"
        for s in skills[:20]  # limitamos para no saturar tokens
    ]
    return "\n".join(lines) if lines else "  (ninguna detectada)"


def _format_suggested_list(skills: List[Dict[str, Any]]) -> str:
    """Formatea las brechas de habilidades sugeridas para el prompt."""
    high = [s for s in skills if s.get("priority") == "high"]
    lines = [
        f"  - {s['name']}: {s.get('reason', '')}"
        for s in high[:10]
    ]
    return "\n".join(lines) if lines else "  (ninguna)"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _call_llm(prompt_kwargs: dict, model_id: Optional[str] = None) -> dict:
    """
    Realiza la llamada asíncrona al LLM para generar la ruta.
    
    Args:
        prompt_kwargs (dict): Argumentos para formatear el prompt del humano.
        model_id (str, optional): ID del modelo específico a usar.
        
    Returns:
        dict: Respuesta estructurada del LLM.
    """
    llm = get_llm(model_id=model_id)
    # Constructing the message sequence
    messages = [
        SystemMessage(content=LEARNING_PATH_SYSTEM),
        HumanMessage(content=LEARNING_PATH_HUMAN.format(**prompt_kwargs)),
    ]
    # Executing invocation
    response = await llm.ainvoke(messages)
    return _parse_llm_json(response.content)


def _build_learning_path_result(
    session_id: str,
    state: Dict[str, Any],
    llm_output: dict,
    courses_by_id: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Combina la salida del LLM con los datos completos de los cursos de Firebase."""
    steps = []
    total_hours = 0.0
    total_weeks = 0.0

    for step_data in llm_output.get("steps", []):
        course_id = step_data.get("course_id", "")
        course = courses_by_id.get(course_id)
        if not course:
            logger.warning("[LearningPath] ID de curso '{}' no encontrado – saltando.", course_id)
            continue

        duration = course.get("duration_hours") or 0
        weeks = step_data.get("estimated_weeks") or round(duration / 5, 1)
        total_hours += duration
        total_weeks += weeks

        steps.append(
            {
                "step": step_data.get("step", len(steps) + 1),
                "phase": step_data.get("phase", "Core Skills"),
                "course": course,
                "rationale": step_data.get("rationale", ""),
                "estimated_weeks": weeks,
            }
        )

    return {
        "session_id": session_id,
        "candidate_name": state.get("candidate_name"),
        "seniority_level": state.get("seniority_level", "junior"),
        "total_duration_hours": round(total_hours, 1),
        "total_estimated_weeks": round(total_weeks, 1),
        "steps": steps,
        "executive_summary": llm_output.get("executive_summary", ""),
        "current_skills": state.get("current_skills", []),
        "suggested_skills": state.get("suggested_skills", []),
    }


async def learning_path_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nodo de LangGraph: coordina la orquestación del generador de rutas.
    
    Este nodo prepara el contexto con los cursos encontrados, llama al LLM,
    y persiste el resultado final en la base de datos (Firebase).

    Args:
        state (Dict[str, Any]): Estado actual de la sesión.
        
    Returns:
        Dict[str, Any]: Estado actualizado con la ruta de aprendizaje generada.
    """
    session_id: str = state.get("session_id", "unknown")
    logger.info("[LearningPath] Generando ruta para la sesión {}", session_id)

    matched_courses: List[Dict[str, Any]] = state.get("matched_courses", [])
    errors: list = list(state.get("errors", []))

    if not matched_courses:
        error_msg = "No hay cursos disponibles para construir una ruta de aprendizaje."
        logger.warning("[LearningPath] {}", error_msg)
        errors.append(error_msg)
        return {
            "learning_path": {},
            "errors": errors,
            "current_step": "learning_path_generator",
        }

    # Mapa de búsqueda por ID
    courses_by_id = {c.get("id", ""): c for c in matched_courses}

    prompt_kwargs = {
        "candidate_name": state.get("candidate_name") or "el candidato",
        "seniority_level": state.get("seniority_level", "junior"),
        "years_experience": state.get("years_total_experience") or "N/A",
        "profile_summary": state.get("profile_summary", "Sin resumen disponible."),
        "current_skills_list": _format_skills_list(state.get("current_skills", [])),
        "suggested_skills_list": _format_suggested_list(state.get("suggested_skills", [])),
        "courses_json": json.dumps(matched_courses[:12], indent=2, ensure_ascii=False),
        "professional_objective": state.get("professional_objective") or "No especificado",
        "current_date": datetime.now().strftime("%B %Y"),
    }

    # --- DIAGNÓSTICO DE ENTRADA ---
    logger.debug("[LearningPath] Entrada -> Contexto enviado al LLM con {} cursos.", len(matched_courses[:12]))

    try:
        # Aquí puedes cambiar el modelo si quieres uno más potente para la ruta final
        llm_output = await _call_llm(prompt_kwargs)
        
        learning_path = _build_learning_path_result(
            session_id, state, llm_output, courses_by_id
        )
        
        # --- DIAGNÓSTICO DE SALIDA ---
        logger.info(
            "[LearningPath] ÉXITO. Generada ruta con {} pasos, {} horas en total.",
            len(learning_path["steps"]),
            learning_path["total_duration_hours"],
        )
        logger.debug("[LearningPath] Resumen ejecutivo generado: {}", learning_path["executive_summary"])

        # Persistir en Firebase (llamada síncrona dentro del flujo asíncrono)
        try:
            save_learning_path(session_id, learning_path)
        except Exception as fb_exc:
            logger.warning("[LearningPath] Fallo al guardar en Firebase (no crítico): {}", fb_exc)

        return {
            "learning_path": learning_path,
            "errors": errors,
            "current_step": "learning_path_generator",
        }

    except Exception as exc:
        error_msg = f"Fallo al generar la ruta de aprendizaje: {exc}"
        logger.error("[LearningPath] {}", error_msg)
        errors.append(error_msg)
        return {
            "learning_path": {},
            "errors": errors,
            "current_step": "learning_path_generator",
        }
