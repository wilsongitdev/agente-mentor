"""
Agent 3 – Course Matching

Input  : state["current_skills"], state["suggested_skills"], state["seniority_level"]
Output : state["matched_courses"]

Strategy:
  1. Build semantic queries from skill names.
  2. Search the FAISS/Chroma vector index.
  3. Filter out courses the candidate has already mastered.
  4. Return up to MAX_COURSES deduplicated results sorted by relevance.
"""

from __future__ import annotations

from typing import Any, Dict, List

from services.vector_store_service import vector_store_service
from utils.logger import logger

MAX_COURSES = 15
K_PER_QUERY = 4

# Skills at these levels are already mastered – skip matching their courses
SKIP_LEVELS = {"advanced", "expert"}


def _build_queries(
    current_skills: List[Dict[str, Any]],
    suggested_skills: List[Dict[str, Any]],
    seniority_level: str,
) -> List[str]:
    """
    Create a diverse set of natural-language queries for the vector store.
    """
    queries: List[str] = []

    # High-priority gap skills → most important queries
    for skill in suggested_skills:
        if skill.get("priority") == "high":
            queries.append(f"course to learn {skill['name']} from scratch")
            queries.append(
                f"{skill['name']} {seniority_level} developer course"
            )

    # Current skills that are not yet mastered → deepen them
    for skill in current_skills:
        if skill.get("level") not in SKIP_LEVELS:
            queries.append(
                f"intermediate to advanced {skill['name']} course"
            )

    # Medium-priority gap skills
    for skill in suggested_skills:
        if skill.get("priority") == "medium":
            queries.append(f"learn {skill['name']} course")

    # Generic query based on seniority
    queries.append(
        f"software development {seniority_level} level career path course"
    )

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)
    return unique[:12]  # cap to avoid too many API calls


def _already_mastered_skill_names(current_skills: List[Dict[str, Any]]) -> set:
    return {
        s["name"].lower()
        for s in current_skills
        if s.get("level") in SKIP_LEVELS
    }


def course_matching_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: find relevant courses via semantic search.
    """
    logger.info(
        "[CourseMatcher] Starting for session %s", state.get("session_id")
    )

    current_skills: List[Dict[str, Any]] = state.get("current_skills", [])
    suggested_skills: List[Dict[str, Any]] = state.get("suggested_skills", [])
    seniority_level: str = state.get("seniority_level", "mid")
    errors: list = list(state.get("errors", []))

    mastered = _already_mastered_skill_names(current_skills)
    queries = _build_queries(current_skills, suggested_skills, seniority_level)

    logger.debug("[CourseMatcher] Running %d queries against vector store.", len(queries))

    try:
        raw_courses = vector_store_service.multi_query_search(
            queries, k_per_query=K_PER_QUERY
        )
    except Exception as exc:
        error_msg = f"Vector store search failed: {exc}"
        logger.error("[CourseMatcher] %s", error_msg)
        errors.append(error_msg)
        return {
            "matched_courses": [],
            "errors": errors,
            "current_step": "course_matcher",
        }

    # Filter and cap
    filtered = [
        c for c in raw_courses
        if not any(
            mastered_skill in c.get("title", "").lower()
            for mastered_skill in mastered
        )
    ][:MAX_COURSES]

    logger.info(
        "[CourseMatcher] Found %d relevant courses (after filtering).", len(filtered)
    )

    return {
        "matched_courses": filtered,
        "errors": errors,
        "current_step": "course_matcher",
    }
