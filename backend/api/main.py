"""
Punto de entrada de la aplicación FastAPI.

Ejecutar con:
    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes.cv import router as cv_router
from api.routes.learning_path import router as lp_router
from config.settings import settings
from utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando la API de Agente Mentor...")
    logger.info("Proveedor de LLM: {}", settings.llm_provider)
    logger.info("Almacén vectorial: {}", settings.vector_store_type)
    yield
    logger.info("Apagando la API de Agente Mentor.")


app = FastAPI(
    title="API Agente Mentor",
    description=(
        "Plataforma multi-agente que analiza CVs y genera rutas de "
        "aprendizaje personalizadas usando LangGraph, LLMs y búsqueda semántica."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS (Permitir peticiones desde el frontend) ──────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite / CRA
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rutas ────────────────────────────────────────────────────────────────────
app.include_router(cv_router, prefix="/api/v1", tags=["Subida de CV"])
app.include_router(lp_router, prefix="/api/v1", tags=["Ruta de Aprendizaje"])


# ── Comprobación de salud (Health check) ──────────────────────────────────────
@app.get("/health", tags=["Salud"])
async def health_check() -> JSONResponse:
    return JSONResponse({"status": "ok", "version": "1.0.0"})
