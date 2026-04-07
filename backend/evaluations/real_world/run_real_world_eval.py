"""
Evaluación Real-World con CVs de LinkedIn en LangSmith.

Este script:
1. Lee todos los PDFs de la carpeta 'cvs_to_test/'
2. Extrae el texto usando el pdf_service del proyecto
3. Sube los CVs como dataset en LangSmith ('Real-World-CVs-LinkedIn')
4. Ejecuta el flujo E2E completo con TODAS las 6 métricas:
   - Agente 1 (Skill Extraction):  technical_fidelity, gap_pertinence, seniority_consistency
   - Agente 3 (Learning Path):     path_effectiveness, logical_order
   - Sistema E2E:                  overall_mentor_quality

Uso:
    cd backend
    python -m evaluations.real_world.run_real_world_eval
"""
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path

# --- Configurar path para importar módulos del proyecto ---
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Cargar configuraciones primero (activa LangSmith)
from config.settings import settings  # noqa
from utils.logger import logger

from langsmith import Client, evaluate

# Agentes del flujo
from services.pdf_service import extract_text_from_pdf
from agents.skill_extraction_agent import skill_extraction_node
from agents.course_matching_agent import course_matching_node
from agents.learning_path_agent import learning_path_node

# Todos los evaluadores (6 métricas en total)
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

# ─────────────────────────────────────────────────────────────────────────────
DATASET_NAME = "Real-World-CVs-LinkedIn"
INPUT_DIR = Path(__file__).parent / "cvs_to_test"
# ─────────────────────────────────────────────────────────────────────────────


def _infer_objective(pdf_path: Path) -> str:
    """
    Intenta inferir el objetivo profesional desde el nombre del archivo.
    Ejemplo:  'DataEngineer_Juan.pdf' -> 'Data Engineer'
              'MLEngineer_Maria.pdf'  -> 'ML Engineer'
    Si no puede inferirlo, usa 'AI Engineer' como valor por defecto.
    """
    stem = pdf_path.stem  # Ejemplo: 'DataEngineer_Juan'
    parts = stem.split("_")

    # Heurística: si la primera parte tiene más de 5 letras, probablemente es el rol
    if parts and len(parts[0]) > 5:
        # Insertar espacio antes de cada letra mayúscula (CamelCase -> title case)
        import re
        role = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", parts[0])
        return role if role else "AI Engineer"

    # Fallback: usar el nombre completo del archivo
    return stem.replace("_", " ").replace("-", " ")


async def _extract_cvs_from_pdfs() -> list[dict]:
    """Lee todos los PDFs y devuelve lista de dicts {cv_text, professional_objective, filename}."""
    pdfs = sorted(INPUT_DIR.glob("*.pdf"))
    if not pdfs:
        return []

    examples = []
    print(f"\n[FILES] Extrayendo texto de {len(pdfs)} PDFs...")
    for pdf in pdfs:
        try:
            text = await extract_text_from_pdf(str(pdf))
            objective = _infer_objective(pdf)
            examples.append({
                "filename": pdf.name,
                "cv_text": text,
                "professional_objective": objective,
            })
            print(f"   [OK] {pdf.name} -> Objetivo: '{objective}' ({len(text)} chars)")
        except Exception as e:
            print(f"   [ERROR] {pdf.name}: {e}")

    return examples


def _setup_dataset(examples: list[dict]) -> bool:
    """Crea o actualiza el dataset en LangSmith con los CVs extraídos."""
    client = Client()

    if client.has_dataset(dataset_name=DATASET_NAME):
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
        print(f"\n[UPDATE] Actualizando dataset '{DATASET_NAME}' (limpiando ejemplos previos)...")
        for ex in client.list_examples(dataset_id=dataset.id):
            client.delete_example(ex.id)
    else:
        dataset = client.create_dataset(
            DATASET_NAME,
            description="CVs reales extraídos de LinkedIn para evaluación de robustez del Agente Mentor."
        )
        print(f"\n[CREATED] Dataset '{DATASET_NAME}' creado.")

    print(f"[UPLOAD] Subiendo {len(examples)} ejemplos a LangSmith...")
    for ex in examples:
        client.create_example(
            inputs={
                "cv_text": ex["cv_text"],
                "professional_objective": ex["professional_objective"],
                # filename como metadata para trazabilidad
                "filename": ex["filename"],
            },
            outputs={},  # Sin Ground Truth predefinida; el juez es auto-suficiente
            dataset_id=dataset.id,
        )
    print("   [OK] Dataset listo en LangSmith.")
    return True


# ── Función pipeline E2E (la que LangSmith evaluará) ──────────────────────────

async def _run_full_pipeline_async(inputs: dict) -> dict:
    """Ejecuta el flujo completo de 3 agentes para un CV."""
    state = {
        "session_id": f"rw-{datetime.now().strftime('%m%d-%H%M%S')}",
        "cv_text": inputs.get("cv_text", ""),
        "professional_objective": inputs.get("professional_objective", "AI Engineer"),
        "errors": [],
    }

    # Usar versiones de prompt desde el entorno (V3 por defecto si no se especifica)
    use_rerank = os.getenv("USE_RERANKING", "true").lower() == "true"
    prompt_v = os.getenv("PROMPT_VERSION", "V3")
    prompt_lp_v = os.getenv("PROMPT_VERSION_LP", "V3")
    
    logger.info(f"[PIPELINE] Iniciando Pipeline con SE_{prompt_v} y LP_{prompt_lp_v} (Reranking: {use_rerank})")

    # Agente 1: Extracción de habilidades
    state.update(await skill_extraction_node(state))

    # Agente 2: Matching de cursos (sólo si hay skills)
    if state.get("current_skills") or state.get("suggested_skills"):
        state.update(await course_matching_node(state))

    # Agente 3: Generación de ruta (sólo si hay cursos)
    if state.get("matched_courses"):
        state.update(await learning_path_node(state))

    return state


def run_full_pipeline_sync(inputs: dict) -> dict:
    """Wrapper síncrono requerido por langsmith.evaluate()."""
    return asyncio.run(_run_full_pipeline_async(inputs))


# ── Ejecución Principal ────────────────────────────────────────────────────────

def run_evaluation(experiment_name: str | None = None):
    """Orquesta la evaluación completa de CVs reales."""

    # 0. Verificar carpeta
    if not INPUT_DIR.exists():
        INPUT_DIR.mkdir(parents=True)
        print(f"📁 Carpeta creada: {INPUT_DIR}")
        print("ℹ️  Copia tus 6 PDFs de LinkedIn allí y vuelve a ejecutar.")
        return

    # 1. Extraer CVs de los PDFs
    examples = asyncio.run(_extract_cvs_from_pdfs())
    if not examples:
        print(f"\n⚠️  No se encontraron PDFs en: {INPUT_DIR}")
        print("ℹ️  Copia tus 6 PDFs de LinkedIn allí con formato: 'RolObjetivo_Nombre.pdf'")
        return

    # 2. Crear/actualizar dataset en LangSmith
    _setup_dataset(examples)

    # 3. Definir todos los evaluadores (las 6 métricas)
    ALL_EVALUATORS = [
        # Agente 1 — Extracción de habilidades
        evaluate_technical_fidelity,    # ¿Extracción sin alucinaciones?
        evaluate_gap_pertinence,        # ¿Sugerencias relevantes al objetivo?
        evaluate_seniority_consistency, # ¿Nivel de seniority correcto?
        # Agente 3 — Ruta de aprendizaje
        evaluate_path_effectiveness,    # ¿Los cursos cubren las brechas?
        evaluate_logical_order,         # ¿Orden pedagógico correcto?
        # Sistema E2E
        evaluate_mentor_quality,        # ¿La ruta final es útil en conjunto?
    ]

    # 4. Ejecutar evaluación con LangSmith
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    exp_name = experiment_name or f"real-world-linkedin-{timestamp}"

    print(f"\n[INICIO] Iniciando evaluación completa en LangSmith...")
    print(f"   Experimento: '{exp_name}'")
    print(f"   Métricas: {[e.__name__ for e in ALL_EVALUATORS]}\n")

    evaluate(
        run_full_pipeline_sync,
        data=DATASET_NAME,
        evaluators=ALL_EVALUATORS,
        experiment_prefix=exp_name,
        metadata={
            "source": "Real LinkedIn PDFs",
            "cvs_count": len(examples),
            "run_date": timestamp,
            "prompt_version_lp": "V3",
        },
    )

    print("\n" + "=" * 65)
    print("[OK] EVALUACIÓN REAL-WORLD COMPLETADA")
    print("=" * 65)
    print(f"\n[INFO] Revisa los resultados en LangSmith:")
    print(f"   https://smith.langchain.com/")
    print(f"   Dataset:     {DATASET_NAME}")
    print(f"   Experimento: {exp_name}")
    print(f"\n[TIP] Para generar la gráfica con conclusiones, ejecuta:")
    print(f"   python -m evaluations.reports.generate_real_world_report")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluación Real-World con CVs de LinkedIn.")
    parser.add_argument("--experiment", type=str, default=None, help="Nombre opcional del experimento.")
    args = parser.parse_args()
    
    run_evaluation(experiment_name=args.experiment)
