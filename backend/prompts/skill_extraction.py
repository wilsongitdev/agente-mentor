"""
Selector dinámico de prompts para el Agente de Extracción de Habilidades.
Permite cambiar versiones de prompt para A/B testing mediante PROMPT_VERSION.
    V1: Baseline mínimo  |  V2: Elaborado  |  V3: Premium  |  V4: Real-World Tuned

Ejemplo de uso:
    $env:PROMPT_VERSION="V1"; python -m evaluations.run_eval --experiment "v1-baseline"
    $env:PROMPT_VERSION="V3"; python -m evaluations.run_eval --experiment "v3-premium"
    $env:PROMPT_VERSION="V4"; python -m evaluations.run_eval --experiment "v4-realworld"
"""
import os
from prompts.prompt_library import (
    SE_V1_SYSTEM, SE_V1_HUMAN,
    SE_V2_SYSTEM, SE_V2_HUMAN,
    SE_V3_SYSTEM, SE_V3_HUMAN,
)

# Detectar la versión deseada (por defecto V3 = producción)
_version = os.getenv("PROMPT_VERSION", "V3").upper()

_VERSIONS = {
    "V1": (SE_V1_SYSTEM, SE_V1_HUMAN),
    "V2": (SE_V2_SYSTEM, SE_V2_HUMAN),
    "V3": (SE_V3_SYSTEM, SE_V3_HUMAN),
}

SKILL_EXTRACTION_SYSTEM, SKILL_EXTRACTION_HUMAN = _VERSIONS.get(_version, _VERSIONS["V3"])
