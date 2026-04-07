"""
Firebase Realtime Database service.

Provides:
  - get_all_courses()  → List[dict]
  - get_course(id)     → dict | None
  - save_learning_path(session_id, data)
  - get_learning_path(session_id) → dict | None
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional

from utils.logger import logger


@lru_cache(maxsize=1)
def _get_db():
    """Initialise and return the Firebase Realtime Database reference."""
    import firebase_admin  # type: ignore
    from firebase_admin import credentials, db  # type: ignore

    from config.settings import settings

    if not firebase_admin._apps:
        cred_path = settings.firebase_credentials_path
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(
                cred,
                {"databaseURL": settings.firebase_database_url},
            )
            logger.info("Firebase initialised successfully.")
        except Exception as exc:
            logger.error("Firebase initialisation failed: {}", exc)
            raise

    return db.reference("/")


# ── Courses ───────────────────────────────────────────────────────────────────

def get_all_courses() -> List[Dict[str, Any]]:
    """Fetch all courses from Firebase and return as a list of dicts."""
    try:
        ref = _get_db().child("courses")
        data: Optional[Dict[str, Any]] = ref.get()
        if not data:
            logger.warning("No courses found in Firebase.")
            return []
        courses = []
        for course_id, course_data in data.items():
            course_data["id"] = course_id
            courses.append(course_data)
        logger.info("Fetched {} courses from Firebase.", len(courses))
        return courses
    except Exception as exc:
        logger.error("Error fetching courses: {}", exc)
        return []


def get_course_by_id(course_id: str) -> Optional[Dict[str, Any]]:
    try:
        ref = _get_db().child(f"courses/{course_id}")
        data = ref.get()
        if data:
            data["id"] = course_id
        return data
    except Exception as exc:
        logger.error("Error fetching course {}: {}", course_id, exc)
        return None


def upsert_course(course_id: str, data: Dict[str, Any]) -> None:
    """Create or update a course in Firebase."""
    try:
        _get_db().child(f"courses/{course_id}").set(data)
        logger.debug("Upserted course {} in Firebase.", course_id)
    except Exception as exc:
        logger.error("Error upserting course {}: {}", course_id, exc)
        raise


# ── Learning Paths ────────────────────────────────────────────────────────────

def save_learning_path(session_id: str, data: Dict[str, Any]) -> None:
    try:
        _get_db().child(f"learning_paths/{session_id}").set(data)
        logger.info("Saved learning path for session {}.", session_id)
    except Exception as exc:
        logger.error("Error saving learning path: {}", exc)
        raise


def get_learning_path(session_id: str) -> Optional[Dict[str, Any]]:
    try:
        ref = _get_db().child(f"learning_paths/{session_id}")
        return ref.get()
    except Exception as exc:
        logger.error("Error fetching learning path {}: {}", session_id, exc)
        return None
