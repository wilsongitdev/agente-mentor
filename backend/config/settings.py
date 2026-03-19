"""
Centralised settings loaded from environment variables via pydantic-settings.
Import `settings` anywhere in the project to access typed configuration.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ───────────────────────────────────────────────────────────────
    llm_provider: str = Field(default="openai", pattern="^(openai|bedrock)$")
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o-mini")
    aws_access_key_id: str = Field(default="")
    aws_secret_access_key: str = Field(default="")
    aws_region: str = Field(default="us-east-1")
    bedrock_model_id: str = Field(default="anthropic.claude-3-sonnet-20240229-v1:0")

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
    return Settings()


settings = get_settings()
