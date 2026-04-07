"""
Evaluador de Calidad de Sistema (E2E) para el Agente Mentor.
Mide la eficacia del sistema completo comparando el perfil inicial con la recomendación final.

MÉTRICA PRINCIPAL:
1. overall_mentor_quality (Sistema E2E)
   Evalúa si la ruta de aprendizaje generada es coherente, lógica 
   y orientada al objetivo profesional del candidato.
"""

from __future__ import annotations
import json
import os
import sys

# ── Permitir importaciones desde el directorio raíz de backend ────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langsmith.schemas import Example, Run
from evaluations.evaluators.skill_extraction_evaluator import _build_judge_chain, _extract_score_and_reason

# ─────────────────────────────────────────────────────────────────────────────
# MÉTRICA: CALIDAD DEL MENTOR (Mentor Quality - E2E)
# ─────────────────────────────────────────────────────────────────────────────

_MENTOR_QUALITY_SYSTEM = """\
Eres un Director Académico y Mentor de Carrera (Career Coach) experto.
Tu misión es auditar una "Ruta de Aprendizaje" generada por un sistema de IA (Mentor AI) para un candidato.

Para que el sistema sea calificado como de "Alta Calidad" (High Quality), debe:
1. ALIGNMENT (Alineación): Responder directamente al "Professional Objective" del candidato.
2. LOGIC (Coherencia): Tener un orden lógico (ej. no sugerir frameworks avanzados antes que las bases).
3. FEASIBILITY (Viabilidad): Asignar tiempos de estudio razonables y ser realista según el seniority detectado.

FALLOS CRÍTICOS (Score 0.0 - 0.3):
- La ruta sugiere cursos que no tienen nada que ver con el objetivo.
- Recomienda cosas básicas a un perfil Senior, o cosas avanzadísimas a un perfil sin bases.
- El orden es completamente ilógico.

SCORING SCALE:
- 1.0 → Exceptional: Realistic, perfectly ordered, and direct to the professional goal.
- 0.8 → High Quality: Very good, small details could be improved in order or course selection.
- 0.5 → Basic/Generic: Mediocre value, some logic or level mismatches.
- 0.2 → Poor: Irrelevant courses or completely wrong level.
- 0.0 → Critical Failure: The system failed to provide a useful path for the given input.

Responde ÚNICAMENTE con este JSON (sin markdown, sin texto extra):
{{"score": <número entre 0.0 y 1.0>, "reason": "<Explicación corta en español justificando la nota>"}}
"""

def evaluate_mentor_quality(run: Run, example: Example) -> dict:
    """
    Evalúa la calidad integral del sistema (End-to-End).
    Analiza el resultado final (learning_path) contra el ingreso (inputs).
    """
    professional_objective = (example.inputs or {}).get("professional_objective", "Objetivo Desconocido")
    
    # run.outputs contiene el estado final del flujo
    learning_path = (run.outputs or {}).get("learning_path", {})
    
    if not learning_path or not learning_path.get("steps"):
        return {
            "key": "overall_mentor_quality",
            "score": 0.0,
            "comment": "CRITICAL FAILURE: No learning path steps were generated."
        }

    candidate_name = learning_path.get("candidate_name", "Candidato")
    seniority_level = learning_path.get("seniority_level", "unknown")
    total_duration = learning_path.get("total_duration_hours", 0)
    
    # Resumen simplificado de la ruta para el Juez
    ruta_resumida = []
    for step in learning_path.get("steps", []):
        course = step.get("course", {})
        ruta_resumida.append({
            "step_no": step.get("step"),
            "phase": step.get("phase"),
            "course": course.get("title", "No Title"),
            "level": course.get("level", "N/A"),
            "rationale": step.get("rationale")
        })

    input_text = f"""
CANDIDATO: {candidate_name} (Seniority: {seniority_level})
PROFESSIONAL OBJECTIVE: {professional_objective}

TOTAL ESTIMATED DURATION: {total_duration} hours.

GENERATED SYSTEM PATH:
{json.dumps(ruta_resumida, indent=2, ensure_ascii=False)}

Audit the 'Mentor Quality' (Score 0 to 1.0) based on logic, feasibility, and alignment with the Professional Objective.
"""

    try:
        chain = _build_judge_chain(_MENTOR_QUALITY_SYSTEM)
        result = chain.invoke({"input": input_text})
        score, reason = _extract_score_and_reason(result)
    except Exception as e:
        score, reason = 0.0, f"Error executing judge: {e}"

    return {"key": "overall_mentor_quality", "score": score, "comment": reason}
