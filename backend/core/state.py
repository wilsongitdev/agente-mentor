"""
LangGraph shared state definition.

Every agent reads from and writes to this TypedDict.
Fields are Optional so each agent only populates its own section.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict, total=False):
    # ── Session ───────────────────────────────────────────────────────────
    session_id: str
    pdf_path: str
    professional_objective: str

    # ── PDF Parser output ─────────────────────────────────────────────────
    cv_text: str

    # ── Skill Extraction output ───────────────────────────────────────────
    candidate_name: Optional[str]
    seniority_level: str
    years_total_experience: Optional[float]
    current_skills: List[Dict[str, Any]]          # list of Skill dicts
    suggested_skills: List[Dict[str, Any]]        # list of SuggestedSkill dicts
    profile_summary: str

    # ── Course Matching output ────────────────────────────────────────────
    matched_courses: List[Dict[str, Any]]         # list of Course dicts

    # ── Learning Path output ──────────────────────────────────────────────
    learning_path: Dict[str, Any]                 # LearningPathResult dict

    # ── Control / Metadata ────────────────────────────────────────────────
    errors: List[str]
    current_step: str
