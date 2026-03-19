"""
Agent 2 – Skill Extraction

Input  : state["cv_text"]
Output : state["current_skills"], state["suggested_skills"],
         state["seniority_level"], state["candidate_name"],
         state["years_total_experience"], state["profile_summary"]
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential

from prompts.skill_extraction import SKILL_EXTRACTION_HUMAN, SKILL_EXTRACTION_SYSTEM
from services.llm_service import get_llm
from utils.logger import logger


def _parse_llm_json(raw: str) -> dict:
    """Extract the first JSON object from an LLM response string."""
    # Strip markdown code fences if present
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    # Find the first { ... } block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM response.")
    return json.loads(match.group())


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _call_llm(cv_text: str) -> dict:
    llm = get_llm()
    messages = [
        SystemMessage(content=SKILL_EXTRACTION_SYSTEM),
        HumanMessage(content=SKILL_EXTRACTION_HUMAN.format(cv_text=cv_text)),
    ]
    response = llm.invoke(messages)
    return _parse_llm_json(response.content)


def skill_extraction_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: extract skills from CV text via LLM.
    """
    logger.info(
        "[SkillExtractor] Starting for session %s", state.get("session_id")
    )

    cv_text: str = state.get("cv_text", "")
    errors: list = list(state.get("errors", []))

    if not cv_text.strip():
        error_msg = "cv_text is empty – cannot extract skills."
        logger.error("[SkillExtractor] %s", error_msg)
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
        result = _call_llm(cv_text)
        logger.info(
            "[SkillExtractor] Extracted %d current skills, %d suggestions. Seniority: %s",
            len(result.get("current_skills", [])),
            len(result.get("suggested_skills", [])),
            result.get("seniority_level", "unknown"),
        )
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
        error_msg = f"Skill extraction LLM call failed: {exc}"
        logger.error("[SkillExtractor] %s", error_msg)
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
