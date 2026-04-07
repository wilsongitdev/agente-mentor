"""
[DEBUG] DEBUG_fast_test_cv.py
==============================
Herramienta de diagnóstico rápido para probar el flujo E2E completo con
un ÚNICO archivo PDF y ver todas las métricas de calidad en consola.

⚠️  SOLO PARA DEBUGGING - No registra en LangSmith ni modifica datasets.

Uso:
    python -m evaluations.real_world.DEBUG_fast_test_cv Data_Analyst_Angel.pdf

Los PDFs disponibles están en: evaluations/real_world/cvs_to_test/

Para evaluación masiva oficial, usa:
    python -m evaluations.runners.run_e2e_eval
"""
import os
import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path

# --- Configurar path para importar módulos del proyecto ---
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Cargar configuraciones
from config.settings import settings
from utils.logger import logger

# Agentes
from services.pdf_service import extract_text_from_pdf
from agents.skill_extraction_agent import skill_extraction_node
from agents.course_matching_agent import course_matching_node
from agents.learning_path_agent import learning_path_node

# Evaluadores
from evaluations.evaluators.skill_extraction_evaluator import (
    evaluate_technical_fidelity,
    evaluate_gap_pertinence,
    evaluate_seniority_consistency,
)
from evaluations.evaluators.learning_path_evaluator import (
    evaluate_path_effectiveness,
    evaluate_logical_order,
)
from evaluations.evaluators.system_quality_evaluator import evaluate_mentor_quality

# Mock de langsmith components para ejecución local directa
class MockRun:
    def __init__(self, outputs):
        self.outputs = outputs

class MockExample:
    def __init__(self, inputs):
        self.inputs = inputs

async def test_single_cv(filename: str):
    pdf_path = Path(__file__).parent / "cvs_to_test" / filename
    if not pdf_path.exists():
        print(f"❌ Error: El archivo {filename} no existe en cvs_to_test/")
        return

    print(f"\n[CV ANALISIS] Archivo: {filename}")
    print("-" * 50)

    # 1. Extracción de texto
    cv_text = await extract_text_from_pdf(str(pdf_path))
    # Inferir objetivo: 'Data_Analyst_Angel.pdf' -> 'Data Analyst'
    objective = filename.split("_")[0] + " " + filename.split("_")[1] if "_" in filename else "Data Analyst"
    if "Angel" in objective: objective = "Data Analyst" # Limpieza rápida
    
    print(f"[OBJETIVO] Inferred: {objective}")

    # 2. Pipeline E2E
    state = {
        "session_id": f"fast-test-{datetime.now().strftime('%H%M%S')}",
        "cv_text": cv_text,
        "professional_objective": objective,
        "errors": [],
    }

    # Node 1
    print("[AGENTE 1] Extracting skills...")
    state.update(await skill_extraction_node(state))
    
    # Node 2
    print("[AGENTE 3] Searching courses...")
    state.update(await course_matching_node(state))
    
    # Node 3
    print("[AGENTE 4] Generating path...")
    state.update(await learning_path_node(state))

    # 3. Evaluación con Jueces
    print("\n[JUECES] Executing Quality Evaluators...")
    
    run = MockRun(outputs=state)
    example = MockExample(inputs={"professional_objective": objective, "cv_text": cv_text})
    
    metrics = [
        ("Fidelidad Tecnica", evaluate_technical_fidelity),
        ("Pertinencia de Brechas", evaluate_gap_pertinence),
        ("Consistencia Seniority", evaluate_seniority_consistency),
        ("Eficacia de Ruta", evaluate_path_effectiveness),
        ("Orden Logico", evaluate_logical_order),
        ("Calidad General", evaluate_mentor_quality)
    ]

    results = []
    for name, eval_fn in metrics:
        try:
            res = eval_fn(run, example)
            results.append({
                "Metrica": name,
                "Score": res["score"],
                "Comentario": res["comment"]
            })
        except Exception as e:
            results.append({
                "Metrica": name,
                "Score": 0.0,
                "Comentario": f"Error: {e}"
            })

    # 4. Mostrar Resultados
    print("\n" + "=" * 80)
    print(f"{'METRICA':<25} | {'SCORE':<7} | {'COMENTARIO'}")
    print("-" * 80)
    for r in results:
        status = "OK" if r["Score"] >= 0.8 else "WARN" if r["Score"] >= 0.5 else "FAIL"
        print(f"{r['Metrica']:<25} | {r['Score']:<7.2f} | [{status}] {r['Comentario']}")
    print("=" * 80 + "\n")

    # Mostrar la ruta generada brevemente
    lp = state.get("learning_path", {})
    print(f"[RUTA] Summary for {lp.get('candidate_name', 'Angel')}:")
    for step in lp.get("steps", []):
        print(f"  Paso {step['step']}: {step['course']['title']} ({step['course']['level']})")
    print("\n" + "-" * 50)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python fast_test_cv.py <nombre_archivo.pdf>")
    else:
        asyncio.run(test_single_cv(sys.argv[1]))
