import os
import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path

# --- Configurar Path para Importar Agentes y Servicios ---
# Estamos en: backend/evaluations/real_world/bulk_evaluate_cvs.py
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

# Mock simple para LangSmith Schemas
class MockObj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

async def evaluate_cv(pdf_path: Path, objective: str):
    """Ejecuta el flujo E2E para un CV y devuelve el estado final."""
    print(f"\n📄 Procesando: {pdf_path.name}")
    print(f"🎯 Objetivo: {objective}")

    try:
        # 1. Extracción
        cv_text = await extract_text_from_pdf(str(pdf_path))
        
        # 2. Estado Inicial
        state = {
            "session_id": f"bulk-eval-{datetime.now().strftime('%m%d-%H%M')}-{pdf_path.stem[:10]}",
            "cv_text": cv_text,
            "professional_objective": objective,
            "errors": [],
        }

        # 3. Nodo 1: Skill Extraction
        state.update(await skill_extraction_node(state))
        
        # 4. Nodo 2: Course Matching
        os.environ["USE_RERANKING"] = "true"
        state.update(await course_matching_node(state))
        
        # 5. Nodo 3: Learning Path
        os.environ["PROMPT_VERSION_LP"] = "V3"
        state.update(await learning_path_node(state))
        
        # 6. Evaluación (Juez)
        run_mock = MockObj(outputs=state)
        example_mock = MockObj(inputs={"professional_objective": objective})
        eval_result = evaluate_mentor_quality(run_mock, example_mock)
        state["evaluation"] = eval_result
        
        print(f"   ✅ Calidad detectada: {eval_result.get('score', 0.0)}/1.0")
        return state

    except Exception as e:
        print(f"   ❌ Error procesando {pdf_path.name}: {e}")
        return None

async def run_bulk_evaluation():
    """Busca PDFs en la carpeta de prueba y los evalúa todos."""
    base_path = Path(__file__).parent
    input_dir = base_path / "cvs_to_test"
    output_dir = base_path / "results"
    output_dir.mkdir(exist_ok=True)

    if not input_dir.exists() or not list(input_dir.glob("*.pdf")):
        print(f"\n⚠️ No se encontraron PDFs en: {input_dir}")
        print("Sugerencia: Copia tus 6 CVs a esa carpeta y vuelve a ejecutar.")
        return

    pdfs = list(input_dir.glob("*.pdf"))
    print("\n" + "="*60)
    print(colored_text(f"🚀 INICIANDO EVALUACIÓN MASIVA ({len(pdfs)} archivos)", "cyan"))
    print("="*60)

    # El experimento en LangSmith se agrupará por este prefijo si se corre vía Script
    # Nota: Como usamos los nodos directamente, LangSmith registrará los rastreos individuales
    # bajo el proyecto configurado en .env
    
    results_summary = []

    for pdf in pdfs:
        # Intentar inferir objetivo del nombre del archivo o usar default
        # Ej: "Data_Engineer_Juan.pdf" -> "Data Engineer"
        clean_name = pdf.stem.replace("_", " ").replace("-", " ")
        # Si el nombre es muy corto, usamos por defecto Software Engineer
        objective = clean_name if len(clean_name) > 5 else "Software Engineer"
        
        # Preguntar al usuario si desea confirmar el objetivo (opcional, pero ayuda)
        # Como es masivo, mejor inferir o pedir al inicio. 
        # Aquí usaremos la inferencia por simplicidad para el usuario cansado.
        
        final_state = await evaluate_cv(pdf, objective)
        
        if final_state:
            results_summary.append({
                "file": pdf.name,
                "candidate": final_state.get("candidate_name", "N/A"),
                "score": final_state.get("evaluation", {}).get("score", 0.0)
            })
            
            # Guardar JSON individual
            filename = f"bulk_res_{pdf.stem}_{datetime.now().strftime('%H%M')}.json"
            with open(output_dir / filename, "w", encoding="utf-8") as f:
                json.dump(final_state, f, indent=2, ensure_ascii=False)

    print("\n" + "="*60)
    print(colored_text("✅ FIN DE EVALUACIÓN MASIVA", "green"))
    print("="*60)
    print("\nRESUMEN:")
    for res in results_summary:
        print(f" - {res['file']:<30} | {res['candidate']:<20} | Score: {res['score']}")
    
    print(f"\n📁 Resultados guardados en: {output_dir}")
    print(f"👉 Revisa tu dashboard de LangSmith en el proyecto: {settings.langchain_project}")
    print("="*60 + "\n")

def colored_text(text, color):
    # Simulación simple de colores en terminal
    colors = {"green": "\033[92m", "cyan": "\033[96m", "yellow": "\033[93m", "red": "\033[91m", "reset": "\033[0m"}
    return f"{colors.get(color, '')}{text}{colors['reset']}"

if __name__ == "__main__":
    try:
        asyncio.run(run_bulk_evaluation())
    except KeyboardInterrupt:
        print("\n\n👋 Evaluación cancelada por el usuario.")
