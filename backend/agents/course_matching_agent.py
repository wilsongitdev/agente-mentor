"""
Agente 3: Emparejador de Cursos (Course Matching Agent)

Este agente se encarga de buscar y filtrar los cursos más relevantes para el usuario
basándose en sus habilidades actuales, brechas detectadas y seniority.
Utiliza búsqueda semántica (FAISS/Chroma) y un re-ranking heurístico para optimizar
la calidad de los resultados sin costo adicional de LLM.

Estrategia:
  1. Construir consultas semánticas diversificadas.
  2. Buscar en el almacén de vectores (Vector Store).
  3. Aplicar filtrado de habilidades ya dominadas.
  4. Re-puntuación (Reranking) basada en heurística de relevancia y pedagogía.
"""

from __future__ import annotations
from typing import Any, Dict, List
import json

from services.vector_store_service import vector_store_service
from utils.logger import logger

MAX_FAISS_COURSES = 30
MAX_RERANKED_COURSES = 8
K_PER_QUERY = 5

# Las habilidades en estos niveles se consideran dominadas: saltamos la búsqueda de cursos para ellas
SKIP_LEVELS = {"advanced", "expert"}


def _build_queries(
    current_skills: List[Dict[str, Any]],
    suggested_skills: List[Dict[str, Any]],
    seniority_level: str,
    professional_objective: str,
) -> List[str]:
    """
    Construye una lista de consultas de búsqueda diversificadas.
    
    Genera queries para habilidades sugeridas (brechas) y habilidades actuales
    que necesitan ser profundizadas, integrando el rol profesional.

    Args:
        current_skills: Lista de habilidades que el usuario ya posee.
        suggested_skills: Lista de habilidades recomendadas (brechas).
        seniority_level: Nivel de experiencia del candidato.
        professional_objective: Meta profesional del usuario.

    Returns:
        List[str]: Lista de cadenas de texto para búsqueda semántica.
    """
    queries: List[str] = []
    
    contextual_role = f" para perfil de {professional_objective}" if professional_objective and professional_objective != "No especificado" else ""

    # Brechas de habilidades de alta prioridad → consultas más importantes
    for skill in suggested_skills:
        if skill.get("priority") == "high":
            queries.append(f"curso para aprender {skill['name']} desde cero{contextual_role}")
            queries.append(
                f"curso de {skill['name']} para desarrollador nivel {seniority_level}{contextual_role}"
            )

    # Habilidades actuales que no han sido dominadas → profundizarlas
    for skill in current_skills:
        if skill.get("level") not in SKIP_LEVELS:
            queries.append(
                f"curso de {skill['name']} nivel intermedio a avanzado{contextual_role}"
            )

    # Brechas de habilidades de prioridad media
    for skill in suggested_skills:
        if skill.get("priority") == "medium":
            queries.append(f"aprender curso de {skill['name']}{contextual_role}")

    # Consulta genérica basada en seniority y objetivo
    if contextual_role:
        queries.append(f"curso de formación integral para ser {professional_objective}")
        queries.append(f"curso avanzado nivel {seniority_level} para {professional_objective}")
    else:
        queries.append(
            f"curso de trayectoria profesional nivel {seniority_level} en desarrollo de software"
        )

    # Eliminar duplicados manteniendo el orden
    seen = set()
    unique = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)
    return unique[:12]  # limitamos para evitar demasiadas llamadas a la API


def _already_mastered_skill_names(current_skills: List[Dict[str, Any]]) -> set:
    """Devuelve un conjunto de nombres de habilidades que ya se dominan."""
    return {
        s["name"].lower()
        for s in current_skills
        if s.get("level") in SKIP_LEVELS
    }


def _heuristic_rerank(
    raw_courses: List[Dict[str, Any]],
    current_skills: List[Dict[str, Any]],
    suggested_skills: List[Dict[str, Any]],
    seniority_level: str
) -> List[Dict[str, Any]]:
    """
    Re-puntuación Heurística de cursos (Heuristic Scoring).
    
    Aplica pesos a los cursos según coincidan con las brechas críticas (Skills Gaps),
    el nivel del curso vs seniority y criterios pedagógicos.
    """
    if not raw_courses:
        return []
        
    scored_courses = []
    
    # Extraemos nombres para match rápido
    suggested_names = [s["name"].lower() for s in suggested_skills]
    
    # Mapeo de niveles para scoring de seniority
    level_map = {
        "junior": "beginner",
        "mid": "intermediate",
        "senior": "advanced",
        "lead": "advanced",
        "principal": "advanced"
    }
    target_level = level_map.get(seniority_level.lower(), "beginner")

    # Palabras clave de fundamentos técnicos reales (Pilares de Datos/IA)
    domain_fundamentals = ["pandas", "numpy", "sql", "matplotlib", "seaborn", "estadística", "math", "analysis"]
    
    # Herramientas de ofimática o bases genéricas (para penalizar en perfiles Senior)
    generic_basics = ["excel", "word", "outlook", "powerpoint", "internet", "niños", "kids", "computer basics"]
    
    # Palabras clave de cursos integrales (que cubren de básico a avanzado)
    comprehensive_keywords = ["completo", "desde cero", "full", "bootcamp", "integral", "all-in-one", "guide"]

    for course in raw_courses:
        title = course.get("title", "").lower()
        description = course.get("description", "").lower()
        skills = [s.lower() for s in course.get("skills_covered", [])]
        course_level = course.get("level", "intermediate").lower()
        
        score = 0
        is_high_priority = False
        
        # 1. REGLA DE EFICACIA (Exact Match de Brechas) -> Mucho Peso (+15)
        for gap in suggested_skills:
            gap_name = gap["name"].lower()
            if gap_name in title or gap_name in skills:
                score += 15  # Incrementado para asegurar relevancia Core
                if gap.get("priority") == "high":
                    is_high_priority = True
            elif gap_name in description:
                score += 5
        
        # 2. REGLA DE NIVEL Y SENIORITY (FLEXIBLE Y GENERALIZABLE)
        is_senior_profile = seniority_level.lower() in ["senior", "lead", "principal"]
        is_comprehensive = any(ck in title for ck in comprehensive_keywords)
        is_generic_basic = any(gb in title or gb in skills for gb in generic_basics)
        is_domain_fundamental = any(df in title or df in skills for df in domain_fundamentals)
        
        if course_level == target_level:
            score += 10
            
        if seniority_level.lower() == "junior" and course_level == "advanced":
            if is_comprehensive:
                score += 5
            elif is_high_priority:
                score -= 5
            else:
                score -= 15
        
        if is_senior_profile:
            if is_generic_basic:
                score -= 25  # Penalización fuerte: Un Senior Dev NO necesita 'Excel básico' o 'Conceptos de PC'
            elif course_level == "beginner" and not is_domain_fundamental:
                score -= 12  # Cursos de nivel principiante que no sean de dominio técnico real
                
        # 3. REGLA PEDAGÓGICA (Solo para fundamentos de dominio real)
        if is_domain_fundamental:
            score += 8  # Solo bonificar bases reales (Pandas/SQL), no cualquier 'intro'
            
        scored_courses.append((score, course))
        
    # Ordenar por puntaje (descendente)
    scored_courses.sort(key=lambda x: x[0], reverse=True)
    
    return [c for score, c in scored_courses]


async def course_matching_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nodo de LangGraph: Orquesta la búsqueda y el filtrado de cursos.
    
    Realiza la multi-consulta, aplica el re-ranking (si está activo)
    y gestiona los errores del almacén de vectores.

    Args:
        state: Estado actual de la sesión.

    Returns:
        Dict[str, Any]: Estado actualizado con la lista de matched_courses.
    """
    session_id = state.get("session_id", "unknown")
    logger.info("[CourseMatcher] Iniciando búsqueda para la sesión {}", session_id)

    current_skills: List[Dict[str, Any]] = state.get("current_skills", [])
    suggested_skills: List[Dict[str, Any]] = state.get("suggested_skills", [])
    seniority_level: str = state.get("seniority_level", "junior")
    professional_objective: str = state.get("professional_objective", "No especificado")
    errors: list = list(state.get("errors", []))

    mastered = _already_mastered_skill_names(current_skills)
    queries = _build_queries(current_skills, suggested_skills, seniority_level, professional_objective)

    # --- DIAGNÓSTICO DE ENTRADA ---
    logger.debug("[CourseMatcher] Ejecutando {} consultas contra el almacén de vectores.", len(queries))
    logger.debug("[CourseMatcher] Consultas: {}", queries)

    try:
        raw_courses = vector_store_service.multi_query_search(
            queries, k_per_query=K_PER_QUERY
        )
    except Exception as exc:
        error_msg = f"Fallo en la búsqueda del almacén de vectores: {exc}"
        logger.error("[CourseMatcher] {}", error_msg)
        errors.append(error_msg)
        return {
            "matched_courses": [],
            "errors": errors,
            "current_step": "course_matcher",
        }

    # Filtrar por habilidades dominadas y limitar cantidad (FAISS amplio)
    filtered = [
        c for c in raw_courses
        if not any(
            mastered_skill in c.get("title", "").lower()
            for mastered_skill in mastered
        )
    ][:MAX_FAISS_COURSES]

    logger.debug("[CourseMatcher] FAISS devolvió {} cursos.", len(filtered))

    # --- FEATURE FLAG: RE-RANKING ---
    import os
    use_reranking = os.getenv("USE_RERANKING", "true").lower() == "true"
    
    if use_reranking:
        logger.debug("[CourseMatcher] Iniciando Re-Ranking Heurístico (Score-Based)...")
        # El algoritmo heurístico devuelve directamente la lista de cursos ya puntuados y ordenados
        final_courses = _heuristic_rerank(
            filtered, current_skills, suggested_skills, seniority_level
        )[:MAX_RERANKED_COURSES]
    else:
        logger.debug("[CourseMatcher] Re-Ranking DESACTIVADO. Usando resultados crudos de FAISS.")
        final_courses = filtered[:MAX_RERANKED_COURSES]

    # --- DIAGNÓSTICO DE SALIDA ---
    logger.info(
        "[CourseMatcher] Éxito. FAISS: {} -> ReRanked: {} cursos.", len(filtered), len(final_courses)
    )
    if final_courses:
        logger.debug("[CourseMatcher] Selección final (ReRanked): {}", [c.get("title") for c in final_courses])

    return {
        "matched_courses": final_courses,
        "errors": errors,
        "current_step": "course_matcher",
    }
