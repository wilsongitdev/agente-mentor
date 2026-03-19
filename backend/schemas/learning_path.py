from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

from .course import Course


class LearningPathStep(BaseModel):
    step: int
    phase: str = Field(
        ...,
        description="E.g. 'Foundations', 'Core Skills', 'Specialisation', 'Advanced'",
    )
    course: Course
    rationale: str = Field(
        ..., description="Why this course is recommended at this step"
    )
    estimated_weeks: Optional[float] = None


class LearningPathResult(BaseModel):
    session_id: str
    candidate_name: Optional[str] = None
    seniority_level: str
    total_duration_hours: float
    total_estimated_weeks: float
    steps: List[LearningPathStep] = Field(default_factory=list)
    executive_summary: str = Field(
        ..., description="High-level narrative of the recommended path"
    )
    current_skills: list = Field(default_factory=list)
    suggested_skills: list = Field(default_factory=list)
