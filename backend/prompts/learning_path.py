"""
Selector dinámico de prompts para el Agente Generador de Rutas de Aprendizaje.
Permite cambiar versiones de prompt para A/B testing mediante PROMPT_VERSION_LP.
    V1: Mínima/Baseline | V2: Motivacional/Soft Skills | V3: Seniority-aware | V4: Real-World Tuned

Ejemplo de uso:
    $env:PROMPT_VERSION_LP="V1"; python -m evaluations.run_path_eval --experiment "LP-v1-baseline"
    $env:PROMPT_VERSION_LP="V4"; python -m evaluations.run_path_eval --experiment "LP-v4-realworld"
"""
import os
from prompts.prompt_library import (
    LP_V1_SYSTEM, LP_V1_HUMAN,
    LP_V2_SYSTEM, LP_V2_HUMAN,
    LP_V3_SYSTEM, LP_V3_HUMAN,
)

# Detectar la versión deseada (por defecto V3 = producción)
_version = os.getenv("PROMPT_VERSION_LP", "V3").upper()

_VERSIONS = {
    "V1": (LP_V1_SYSTEM, LP_V1_HUMAN),
    "V2": (LP_V2_SYSTEM, LP_V2_HUMAN),
    "V3": (LP_V3_SYSTEM, LP_V3_HUMAN),
}

LEARNING_PATH_SYSTEM, LEARNING_PATH_HUMAN = _VERSIONS.get(_version, _VERSIONS["V3"])
