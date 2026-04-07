"""
GET /api/v1/learning-path/{session_id}

Devuelve la ruta de aprendizaje generada para una sesión dada.
También expone un endpoint POST para disparar el (re-)indexado de cursos manualmente.
"""

from __future__ import annotations
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import JSONResponse

from services.firebase_service import get_all_courses, get_learning_path
from services.vector_store_service import vector_store_service
from utils.logger import logger

# Importar el almacén de trabajos en memoria desde el router de CV
from api.routes.cv import _job_status

router = APIRouter()


@router.get(
    "/learning-path/{session_id}",
    summary="Obtener la ruta de aprendizaje generada para una sesión",
)
async def get_learning_path_result(session_id: str) -> JSONResponse:
    # Primero consultar el caché en memoria
    job = _job_status.get(session_id)
    if job:
        if job["status"] == "procesando":
            return JSONResponse(
                status_code=202,
                content={"status": "procesando", "message": "El análisis aún se está ejecutando..."},
            )
        if job["status"] == "fallido":
            raise HTTPException(
                status_code=500,
                detail={"status": "fallido", "errors": job.get("errors", [])},
            )
        if job["status"] == "completado":
            return JSONResponse(content=job["learning_path"])

    # Si no está en memoria, buscar en Firebase (soportar reinicios / escalado horizontal)
    lp = get_learning_path(session_id)
    if lp:
        return JSONResponse(content=lp)

    raise HTTPException(
        status_code=404,
        detail=f"No se encontró ninguna ruta de aprendizaje para la sesión '{session_id}'.",
    )


@router.post(
    "/index-courses",
    status_code=202,
    summary="Re-indexar cursos desde Firebase en el almacén vectorial",
)
async def index_courses(background_tasks: BackgroundTasks) -> JSONResponse:
    def _do_index() -> None:
        try:
            courses = get_all_courses()
            if not courses:
                logger.warning("[Index] No se encontraron cursos en Firebase.")
                return
            vector_store_service.build_index(courses)
            logger.info("[Index] Re-indexados {} cursos.", len(courses))
        except Exception as exc:
            logger.error("[Index] El indexado falló: {}", exc)

    background_tasks.add_task(_do_index)
    return JSONResponse(
        status_code=202,
        content={"message": "El indexado de cursos se ha iniciado en segundo plano."},
    )
