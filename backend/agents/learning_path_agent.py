"""
Agent 4 – Learning Path Generator

Input  : full state (skills + matched_courses)
Output : state["learning_path"]  (LearningPathResult dict)
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential

from prompts.learning_path import LEARNING_PATH_HUMAN, LEARNING_PATH_SYSTEM
from services.firebase_service import save_learning_path
from services.llm_service import get_llm
from utils.logger import logger


def _parse_llm_json(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM response.")
    return json.loads(match.group())


def _format_skills_list(skills: List[Dict[str, Any]]) -> str:
    lines = [
        f"  - {s['name']} ({s.get('level', 'unknown')})"
        for s in skills[:20]  # cap for token budget
    ]
    return "\n".join(lines) if lines else "  (none detected)"


def _format_suggested_list(skills: List[Dict[str, Any]]) -> str:
    high = [s for s in skills if s.get("priority") == "high"]
    lines = [
        f"  - {s['name']}: {s.get('reason', '')}"
        for s in high[:10]
    ]
    return "\n".join(lines) if lines else "  (none)"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _call_llm(prompt_kwargs: dict) -> dict:
    llm = get_llm()
    messages = [
        SystemMessage(content=LEARNING_PATH_SYSTEM),
        HumanMessage(content=LEARNING_PATH_HUMAN.format(**prompt_kwargs)),
    ]
    response = llm.invoke(messages)
    return _parse_llm_json(response.content)


def _build_learning_path_result(
    session_id: str,
    state: Dict[str, Any],
    llm_output: dict,
    courses_by_id: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    steps = []
    total_hours = 0.0
    total_weeks = 0.0

    for step_data in llm_output.get("steps", []):
        course_id = step_data.get("course_id", "")
        course = courses_by_id.get(course_id)
        if not course:
            logger.warning("[LearningPath] Course id '%s' not found – skipping.", course_id)
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
        "seniority_level": state.get("seniority_level", "unknown"),
        "total_duration_hours": round(total_hours, 1),
        "total_estimated_weeks": round(total_weeks, 1),
        "steps": steps,
        "executive_summary": llm_output.get("executive_summary", ""),
        "current_skills": state.get("current_skills", []),
        "suggested_skills": state.get("suggested_skills", []),
    }


def learning_path_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: generate an ordered learning path via LLM.
    """
    session_id: str = state.get("session_id", "unknown")
    logger.info("[LearningPath] Generating path for session %s", session_id)

    matched_courses: List[Dict[str, Any]] = state.get("matched_courses", [])
    errors: list = list(state.get("errors", []))

    if not matched_courses:
        error_msg = "No courses available to build a learning path."
        logger.warning("[LearningPath] %s", error_msg)
        errors.append(error_msg)
        return {
            "learning_path": {},
            "errors": errors,
            "current_step": "learning_path_generator",
        }

    # Build a lookup by id for later resolution
    courses_by_id = {c.get("id", ""): c for c in matched_courses}

    prompt_kwargs = {
        "candidate_name": state.get("candidate_name") or "the candidate",
        "seniority_level": state.get("seniority_level", "mid"),
        "years_experience": state.get("years_total_experience") or "N/A",
        "profile_summary": state.get("profile_summary", "No summary available."),
        "current_skills_list": _format_skills_list(state.get("current_skills", [])),
        "suggested_skills_list": _format_suggested_list(state.get("suggested_skills", [])),
        "courses_json": json.dumps(matched_courses[:12], indent=2),  # token budget cap
    }

    try:
        llm_output = _call_llm(prompt_kwargs)
        learning_path = _build_learning_path_result(
            session_id, state, llm_output, courses_by_id
        )
        logger.info(
            "[LearningPath] Generated %d steps, %.0f hours total.",
            len(learning_path["steps"]),
            learning_path["total_duration_hours"],
        )

        # Persist to Firebase asynchronously-friendly (sync call here)
        try:
            save_learning_path(session_id, learning_path)
        except Exception as fb_exc:
            logger.warning("[LearningPath] Firebase save failed (non-critical): %s", fb_exc)

        return {
            "learning_path": learning_path,
            "errors": errors,
            "current_step": "learning_path_generator",
        }

    except Exception as exc:
        error_msg = f"Learning path generation failed: {exc}"
        logger.error("[LearningPath] %s", error_msg)
        errors.append(error_msg)
        return {
            "learning_path": {},
            "errors": errors,
            "current_step": "learning_path_generator",
        }
