"""
POST /api/v1/upload-cv

Accepts a PDF file, saves it locally, and runs the full multi-agent pipeline
asynchronously. Returns a session_id immediately; the client polls
GET /api/v1/learning-path/{session_id} for the result.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from config.settings import settings
from core.graph import cv_analysis_graph
from schemas.cv import CVUploadResponse
from utils.logger import logger

router = APIRouter()

# In-memory job status store (swap for Redis / DB in production)
_job_status: dict[str, dict] = {}


async def _run_pipeline(session_id: str, pdf_path: str) -> None:
    """Background task: invoke the LangGraph pipeline and cache the result."""
    _job_status[session_id] = {"status": "processing"}
    try:
        initial_state = {
            "session_id": session_id,
            "pdf_path": pdf_path,
            "errors": [],
        }
        final_state = await cv_analysis_graph.ainvoke(initial_state)

        errors = final_state.get("errors", [])
        learning_path = final_state.get("learning_path", {})

        if not learning_path:
            _job_status[session_id] = {
                "status": "failed",
                "errors": errors,
            }
        else:
            _job_status[session_id] = {
                "status": "completed",
                "learning_path": learning_path,
                "errors": errors,
            }
        logger.info("[API] Pipeline completed for session %s. Errors: %s", session_id, errors)
    except Exception as exc:
        logger.error("[API] Pipeline crashed for session %s: %s", session_id, exc)
        _job_status[session_id] = {
            "status": "failed",
            "errors": [str(exc)],
        }


@router.post(
    "/upload-cv",
    response_model=CVUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a CV PDF and start analysis",
)
async def upload_cv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF resume / CV file"),
) -> CVUploadResponse:
    # ── Validate ──────────────────────────────────────────────────────────
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported.",
        )

    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_file_size_mb} MB.",
        )

    # ── Save file ─────────────────────────────────────────────────────────
    session_id = str(uuid.uuid4())
    upload_path = Path(settings.upload_dir) / f"{session_id}.pdf"

    async with aiofiles.open(upload_path, "wb") as f:
        await f.write(content)

    logger.info("[API] Saved CV to %s (session=%s)", upload_path, session_id)

    # ── Kick off background pipeline ──────────────────────────────────────
    background_tasks.add_task(_run_pipeline, session_id, str(upload_path))

    return CVUploadResponse(
        session_id=session_id,
        filename=file.filename,
        status="processing",
        message="CV received. Analysis started – poll /learning-path/{session_id} for results.",
    )


@router.get(
    "/job-status/{session_id}",
    summary="Check pipeline job status",
)
async def get_job_status(session_id: str) -> JSONResponse:
    job = _job_status.get(session_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return JSONResponse(content=job)
