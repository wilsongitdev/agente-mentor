"""
LLM service factory.

Returns a LangChain ChatModel based on the configured provider (OpenAI or AWS Bedrock).
Supports structured output via .with_structured_output(schema).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from config.settings import settings
from utils.logger import logger


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """Return the configured chat LLM (cached singleton)."""
    provider = settings.llm_provider.lower()

    if provider == "openai":
        return _build_openai_llm()
    elif provider == "bedrock":
        return _build_bedrock_llm()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def _build_openai_llm() -> BaseChatModel:
    from langchain_openai import ChatOpenAI  # type: ignore

    logger.info("Initialising OpenAI LLM – model: %s", settings.openai_model)
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
        max_retries=3,
    )


def _build_bedrock_llm() -> BaseChatModel:
    import boto3  # type: ignore
    from langchain_aws import ChatBedrock  # type: ignore

    logger.info("Initialising AWS Bedrock LLM – model: %s", settings.bedrock_model_id)
    client = boto3.client(
        "bedrock-runtime",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )
    return ChatBedrock(
        model_id=settings.bedrock_model_id,
        client=client,
        model_kwargs={"temperature": 0.2, "max_tokens": 4096},
    )


@lru_cache(maxsize=1)
def get_embeddings() -> Any:
    """Return an embedding model for vector similarity search."""
    provider = settings.llm_provider.lower()

    if provider in ("openai", "bedrock"):
        # Use OpenAI embeddings in both cases for consistency
        # (Bedrock embedding support is optional)
        from langchain_openai import OpenAIEmbeddings  # type: ignore

        logger.info("Initialising OpenAI Embeddings – model: %s", settings.embedding_model)
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )
    raise ValueError(f"Cannot determine embeddings for provider: {provider}")
