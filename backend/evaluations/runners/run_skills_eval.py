"""
Ejecución de la Evaluación LLM-as-Judge en LangSmith.

Este script:
1. Toma el dataset "Skill Extraction Quality - Agente Mentor" creado por dataset_builder.py
2. Ejecuta el agente de extracción de skills para cada ejemplo del dataset
3. Pasa los resultados a los 4 evaluadores LLM-as-Judge
4. Sube los scores a LangSmith para que los puedas ver en el dashboard

Uso:
    cd backend
    python -m evaluations.runners.run_skills_eval

    # Para comparar versiones de prompts:
    python -m evaluations.runners.run_skills_eval --experiment "prompt-v2-con-evidencia"
"""

from __future__ import annotations
import asyncio
import argparse
import sys
import os
from datetime import datetime

# ── Permitir importaciones desde backend ─────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# IMPORTANTE: settings debe cargarse PRIMERO para activar las variables de LangSmith
from config.settings import settings  # noqa: F401

from langsmith import Client, evaluate
from langsmith.schemas import Example, Run

from evaluations.evaluators.skill_extraction_evaluator import ALL_EVALUATORS
from agents.skill_extraction_agent import skill_extraction_node

DATASET_NAME = os.getenv("DATASET_NAME_OVERRIDE", "Skill Extraction Quality - Agente Mentor")


# ── Función target (la que LangSmith evaluará) ───────────────────────────────

async def _run_skill_extraction_async(inputs: dict) -> dict:
    """
    Wrapper async del agente de extracción de skills.
    Convierte las inputs del dataset al formato de estado de LangGraph.
    """
    state = {
        "session_id": "eval-run",
        "cv_text": inputs.get("cv_text", ""),
        "professional_objective": inputs.get("professional_objective", "No especificado"),
        "errors": [],
    }
    result = await skill_extraction_node(state)
    return result


def run_skill_extraction(inputs: dict) -> dict:
    """Wrapper síncrono para que LangSmith pueda ejecutar el agente."""
    return asyncio.run(_run_skill_extraction_async(inputs))


# ── Función principal de evaluación ──────────────────────────────────────────

def run_evaluation(experiment_name: str | None = None) -> None:
    """
    Ejecuta la evaluación completa y sube los resultados a LangSmith.

    Args:
        experiment_name: Nombre del experimento. Si None, se genera automáticamente
                         con la fecha/hora actual para facilitar la comparación.
    """
    client = Client()

    # Verificar que el dataset existe
    if not client.has_dataset(dataset_name=DATASET_NAME):
        print(f"❌ Dataset '{DATASET_NAME}' no encontrado.")
        print("   Ejecúta primero: python -m evaluations.dataset_builder")
        sys.exit(1)

    # Nombre del experimento para comparar en el dashboard
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    exp_name = experiment_name or f"skill-extraction-eval-{timestamp}"

    print(f"[INICIO] Evaluacion: '{exp_name}'")
    print(f"   Dataset: {DATASET_NAME}")
    print(f"   Evaluadores: {[e.__name__ for e in ALL_EVALUATORS]}")
    print()

    # ── Ejecutar evaluación con LangSmith ────────────────────────────────────
    results = evaluate(
        run_skill_extraction,           # ← El agente que evaluamos
        data=DATASET_NAME,              # ← El dataset que creamos
        evaluators=ALL_EVALUATORS,      # ← Los 4 jueces LLM
        experiment_prefix=exp_name,     # ← Nombre en el dashboard
        metadata={
            "agent": "skill_extraction_node",
            "prompt_version": experiment_name or "default",
            "llm_provider": settings.llm_provider,
            "model": settings.openai_model if settings.llm_provider == "openai" else settings.bedrock_model_id,
        },
    )

    # ── Mostrar resumen en consola ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("[OK] EVALUACION COMPLETADA")
    print("=" * 60)

    try:
        # Intentar mostrar resumen de scores (si la versión de langsmith lo soporta)
        df = results.to_pandas()
        metrics = ["technical_fidelity", "gap_pertinence", "seniority_consistency"]
        print("\nSCORES PROMEDIO:")
        for metric in metrics:
            col = f"feedback.{metric}"
            if col in df.columns:
                avg = df[col].mean()
                bar = "█" * int(avg * 10) + "░" * (10 - int(avg * 10))
                print(f"  {metric:<28} [{bar}]  {avg:.2f}")
    except Exception:
        # Si falla el resumen, no es crítico
        pass

    print(f"\n[INFO] Ver resultados en: https://smith.langchain.com/")
    print(f"   Proyecto: {settings.langchain_project}")
    print(f"   Experimento: {exp_name}")
    print()
    print("[TIP] Compara este experimento con el anterior cambiando el prompt")
    print("      en backend/prompts/skill_extraction.py y ejecutando de nuevo.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ejecuta la evaluación LLM-as-Judge para el Agente de Extracción de Skills."
    )
    parser.add_argument(
        "--experiment",
        type=str,
        default=None,
        help="Nombre del experimento (ej: 'prompt-v2-con-evidencia'). "
             "Si no se especifica, se usa la fecha/hora actual.",
    )
    args = parser.parse_args()
    run_evaluation(experiment_name=args.experiment)
