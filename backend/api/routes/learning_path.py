"""
GET /api/v1/learning-path/{session_id}

Returns the generated learning path for a given session.
Also exposes a POST endpoint to manually trigger (re-)indexing of courses.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import JSONResponse

from services.firebase_service import get_all_courses, get_learning_path
from services.vector_store_service import vector_store_service
from utils.logger import logger

# Import the in-memory job store from the cv router
from api.routes.cv import _job_status

router = APIRouter()


@router.get(
    "/learning-path/{session_id}",
    summary="Get the generated learning path for a session",
)
async def get_learning_path_result(session_id: str) -> JSONResponse:
    # First check in-memory cache
    job = _job_status.get(session_id)
    if job:
        if job["status"] == "processing":
            return JSONResponse(
                status_code=202,
                content={"status": "processing", "message": "Analysis still running…"},
            )
        if job["status"] == "failed":
            raise HTTPException(
                status_code=500,
                detail={"status": "failed", "errors": job.get("errors", [])},
            )
        if job["status"] == "completed":
            return JSONResponse(content=job["learning_path"])

    # Fall back to Firebase (supports restarts / horizontally scaled deployments)
    lp = get_learning_path(session_id)
    if lp:
        return JSONResponse(content=lp)

    raise HTTPException(
        status_code=404,
        detail=f"No learning path found for session '{session_id}'.",
    )


@router.post(
    "/index-courses",
    status_code=202,
    summary="Re-index courses from Firebase into the vector store",
)
async def index_courses(background_tasks: BackgroundTasks) -> JSONResponse:
    def _do_index() -> None:
        try:
            courses = get_all_courses()
            if not courses:
                logger.warning("[Index] No courses found in Firebase.")
                return
            vector_store_service.build_index(courses)
            logger.info("[Index] Re-indexed %d courses.", len(courses))
        except Exception as exc:
            logger.error("[Index] Indexing failed: %s", exc)

    background_tasks.add_task(_do_index)
    return JSONResponse(
        status_code=202,
        content={"message": "Course indexing started in the background."},
    )
