"""
Configuración Centralizada (Settings)

Esta clase gestiona la carga de variables de entorno mediante Pydantic Settings.
Proporciona validación de tipos y valores predeterminados para todos los componentes
del sistema (LLMs, Base de datos, Vector Store, Observabilidad).
"""

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Schema global de configuración del proyecto.
    
    Carga automáticamente las variables del archivo .env si existe.
    Las prioridades de carga son: Variables de entorno > Archivo .env > Valores Default.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Sandbox ───────────────────────────────────────────────────────────
    e2b_api_key: str = Field(default="", alias="E2B_API_KEY")

    # ── LLM ───────────────────────────────────────────────────────────────
    llm_provider: str = Field(default="openai", pattern="^(openai|bedrock)$")
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o-mini")
    aws_access_key_id: str = Field(default="", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    bedrock_model_id: str = Field(default="anthropic.claude-3-sonnet-20240229-v1:0", alias="BEDROCK_MODEL_ID")

    # ── LLM Juez (evaluación / LLM-as-Judge) ─────────────────────────────
    # Debe ser un modelo más potente que el agente que evalúa.
    # Por defecto apunta al mismo modelo que el agente, pero se recomienda
    # cambiarlo a un modelo superior (ej: Sonnet sobre Haiku, gpt-4o sobre gpt-4o-mini).
    judge_model_id: str = Field(default="", alias="JUDGE_MODEL_ID")

    # ── Embeddings ────────────────────────────────────────────────────────
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimension: int = Field(default=1536)

    # ── Firebase ──────────────────────────────────────────────────────────
    firebase_credentials_path: str = Field(default="./config/firebase_credentials.json")
    firebase_database_url: str = Field(default="")

    # ── Vector Store ──────────────────────────────────────────────────────
    vector_store_type: str = Field(default="faiss", pattern="^(faiss|chroma)$")
    faiss_index_path: str = Field(default="./db/faiss_index")
    chroma_persist_dir: str = Field(default="./db/chroma")

    # ── API ───────────────────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    debug: bool = Field(default=True)
    secret_key: str = Field(default="change-me-in-production")

    # ── Upload ────────────────────────────────────────────────────────────
    upload_dir: str = Field(default="./uploads")
    max_file_size_mb: int = Field(default=10)

    # ── Logging ───────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")

    # ── LangSmith (Observabilidad) ────────────────────────────────────────
    langchain_tracing_v2: str = Field(default="false")
    langchain_endpoint: str = Field(default="https://api.smith.langchain.com")
    langchain_api_key: str = Field(default="")
    langchain_project: str = Field(default="agente-mentor")

    @field_validator("upload_dir", mode="after")
    @classmethod
    def ensure_upload_dir(cls, v: str) -> str:
        Path(v).mkdir(parents=True, exist_ok=True)
        return v

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """
    Factoría para instanciar y cachear la configuración global.
    
    Inyecta las variables de LangSmith en el entorno del sistema para que 
    LangChain las detecte automáticamente al inicio.

    Returns:
        Settings: Instancia única de la clase Settings.
    """
    s = Settings()
    # Exportar vars de LangSmith al entorno de OS para que LangChain las lea
    # en el momento en que importa sus módulos internos.
    os.environ["LANGCHAIN_TRACING_V2"] = s.langchain_tracing_v2
    os.environ["LANGCHAIN_ENDPOINT"] = s.langchain_endpoint
    os.environ["LANGCHAIN_API_KEY"] = s.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = s.langchain_project
    return s


settings = get_settings()
