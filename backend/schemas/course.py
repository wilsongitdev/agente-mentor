from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class Course(BaseModel):
    id: str
    title: str
    provider: str = Field(..., description="E.g. Udemy, Coursera, Platzi, edX")
    url: Optional[str] = None
    description: str
    skills_covered: List[str] = Field(default_factory=list)
    level: str = Field(
        ..., description="beginner | intermediate | advanced"
    )
    duration_hours: Optional[float] = None
    category: str
    language: str = Field(default="es")
    rating: Optional[float] = None
    relevance_score: Optional[float] = Field(
        default=None,
        description="Computed relevance score (0-1) from semantic search",
    )
