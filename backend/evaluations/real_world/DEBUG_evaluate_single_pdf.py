"""
[DEBUG] DEBUG_evaluate_single_pdf.py
=====================================
Herramienta de diagnóstico local para evaluar un ÚNICO CV real en PDF
de forma manual y observar el flujo completo del pipeline.

⚠️  SOLO PARA DEBUGGING - No forma parte del pipeline de evaluación oficial.

Uso:
    python -m evaluations.real_world.DEBUG_evaluate_single_pdf \\
        --pdf evaluations/real_world/cvs_to_test/AI_Engineer_Wilson.pdf \\
        --objective "AI Engineer"

Para evaluación masiva oficial, usa:
    python -m evaluations.runners.run_e2e_eval
"""
import os
import sys
import asyncio
import json
import argparse
from datetime import datetime
from pathlib import Path

# --- Configurar Path para Importar Agentes y Servicios ---
# Estamos en: backend/evaluations/real_world/evaluate_pdf_cv.py
# Necesitamos: backend/
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT_DIR))

# Cargar configuraciones (debe ir antes para LangSmith)
from config.settings import settings # noqa
from utils.logger import logger

# Importar Servicios y Agentes
from services.pdf_service import extract_text_from_pdf
from agents.skill_extraction_agent import skill_extraction_node
from agents.course_matching_agent import course_matching_node
from agents.learning_path_agent import learning_path_node

# Importar Evaluador (Juez LLM)
from evaluations.evaluators.system_quality_evaluator import evaluate_mentor_quality

# Mock simple para LangSmith Schemas (evita dependencias extras si solo queremos el score)
class MockObj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

async def run_real_cv_evaluation(pdf_path: str, objective: str):
    """Ejecuta el flujo completo para un CV real en PDF."""
    
    # Validador de archivo
    if not os.path.exists(pdf_path):
        print(f"❌ Error: El archivo {pdf_path} no existe.")
        return

    start_time = datetime.now()

    print("\n" + "="*60)
    print(f"** INICIANDO EVALUACION REAL: {Path(pdf_path).name}")
    print(f"** OBJETIVO: {objective}")
    print("="*60)

    # 1. Extracción de PDF
    print("\n[1/5] Extrayendo texto del PDF...")
    try:
        cv_text = await extract_text_from_pdf(pdf_path)
        print(f"   [OK] Texto extraído ({len(cv_text)} caracteres).")
    except Exception as e:
        print(f"   [ERROR] Fallo en extracción: {e}")
        return

    # 2. Inicializar Estado
    state = {
        "session_id": f"real-test-{datetime.now().strftime('%Y%m%d-%H%M')}",
        "cv_text": cv_text,
        "professional_objective": objective,
        "errors": [],
    }

    # 3. Nodo 1: Skill Extraction
    print("\n[2/5] Agente 1: Extrayendo habilidades y perfil...")
    try:
        state.update(await skill_extraction_node(state))
        print(f"   [OK] Candidato: {state.get('candidate_name', 'N/A')}")
        print(f"   [OK] Seniority: {state.get('seniority_level', 'N/A')}")
    except Exception as e:
        print(f"   [ERROR] Fallo en Agente 1: {e}")
        return

    # 4. Nodo 2: Course Matching
    print("\n[3/5] Agente 2: Emparejando cursos (Heurística)...")
    try:
        # Forzar el uso de reranking para esta prueba real
        os.environ["USE_RERANKING"] = "true"
        state.update(await course_matching_node(state))
        print(f"   [OK] Cursos encontrados: {len(state.get('matched_courses', []))}")
    except Exception as e:
        print(f"   [ERROR] Fallo en Agente 2: {e}")
        return

    # 5. Nodo 3: Learning Path
    print("\n[4/5] Agente 3: Generando ruta de aprendizaje...")
    try:
        # Forzar V3 para mejor calidad en prueba real
        os.environ["PROMPT_VERSION_LP"] = "V3"
        state.update(await learning_path_node(state))
        lp = state.get("learning_path", {})
        print(f"   [OK] Pasos en la ruta: {len(lp.get('steps', []))}")
        print(f"   [OK] Duración estimada: {lp.get('total_duration_hours')} horas")
    except Exception as e:
        print(f"   [ERROR] Fallo en Agente 3: {e}")
        return

    # 6. Evaluación por Juez LLM (Calidad E2E)
    print("\n[5/5] Llamando al Juez Académico (Calidad E2E)...")
    try:
        # Mock de objetos de LangSmith para que el evaluador funcione
        run_mock = MockObj(outputs=state)
        example_mock = MockObj(inputs={"professional_objective": objective})
        
        eval_result = evaluate_mentor_quality(run_mock, example_mock)
        
        score = eval_result.get("score", 0.0)
        comment = eval_result.get("comment", "Sin comentarios.")
        
        print("\n" + "*" * 40)
        print(f"SCORE DE CALIDAD E2E: {score}/1.0")
        print(f"JUSTIFICACION: {comment}")
        print("*" * 40)
        
        # Guardar el score en el estado para el JSON
        state["evaluation"] = eval_result
        
    except Exception as e:
        print(f"   [WARN] No se pudo ejecutar el Juez: {e}")

    # Latencia total
    duration = (datetime.now() - start_time).total_seconds()
    print(f"\nLatencia Total: {duration:.1f}s")

    # --- Guardar Resultados ---
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"resultado_{Path(pdf_path).stem}_{timestamp}.json"
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

    print("\n" + "="*60)
    print("EVALUACION REAL COMPLETADA")
    print("="*60)
    print(f"Resultado guardado en: {output_path}")
    print(f"Proyect: {settings.langchain_project}")
    print("="*60 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evalúa un CV real en PDF mediante el flujo de Agente Mentor.")
    parser.add_argument("--pdf", type=str, required=True, help="Ruta al archivo PDF del CV.")
    parser.add_argument("--objective", type=str, required=True, help="Objetivo profesional deseado.")
    
    args = parser.parse_args()
    
    asyncio.run(run_real_cv_evaluation(args.pdf, args.objective))

