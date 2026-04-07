"""
POST /api/v1/upload-cv

Acepta un archivo PDF, lo guarda localmente y ejecuta el pipeline multi-agente
de forma asíncrona. Devuelve un session_id inmediatamente; el cliente debe
consultar GET /api/v1/learning-path/{session_id} para obtener el resultado.
"""

from __future__ import annotations
import uuid
from pathlib import Path
import aiofiles
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from config.settings import settings
from core.graph import cv_analysis_graph
from schemas.cv import CVUploadResponse
from utils.logger import logger

router = APIRouter()

# Almacén de estado de trabajos en memoria (cambiar por Redis / DB en producción)
_job_status: dict[str, dict] = {}


async def _run_pipeline(session_id: str, pdf_path: str, professional_objective: str) -> None:
    """Tarea en segundo plano: invoca el pipeline de LangGraph y cachea el resultado."""
    _job_status[session_id] = {"status": "procesando"}
    try:
        initial_state = {
            "session_id": session_id,
            "pdf_path": pdf_path,
            "professional_objective": professional_objective,
            "errors": [],
        }
        # Ejecución asíncrona por pasos para progreso en tiempo real
        final_state = dict(initial_state)
        async for event in cv_analysis_graph.astream(initial_state):
            # 'event' es típicamente {node_name: {agent_updates}}
            for node_name, node_out in event.items():
                if isinstance(node_out, dict):
                    final_state.update(node_out)
                _job_status[session_id]["status"] = f"procesando_{node_name}"

        errors = final_state.get("errors", [])
        learning_path = final_state.get("learning_path", {})

        if not learning_path:
            _job_status[session_id] = {
                "status": "fallido",
                "errors": errors,
            }
        else:
            # Inyectamos el professional_objective al json final para el frontend
            if isinstance(learning_path, dict) and "professional_objective" not in learning_path:
                learning_path["professional_objective"] = final_state.get("professional_objective", "")

            _job_status[session_id] = {
                "status": "completado",
                "learning_path": learning_path,
                "errors": errors,
            }
        logger.info("[API] Pipeline completado para la sesión {}. Errores: {}", session_id, errors)
    except Exception as exc:
        logger.error("[API] El pipeline colapsó para la sesión {}: {}", session_id, exc)
        _job_status[session_id] = {
            "status": "fallido",
            "errors": [str(exc)],
        }


@router.post(
    "/upload-cv",
    response_model=CVUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Sube un CV en PDF e inicia el análisis",
)
async def upload_cv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Archivo PDF del CV / Currículum"),
    professional_objective: str = Form("No especificado", description="Posición a la que aspira"),
) -> CVUploadResponse:
    # ── Validación ────────────────────────────────────────────────────────
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Solo se admiten archivos PDF.",
        )

    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo supera el tamaño máximo de {settings.max_file_size_mb} MB.",
        )

    # ── Guardar archivo ───────────────────────────────────────────────────
    session_id = str(uuid.uuid4())
    upload_path = Path(settings.upload_dir) / f"{session_id}.pdf"

    async with aiofiles.open(upload_path, "wb") as f:
        await f.write(content)

    logger.info("[API] CV guardado en {} (sesión={})", upload_path, session_id)

    # ── Iniciar pipeline en segundo plano ─────────────────────────────────
    background_tasks.add_task(_run_pipeline, session_id, str(upload_path), professional_objective)

    return CVUploadResponse(
        session_id=session_id,
        filename=file.filename,
        status="procesando",
        message="CV recibido. Análisis iniciado – consulta /learning-path/{session_id} para ver los resultados.",
    )


@router.get(
    "/job-status/{session_id}",
    summary="Consultar el estado del trabajo del pipeline",
)
async def get_job_status(session_id: str) -> JSONResponse:
    job = _job_status.get(session_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    return JSONResponse(content=job)
