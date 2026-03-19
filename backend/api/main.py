"""
FastAPI application entrypoint.

Run with:
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
    logger.info("CV Analyzer API starting up…")
    logger.info("LLM provider: %s", settings.llm_provider)
    logger.info("Vector store: %s", settings.vector_store_type)
    yield
    logger.info("CV Analyzer API shutting down.")


app = FastAPI(
    title="CV Analyzer API",
    description=(
        "Multi-agent platform that analyses CVs and generates personalised "
        "learning paths using LangGraph, LLMs, and semantic search."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite / CRA
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(cv_router, prefix="/api/v1", tags=["CV Upload"])
app.include_router(lp_router, prefix="/api/v1", tags=["Learning Path"])


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    return JSONResponse({"status": "ok", "version": "1.0.0"})
