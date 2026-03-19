from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class Skill(BaseModel):
    name: str
    category: str = Field(
        ...,
        description="E.g. 'Programming Language', 'Framework', 'Cloud', 'Soft Skill'",
    )
    level: str = Field(
        ...,
        description="Estimated proficiency: beginner | intermediate | advanced | expert",
    )
    years_experience: Optional[float] = Field(
        default=None, description="Estimated years of experience (if inferable)"
    )


class SuggestedSkill(BaseModel):
    name: str
    reason: str = Field(..., description="Why this skill would complement the profile")
    priority: str = Field(
        ..., description="high | medium | low"
    )


class SkillExtractionResult(BaseModel):
    candidate_name: Optional[str] = None
    seniority_level: str = Field(
        ...,
        description="Overall seniority: junior | mid | senior | lead | principal",
    )
    years_total_experience: Optional[float] = None
    current_skills: List[Skill] = Field(default_factory=list)
    suggested_skills: List[SuggestedSkill] = Field(default_factory=list)
    summary: str = Field(
        ..., description="One-paragraph professional profile summary"
    )
