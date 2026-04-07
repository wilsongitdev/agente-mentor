"""
Script de Evaluación Aislada para el Agente Generador de Rutas (Agent 3).

Ejecuta el flujo completo para recolectar datos reales, pero 
únicamente evalúa las métricas de diseño instruccional ("logical_order" 
y "path_effectiveness").

Uso:
    cd backend
    cd backend
    python -m evaluations.runners.run_path_eval
"""

from __future__ import annotations
import argparse
import asyncio
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.settings import settings  # noqa: F401

from langsmith import Client, evaluate
from evaluations.runners.run_e2e_eval import run_e2e_path_sync, DATASET_NAME

# Importar Evaluadores Específicos del Node 3
from evaluations.evaluators.learning_path_evaluator import evaluate_path_effectiveness, evaluate_logical_order

def run_evaluation(experiment_name: str | None = None) -> None:
    client = Client()
    if not client.has_dataset(dataset_name=DATASET_NAME):
        print(f"❌ Dataset '{DATASET_NAME}' no encontrado.")
        sys.exit(1)

    timestamp = datetime.now().strftime('%Y%m%d-%H%M')
    exp_name = experiment_name or f"agent3-path-eval-{timestamp}"
    prompt_version = os.getenv("PROMPT_VERSION_LP", "V3").upper()
    
    path_evaluators = [
        evaluate_path_effectiveness,  # Gap resolution
        evaluate_logical_order        # Chronological/Difficulty order
    ]

    print(f"\n[INICIO] Evaluacion Aislada (Agente 3 - Ruta): '{exp_name}'")
    print(f"   Dataset: {DATASET_NAME}")
    print(f"   Versión de Prompt: {prompt_version}")
    print("   Métricas a evaluar:")
    print("      1. Path Effectiveness (Alineación con Brechas)")
    print("      2. Logical Order      (Orden Pedagógico)\n")

    results = evaluate(
        run_e2e_path_sync,
        data=DATASET_NAME,
        evaluators=path_evaluators,
        experiment_prefix=exp_name,
        metadata={
            "agent_flow": "Agent3_LearningPath",
            "prompt_version": prompt_version,
            "llm_provider": settings.llm_provider,
        },
    )

    print("\n[OK] EVALUACION DEL AGENTE 3 FINALIZADA.")
    print("Ver resultados en LangSmith.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ejecuta evaluación para el Agente Generador de Rutas.")
    parser.add_argument("--experiment", type=str, default=None, help="Nombre del experimento.")
    args = parser.parse_args()
    
    run_evaluation(experiment_name=args.experiment)
