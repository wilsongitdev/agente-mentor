"""
Servicio de Factoría LLM (LLM Service Factory)

Proporciona una interfaz unificada para instanciar diferentes modelos de chat
(OpenAI, AWS Bedrock) y modelos de embeddings. Gestiona el almacenamiento en caché
para optimizar el rendimiento y reducir las llamadas redundantes de inicialización.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from typing import Any, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from config.settings import settings
from utils.logger import logger


@lru_cache(maxsize=16)
def get_llm(
    model_id: Optional[str] = None,
    temperature: float = 0,
    max_tokens: int = 8192,
) -> BaseChatModel:
    """
    Retorna una instancia configurada de un modelo de chat (LLM).
    
    Utiliza lru_cache para evitar la re-inicialización costosa si los parámetros
    son idénticos.

    Args:
        model_id: Identificador opcional del modelo. Si es None, usa el de .env.
        temperature: Nivel de aleatoriedad (0-1).
        max_tokens: Límite máximo de tokens de salida.

    Returns:
        BaseChatModel: Instancia de LangChain configurada.
    """
    provider = settings.llm_provider.lower()
    
    if provider == "openai":
        return _build_openai_llm(model_id, temperature, max_tokens)
    elif provider == "bedrock":
        return _build_bedrock_llm(model_id, temperature, max_tokens)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


@lru_cache(maxsize=4)
def get_judge_llm() -> BaseChatModel:
    """
    Returns the LLM configured as 'judge' for LLM-as-Judge evaluations.

    Principio: el juez debe ser SIEMPRE más capaz que el agente evaluado.

    Configuración en .env:
        JUDGE_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0  (Bedrock)
        JUDGE_MODEL_ID=gpt-4o                                         (OpenAI)

    Si JUDGE_MODEL_ID no está definido, usa el mismo modelo que el agente
    (útil para desarrollo, pero no recomendado en producción).
    """
    provider = settings.llm_provider.lower()

    # Resuelve el modelo: prioriza JUDGE_MODEL_ID, si no cae al modelo del agente
    judge_model = settings.judge_model_id or None

    if judge_model:
        logger.info("Judge LLM – provider: {}, model: {}", provider, judge_model)
    else:
        logger.warning(
            "JUDGE_MODEL_ID no definido – el juez usara el mismo modelo que el agente. "
            "Define JUDGE_MODEL_ID en .env para usar un modelo superior."
        )

    # Temperatura 0 → juicios deterministicos y reproducibles
    if provider == "openai":
        return _build_openai_llm(judge_model, temperature=0.0, max_tokens=2048)
    elif provider == "bedrock":
        return _build_bedrock_llm(judge_model, temperature=0.0, max_tokens=2048)
    else:
        raise ValueError(f"Unknown LLM provider for judge: {provider}")


def _build_openai_llm(
    model_id: Optional[str], 
    temperature: float, 
    max_tokens: int
) -> BaseChatModel:
    from langchain_openai import ChatOpenAI  # type: ignore
    
    target_model = model_id or settings.openai_model
    logger.info("Building OpenAI LLM – model: {}, temp: {}", target_model, temperature)
    
    return ChatOpenAI(
        model=target_model,
        api_key=settings.openai_api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        max_retries=3,
    )


def _build_bedrock_llm(
    model_id: Optional[str], 
    temperature: float, 
    max_tokens: int
) -> BaseChatModel:
    import boto3  # type: ignore
    from langchain_aws import ChatBedrock  # type: ignore

    target_model = model_id or settings.bedrock_model_id
    logger.info("Building AWS Bedrock LLM – model: {}, temp: {}", target_model, temperature)
    
    client = boto3.client(
        "bedrock-runtime",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )
    
    return ChatBedrock(
        model_id=target_model,
        client=client,
        model_kwargs={"temperature": temperature, "max_tokens": max_tokens},
    )


@lru_cache(maxsize=1)
def get_embeddings() -> Any:
    """
    Retorna el modelo de embeddings configurado para búsqueda vectorial.
    
    Solo se mantiene una instancia en caché para todo el ciclo de vida de la app.

    Returns:
        Any: Modelo de embeddings (OpenAI o Bedrock).
    """
    provider = settings.llm_provider.lower()

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings  # type: ignore
        logger.info("Initialising OpenAI Embeddings – model: {}", settings.embedding_model)
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )

    elif provider == "bedrock":
        import boto3  # type: ignore
        from langchain_aws import BedrockEmbeddings  # type: ignore
        
        logger.info("Initialising AWS Bedrock Embeddings – model: amazon.titan-embed-text-v1")
        
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

    raise ValueError(f"Cannot determine embeddings for provider: {provider}")


# ── Vision Helpers ────────────────────────────────────────────────────────────

def encode_image_to_base64(image_path: str) -> str:
    """Read a local image and return its base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


async def extract_content_with_vision(image_path: str, prompt: str) -> str:
    """
    Utiliza un modelo con capacidad de visión para analizar una imagen.
    
    Ideal para procesar capturas de pantalla o PDFs convertidos a imagen donde
    el texto plano no es suficiente (ej: tablas complejas).

    Args:
        image_path: Ruta local del archivo de imagen.
        prompt: Instrucción para el análisis visual.

    Returns:
        str: Texto extraído o análisis resultante del LLM.
    """
    base64_image = encode_image_to_base64(image_path)
    llm = get_llm(temperature=0) # Temperatura 0 para máxima fidelidad en extracción
    
    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
            },
        ]
    )
    
    response = await llm.ainvoke([message])
    return str(response.content)
