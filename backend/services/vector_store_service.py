"""
Servicio de almacén vectorial – similitud coseno en Python puro.

Sin dependencias de numpy, faiss ni langchain_community.
Solo usa BedrockEmbeddings (langchain_aws) + math estándar de Python.
Compatible con cualquier entorno donde funcione langchain_aws.
"""

from __future__ import annotations
import json
import math
import pickle
from pathlib import Path
from typing import Any, Dict, List, Tuple

from config.settings import settings
from utils.logger import logger


# ── Embeddings ────────────────────────────────────────────────────────────────

def _get_embedder():
    """Retorna el modelo de embeddings según el proveedor configurado."""
    provider = settings.llm_provider.lower()

    if provider == "bedrock":
        import boto3  # type: ignore
        from langchain_aws import BedrockEmbeddings  # type: ignore

        client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
        return BedrockEmbeddings(
            client=client,
            model_id="amazon.titan-embed-text-v1",
            region_name=settings.aws_region,
        )

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings  # type: ignore
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )

    raise ValueError(f"Proveedor desconocido: {provider}")


# ── Álgebra vectorial en Python puro ─────────────────────────────────────────

def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(a: List[float]) -> float:
    return math.sqrt(sum(x * x for x in a))


def _cosine(a: List[float], b: List[float]) -> float:
    denom = _norm(a) * _norm(b)
    return _dot(a, b) / denom if denom else 0.0


# ── Formato de texto de un curso ──────────────────────────────────────────────

def _course_to_text(course: Dict[str, Any]) -> str:
    skills_text = ", ".join(course.get("skills_covered", []))
    return (
        f"Título: {course.get('title', '')}\n"
        f"Descripción: {course.get('description', '')}\n"
        f"Nivel: {course.get('level', '')}\n"
        f"Categoría: {course.get('category', '')}\n"
        f"Habilidades: {skills_text}"
    )


# ── VectorStoreService ────────────────────────────────────────────────────────

class VectorStoreService:
    """
    Almacén vectorial simple basado en similitud coseno en Python puro.
    Persiste vectores y metadatos en un archivo pickle.
    """

    STORE_FILE = "vectors.pkl"

    def __init__(self) -> None:
        self._vectors: List[List[float]] = []   # embeddings normalizados
        self._courses: List[Dict[str, Any]] = [] # metadatos de cursos
        self._loaded = False

    # ── Persistencia ──────────────────────────────────────────────────────────

    def _store_path(self) -> Path:
        return Path(settings.faiss_index_path) / self.STORE_FILE

    def _save(self) -> None:
        path = self._store_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"vectors": self._vectors, "courses": self._courses}, f)
        logger.info("Almacén vectorial guardado – {} cursos en {}", len(self._courses), path)

    def _load(self) -> bool:
        path = self._store_path()
        if not path.exists():
            logger.warning("Archivo de almacén vectorial no encontrado: {}", path)
            return False
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            self._vectors = data["vectors"]
            self._courses = data["courses"]
            self._loaded = True
            logger.info(
                "Almacén vectorial cargado – {} cursos desde {}", len(self._courses), path
            )
            return True
        except Exception as exc:
            logger.error("Error cargando almacén vectorial: {}", exc)
            return False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            if not self._load():
                raise RuntimeError(
                    "Almacén vectorial no encontrado. Ejecuta: python db/seed_courses.py"
                )

    # ── Construcción del índice ───────────────────────────────────────────────

    def build_index(self, courses: List[Dict[str, Any]]) -> None:
        """Genera embeddings para cada curso y guarda el almacén."""
        logger.info("Generando embeddings para {} cursos…", len(courses))
        embedder = _get_embedder()
        texts = [_course_to_text(c) for c in courses]
        raw_vectors = embedder.embed_documents(texts)

        # Normalizar cada vector (para que coseno = dot product)
        self._vectors = [
            [x / (_norm(v) or 1.0) for x in v] for v in raw_vectors
        ]
        self._courses = courses
        self._loaded = True
        self._save()
        logger.info("Índice construido – {} vectores", len(self._vectors))

    # ── Búsqueda ──────────────────────────────────────────────────────────────

    def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retorna los k cursos más similares a la consulta."""
        self._ensure_loaded()

        embedder = _get_embedder()
        q_vec = embedder.embed_query(query)
        q_norm = _norm(q_vec)
        q_normalized = [x / (q_norm or 1.0) for x in q_vec]

        # Calcular similitud coseno con todos los vectores
        scored: List[Tuple[float, int]] = []
        for i, vec in enumerate(self._vectors):
            score = _dot(q_normalized, vec)  # vectores ya normalizados → coseno directo
            scored.append((score, i))

        # Ordenar por score descendente
        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, idx in scored[:k]:
            course = dict(self._courses[idx])
            course["relevance_score"] = round(score, 4)
            results.append(course)

        return results

    def multi_query_search(
        self, queries: List[str], k_per_query: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta múltiples consultas, deduplica por ID y ordena por relevancia.
        """
        seen_ids: set = set()
        all_courses: List[Dict[str, Any]] = []

        for query in queries:
            try:
                results = self.similarity_search(query, k=k_per_query)
                for course in results:
                    cid = course.get("id", "")
                    if cid and cid not in seen_ids:
                        seen_ids.add(cid)
                        all_courses.append(course)
            except Exception as exc:
                logger.warning(
                    "Fallo en la búsqueda vectorial para la consulta '{}': {}", query, exc
                )

        all_courses.sort(key=lambda c: c.get("relevance_score", 0), reverse=True)
        return all_courses


# Instancia única (Singleton)
vector_store_service = VectorStoreService()
