"""
Evaluador específico para el Agente Generador de Rutas de Aprendizaje (Node 3).

MÉTRICAS:
1. path_effectiveness: ¿Los cursos seleccionados resuelven las brechas (gap) del candidato?
2. logical_order: ¿El orden pedagógico es el correcto (básico → avanzado) respetando el seniority?
"""

from __future__ import annotations
import json
import os
import sys

# Permitir importaciones desde backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langsmith.schemas import Example, Run
from evaluations.evaluators.skill_extraction_evaluator import _build_judge_chain, _extract_score_and_reason

# ─────────────────────────────────────────────────────────────────────────────
# MÉTRICA 1: EFICACIA DE LA RUTA (Path Effectiveness)
# ─────────────────────────────────────────────────────────────────────────────

_PATH_EFFECTIVENESS_SYSTEM = """\
Eres un auditor experto de contenido de e-learning.
Tu misión es evaluar si la ruta de aprendizaje generada aborda eficientemente
las brechas de habilidades identificadas para el candidato.

REGLAS CRÍTICAS DE EVALUACIÓN:
1. EVALÚA POR CONTENIDO, NO SOLO POR TÍTULO: Un curso titulado "LangChain Avanzado" o
   "FastAPI Completo" puede cubrir desde fundamentos hasta niveles altos. Revisa las
   "skills_covered" de cada curso asignado, no solo el título, para determinar si una
   brecha está cubierta.
2. CURSOS INTEGRALES SON VÁLIDOS: Si un curso cubre una tecnología de la lista de brechas
   (aunque sea nombrado como avanzado), cuenta como que la brecha está cubierta.
3. CURSOS FUNDACIONALES SON VÁLIDOS: Cursos de Python, ML básico o programación general
   son steps válidos y necesarios si el candidato los necesita como prerequisito para
   su objetivo (ej: AI Engineer Junior necesita Python antes de LangChain).
4. SOLO PENALIZA SI: La brecha de alta prioridad no está cubierta por NINGUNO de los
   cursos (ni por título ni por skills_covered).

Reglas de scoring (0.0 a 1.0):
- 1.0: Cursos relevantes para las brechas de alta prioridad declaradas.
- 0.5: Falta alguna brecha clave o hay cursos claramente irrelevantes para el objetivo.
- 0.0: Los cursos no tienen relación con el objetivo ni con las brechas del candidato.

Responde ÚNICAMENTE en JSON:
{{"score": <número>, "reason": "<explicación breve en español sobre la pertinencia de los cursos>"}}
"""

def evaluate_path_effectiveness(run: Run, example: Example) -> dict:
    learning_path = (run.outputs or {}).get("learning_path", {})
    suggested_skills = (run.outputs or {}).get("suggested_skills", [])
    
    if not learning_path.get("steps"):
        return {"key": "path_effectiveness", "score": 0.0, "comment": "No se generó ruta."}

    cursos = [
        {
            "title": s.get("course", {}).get("title", ""),
            "skills_covered": s.get("course", {}).get("skills_covered", [])
        }
        for s in learning_path.get("steps", [])
    ]
    
    input_text = f"""
BRECHAS IDENTIFICADAS (lo que el candidato necesita aprender):
{json.dumps(suggested_skills, ensure_ascii=False, indent=2)}

CURSOS ASIGNADOS (título + habilidades que cubre cada uno):
{json.dumps(cursos, ensure_ascii=False, indent=2)}
"""
    try:
        chain = _build_judge_chain(_PATH_EFFECTIVENESS_SYSTEM)
        res = chain.invoke({"input": input_text})
        score, reason = _extract_score_and_reason(res)
    except Exception as e:
        score, reason = 0.0, str(e)

    return {"key": "path_effectiveness", "score": score, "comment": reason}


# ─────────────────────────────────────────────────────────────────────────────
# MÉTRICA 2: ORDEN LÓGICO (Logical Order)
# ─────────────────────────────────────────────────────────────────────────────

_LOGICAL_ORDER_SYSTEM = """\
Eres un diseñador instruccional experto analizando el orden pedagógico de una ruta de cursos.

## DISTINCIÓN DE TRANSICIÓN:
Para evaluar el orden, considera:
1. CAMBIO DE SECTOR: No tiene bases técnicas. Requiere fundamentos de programación Y de dominio.
2. PIVOTE TÉCNICO: Es experto en otra área de software.
   → PUEDE saltarse bases de programación general.
   → DEBE tomar fundamentos del NUEVO dominio (ej: Pandas antes de ML, SQL antes de ETL). Omitir estos fundamentos de dominio es un ERROR pedagógico, incluso para Seniors.

## FALLOS A IDENTIFICAR:
1. Violación de secuencia lógica: Poner herramientas avanzadas sin sus dependencias de dominio (ej: ML sin Pandas, Spark sin SQL).
2. Subestimar al candidato: Hacerle tomar "Python desde cero" si ya es un Senior Dev (pero sí debe tomar "Pandas").

Reglas de scoring (0.0 a 1.0):
- 1.0: Secuencia lógica impecable. Respeta dependencias de dominio.
- 0.5: Orden aceptable pero con saltos pedagógicos cuestionables.
- 0.0: Error fatal: ML antes que Pandas, o ignora totalmente el seniority del candidato.

Responde ÚNICAMENTE en JSON:
{{"score": <número>, "reason": "<explicación en español justificando el orden basándote en el tipo de transición>"}}
"""

def evaluate_logical_order(run: Run, example: Example) -> dict:
    learning_path = (run.outputs or {}).get("learning_path", {})
    
    if not learning_path.get("steps"):
        return {"key": "logical_order", "score": 0.0, "comment": "No se generó ruta."}

    seniority_level = learning_path.get("seniority_level", "unknown")
    current_skills = learning_path.get("current_skills", [])
    profile_summary = learning_path.get("executive_summary", "") # Usamos el resumen de la ruta o el del perfil si estuviera
    
    pasos = []
    for s in learning_path.get("steps", []):
        pasos.append(f"Paso {s.get('step')}: {s.get('course', {}).get('title')} - Razón: {s.get('rationale')}")
        
    input_text = f"""
PERFIL DEL ALUMNO:
- Seniority: {seniority_level}
- Resumen: {profile_summary}
- Habilidades Actuales: {json.dumps(current_skills, ensure_ascii=False)}

ORDEN DE CURSOS ASIGNADOS:
{chr(10).join(pasos)}
"""
    try:
        chain = _build_judge_chain(_LOGICAL_ORDER_SYSTEM)
        res = chain.invoke({"input": input_text})
        score, reason = _extract_score_and_reason(res)
    except Exception as e:
        score, reason = 0.0, str(e)

    return {"key": "logical_order", "score": score, "comment": reason}
