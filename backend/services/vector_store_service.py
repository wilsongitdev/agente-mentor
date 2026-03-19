"""
Vector store service – wraps FAISS or Chroma.

Responsibilities:
  - Build / load an index from course documents
  - Perform semantic similarity search given a list of skill queries
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document

from config.settings import settings
from services.llm_service import get_embeddings
from utils.logger import logger

# ── FAISS helpers ─────────────────────────────────────────────────────────────

def _load_faiss(index_path: str):
    from langchain_community.vectorstores import FAISS  # type: ignore

    if Path(index_path).exists():
        logger.info("Loading existing FAISS index from %s", index_path)
        return FAISS.load_local(
            index_path,
            get_embeddings(),
            allow_dangerous_deserialization=True,
        )
    return None


def _build_faiss(documents: List[Document], index_path: str):
    from langchain_community.vectorstores import FAISS  # type: ignore

    logger.info("Building FAISS index with %d documents…", len(documents))
    store = FAISS.from_documents(documents, get_embeddings())
    Path(index_path).mkdir(parents=True, exist_ok=True)
    store.save_local(index_path)
    logger.info("FAISS index saved to %s", index_path)
    return store


# ── Chroma helpers ────────────────────────────────────────────────────────────

def _load_or_build_chroma(documents: Optional[List[Document]], persist_dir: str):
    from langchain_community.vectorstores import Chroma  # type: ignore

    if documents:
        logger.info("Building Chroma collection with %d documents…", len(documents))
        store = Chroma.from_documents(
            documents,
            get_embeddings(),
            persist_directory=persist_dir,
        )
        store.persist()
        return store

    logger.info("Loading existing Chroma collection from %s", persist_dir)
    return Chroma(
        persist_directory=persist_dir,
        embedding_function=get_embeddings(),
    )


# ── Document builder ──────────────────────────────────────────────────────────

def courses_to_documents(courses: List[Dict[str, Any]]) -> List[Document]:
    """Convert course dicts to LangChain Documents for embedding."""
    docs = []
    for course in courses:
        skills_text = ", ".join(course.get("skills_covered", []))
        content = (
            f"Title: {course.get('title', '')}\n"
            f"Description: {course.get('description', '')}\n"
            f"Level: {course.get('level', '')}\n"
            f"Category: {course.get('category', '')}\n"
            f"Skills: {skills_text}"
        )
        docs.append(
            Document(
                page_content=content,
                metadata={
                    "id": course.get("id", ""),
                    "title": course.get("title", ""),
                    "provider": course.get("provider", ""),
                    "level": course.get("level", ""),
                    "category": course.get("category", ""),
                    "duration_hours": course.get("duration_hours", 0),
                    "url": course.get("url", ""),
                    "rating": course.get("rating", 0),
                    "skills_covered": json.dumps(course.get("skills_covered", [])),
                },
            )
        )
    return docs


# ── Public API ────────────────────────────────────────────────────────────────

class VectorStoreService:
    def __init__(self) -> None:
        self._store = None

    def _get_store(self):
        if self._store is None:
            self._store = self._load_store()
        return self._store

    def _load_store(self):
        vtype = settings.vector_store_type.lower()
        if vtype == "faiss":
            store = _load_faiss(settings.faiss_index_path)
            if store is None:
                raise RuntimeError(
                    "FAISS index not found. Run `python db/seed_courses.py` first."
                )
            return store
        elif vtype == "chroma":
            return _load_or_build_chroma(None, settings.chroma_persist_dir)
        raise ValueError(f"Unknown vector store type: {vtype}")

    def build_index(self, courses: List[Dict[str, Any]]) -> None:
        """(Re-)build the vector index from a list of course dicts."""
        documents = courses_to_documents(courses)
        vtype = settings.vector_store_type.lower()
        if vtype == "faiss":
            self._store = _build_faiss(documents, settings.faiss_index_path)
        elif vtype == "chroma":
            self._store = _load_or_build_chroma(documents, settings.chroma_persist_dir)
        else:
            raise ValueError(f"Unknown vector store type: {vtype}")

    def similarity_search(
        self,
        query: str,
        k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Return top-k course metadata dicts for a given query string."""
        store = self._get_store()
        results = store.similarity_search_with_relevance_scores(query, k=k)
        courses = []
        for doc, score in results:
            meta = dict(doc.metadata)
            meta["description"] = doc.page_content
            meta["relevance_score"] = round(float(score), 4)
            if "skills_covered" in meta:
                try:
                    meta["skills_covered"] = json.loads(meta["skills_covered"])
                except Exception:
                    pass
            courses.append(meta)
        return courses

    def multi_query_search(
        self,
        queries: List[str],
        k_per_query: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Run multiple queries and deduplicate results by course id.
        Returns courses sorted by relevance_score descending.
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
                logger.warning("Vector search failed for query '%s': %s", query, exc)

        all_courses.sort(key=lambda c: c.get("relevance_score", 0), reverse=True)
        return all_courses


# Singleton
vector_store_service = VectorStoreService()
