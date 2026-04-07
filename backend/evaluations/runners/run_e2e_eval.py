"""
Script para la Evaluación Completa (End-to-End) del Agente Mentor.

Este script:
1. Toma tu dataset base ("Skill Extraction Quality - Agente Mentor").
2. Pasa el CV por los 3 Nodos completos:
   (Extracción -> Emparejamiento de Cursos -> Generación de Ruta).
3. Evalúa la calidad utilizando métricas simplificadas de alto impacto:
   - Data Accuracy (Fidelidad de Entrada)
   - Mentor Quality (Calidad E2E del Sistema)
4. Los costos y latencia se registran mágicamente en el dashboard de LangSmith.

Uso:
    cd backend
    python -m evaluations.runners.run_e2e_eval
"""

from __future__ import annotations
import asyncio
import os
import sys
from datetime import datetime

# ── Permitir importaciones desde backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Cargar configuraciones (debe ir primero para LangSmith)
from config.settings import settings  # noqa: F401

from langsmith import Client, evaluate
from langsmith.schemas import Run, Example

# Importar Nodos del Flujo Completo
from agents.skill_extraction_agent import skill_extraction_node
from agents.course_matching_agent import course_matching_node
from agents.learning_path_agent import learning_path_node

# Importar Evaluadores Simplificados
from evaluations.evaluators.skill_extraction_evaluator import evaluate_technical_fidelity
from evaluations.evaluators.system_quality_evaluator import evaluate_mentor_quality as evaluate_overall_mentor_quality

DATASET_NAME = os.getenv("DATASET_NAME_OVERRIDE", "Skill Extraction Quality - Agente Mentor")


# ── 1. EJECUCIÓN DEL FLUJO E2E ──────────────────────────────────────────

async def _run_e2e_path_async(inputs: dict) -> dict:
    """Wrapper asíncrono para ejecutar el Graph (Flujo de 3 agentes)"""
    state = {
        "session_id": "eval-e2e-run",
        "cv_text": inputs.get("cv_text", ""),
        "professional_objective": inputs.get("professional_objective", "Desconocido"),
        "errors": [],
    }

    # Nodo 1: Extracción de Habilidades
    state.update(await skill_extraction_node(state))
    
    # Nodo 2: Emparejamiento de Cursos FAISS/Chroma
    if state.get("current_skills") or state.get("suggested_skills"):
        state.update(await course_matching_node(state))
    
    # Nodo 3: Generación de Ruta de Aprendizaje Final
    if state.get("matched_courses"):
        state.update(await learning_path_node(state))

    # Devolvemos el estado completo para que los Evaluadores lo puedan analizar
    return state


def run_e2e_path_sync(inputs: dict) -> dict:
    """Wrapper síncrono para LangSmith."""
    return asyncio.run(_run_e2e_path_async(inputs))


# ── 2. CONFIGURACIÓN Y EJECUCIÓN EN LANGSMITH ─────────────────────────────

import argparse

# ... (otras importaciones corregidas)

def run_evaluation(experiment_name: str | None = None) -> None:
    client = Client()

    # Verificar existencia del dataset
    if not client.has_dataset(dataset_name=DATASET_NAME):
        print(f"❌ Dataset '{DATASET_NAME}' no encontrado.")
        sys.exit(1)

    timestamp = datetime.now().strftime('%Y%m%d-%H%M')
    exp_name = experiment_name or f"e2e-mentor-eval-{timestamp}"
    
    # Reducimos los evaluadores a los 2 más importantes y representativos
    e2e_evaluators = [
        evaluate_technical_fidelity,  # Asegura que entiende el CV (Data Accuracy)
        evaluate_overall_mentor_quality       # Asegura que el resultado es útil (Mentor Quality)
    ]

    print(f"\n[INICIO] Ejecucion Evaluacion End-to-End: '{exp_name}'")
    print(f"   Dataset: {DATASET_NAME}")
    print(f"   Métricas consolidadas E2E que se evaluarán:")
    print("      1. Data Accuracy          (Input Data Quality)")
    print("      2. Mentor Quality          (Output Value Delivery)")
    print("      3. Costos y Latencia       (Automático en Dashboard)\n")

    results = evaluate(
        run_e2e_path_sync,
        data=DATASET_NAME,
        evaluators=e2e_evaluators,
        experiment_prefix=exp_name,
        metadata={
            "agent_flow": "Full_E2E_Mentor",
            "llm_provider": settings.llm_provider,
            "metric_focus": "Executive_Summary",
        },
    )

    print("\n" + "=" * 60)
    print("[OK] EVALUACION E2E COMPLETADA")
    print("=" * 60)
    print("\n[TIP PARA TU PRESENTACION]:")
    print(f"Entra a: https://smith.langchain.com/")
    print(f"   Proyecto: {settings.langchain_project}")
    print(f"   Experimento: {exp_name}")
    print("\nEn la página de tu experimento en LangSmith haz un screenshot de:")
    print("   1. Avg. Score (Data Accuracy y Mentor Quality)")
    print("   2. Avg. Latency (Latencia por sesión)")
    print("   3. Cost (Costo en tokens)")
    print("Estes 3 datos son todo lo que necesitas para slide de Métricas!\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ejecuta la evaluación End-to-End del Agente Mentor.")
    parser.add_argument("--experiment", type=str, default=None, help="Nombre del experimento.")
    args = parser.parse_args()
    run_evaluation(experiment_name=args.experiment)
