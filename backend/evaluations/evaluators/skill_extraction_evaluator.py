"""
Evaluadores LLM-as-Judge para el Agente de Extracción de Skills.
Diseñados para medir la calidad real del mentor, no solo la corrección técnica.

MÉTRICAS (en orden de importancia para el negocio):

    1. technical_fidelity      → Zero Hallucination: ¿Lo que extrajo existe en el CV?
    2. gap_pertinence          → Mentor Value: ¿Las sugerencias son el puente real al objetivo?
    3. seniority_consistency   → ¿El nivel asignado es coherente con skills + años?

Cada juez devuelve un score entre 0.0 y 1.0 y una razón en español.
Los fallos críticos (alucinación, sugerencias redundantes, nivel contradictorio)
penalizan el score hasta 0.0.
"""

from __future__ import annotations
import json
import re
import sys
import os
from datetime import datetime
from typing import Any

# ── Permitir importaciones desde el directorio raíz de backend ────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langsmith.schemas import Example, Run
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from services.llm_service import get_judge_llm


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_ground_truth(outputs: dict) -> str:
    """
    Genera el bloque de Ground Truth para el juez de seniority.
    Si no hay Ground Truth definido (CVs reales sin referencia), devuelve
    una instrucción al juez para que evalúe solo con el CV, sin penalizar
    al agente por no coincidir con un valor vacío.
    """
    seniority_gt = outputs.get("seniority_level")
    years_gt = outputs.get("years_total_experience")
    if seniority_gt is not None:
        return (
            f"- Seniority Esperado: {seniority_gt}\n"
            f"- Años de Experiencia Esperados: {years_gt}"
        )
    return (
        "- SIN GROUND TRUTH: Este es un CV real sin respuesta de referencia. "
        "Evalúa ÚNICAMENTE con base en el CV original arriba. "
        "NO penalices al agente por no coincidir con un valor vacío (None)."
    )


def _extract_score_and_reason(raw_output: Any) -> tuple[float, str]:
    """
    Parsea la respuesta del juez LLM y devuelve (score, reason).
    Acepta un dict directo (del JsonOutputParser) o un string JSON.
    """
    if isinstance(raw_output, dict):
        score = float(raw_output.get("score", 0.0))
        reason = str(raw_output.get("reason", "Sin razón proporcionada"))
        return min(max(score, 0.0), 1.0), reason

    raw_str = str(raw_output)
    raw_str = re.sub(r"```(?:json)?", "", raw_str).strip()
    match = re.search(r"\{.*\}", raw_str, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            score = float(data.get("score", 0.0))
            reason = str(data.get("reason", "Sin razón proporcionada"))
            return min(max(score, 0.0), 1.0), reason
        except (json.JSONDecodeError, ValueError):
            pass
    return 0.0, f"No se pudo parsear la respuesta del juez: {raw_str[:200]}"


def _build_judge_chain(system_prompt: str):
    """Construye una cadena LangChain para el LLM-juez (modelo superior al agente)."""
    llm = get_judge_llm()  # <- Siempre usa el modelo configurado como juez
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])
    return prompt | llm | JsonOutputParser()


# ─────────────────────────────────────────────────────────────────────────────
# MÉTRICA 1 — FIDELIDAD TÉCNICA (Zero Hallucination)
# ─────────────────────────────────────────────────────────────────────────────

_FIDELITY_SYSTEM = """\
Eres un auditor experto en calidad de sistemas de IA para análisis de CVs.
Tu misión es la más crítica del pipeline: detectar ALUCINACIONES.

Una alucinación ocurre cuando el agente extrae una habilidad que:
  a) No aparece en ninguna parte del CV (ni explícita ni implícitamente).
  b) O asigna el nivel "avanzado" o "experto" a algo que el candidato apenas mencionó de paso.

DEFINICIONES CLAVE:
- "explícita": La herramienta/habilidad aparece nombrada directamente en el CV.
- "inferida válida": No aparece nombrada, pero es OBVIA e INDISPENSABLE para el
  rol o logro descrito. Ejemplo: un "Data Engineer" que diseñó pipelines ETL
  con PySpark IMPLICA Python aunque no lo mencione explícitamente.
- "alucinación": La habilidad no aparece y no es una inferencia lógica del rol.

ESCALA DE PUNTUACIÓN:
- 1.0 → Cero alucinaciones. Todo lo extraído está plenamente justificado.
- 0.8 → 1 habilidad inferida que es cuestionable pero defendible.
- 0.5 → 2-3 habilidades sin respaldo claro, o 1 nivel claramente exagerado.
- 0.2 → Varias alucinaciones que contaminarían la ruta de aprendizaje.
- 0.0 → FALLO CRÍTICO: El agente inventó herramientas clave o ignoró el stack
         principal del perfil (ej: no extraer Python en un perfil de Data Science).

IMPORTANTE: Sé muy estricto. La credibilidad del mentor depende de esta métrica.

Responde ÚNICAMENTE con este JSON (sin markdown, sin texto extra):
{{"score": <número entre 0.0 y 1.0>, "reason": "<explicación breve en español, menciona habilidades específicas si hay errores>"}}
"""


def evaluate_technical_fidelity(run: Run, example: Example) -> dict:
    """
    MÉTRICA 1 — Fidelidad Técnica (Zero Hallucination).

    ¿Todo lo que extrajo el agente tiene respaldo real en el CV?
    ¿Ignoró el stack principal del candidato?

    Fallo crítico: Inventar herramientas o ignorar tecnologías centrales.
    """
    cv_text = (example.inputs or {}).get("cv_text", "")
    current_skills = (run.outputs or {}).get("current_skills", [])

    if not current_skills:
        return {
            "key": "technical_fidelity",
            "score": 0.0,
            "comment": "FALLO CRÍTICO: El agente no extrajo ninguna habilidad.",
        }

    input_text = f"""
FECHA DE EVALUACIÓN: {datetime.now().strftime("%B %Y")}. Usa esta fecha para calcular años de experiencia (ej. 2020-Actual = 6 años).

CV ORIGINAL COMPLETO:
---
{cv_text[:10000]}
---

Habilidades ideales (Ground Truth):
{json.dumps(example.outputs or {}, indent=2, ensure_ascii=False)}

HABILIDADES EXTRAÍDAS POR EL AGENTE:
{json.dumps(current_skills, indent=2, ensure_ascii=False)}

Audita cada habilidad extraída por el agente comparándola con el CV y las habilidades ideales. ¿Tiene respaldo real o es una alucinación?
Menciona en tu razón qué habilidades específicas son problemáticas, si las hay.
"""

    try:
        chain = _build_judge_chain(_FIDELITY_SYSTEM)
        result = chain.invoke({"input": input_text})
        score, reason = _extract_score_and_reason(result)
    except Exception as e:
        score, reason = 0.0, f"Error al ejecutar el juez de fidelidad: {e}"

    return {"key": "technical_fidelity", "score": score, "comment": reason}


# ─────────────────────────────────────────────────────────────────────────────
# MÉTRICA 2 — PERTINENCIA DEL GAP (Mentor Value)
# ─────────────────────────────────────────────────────────────────────────────

_GAP_PERTINENCE_SYSTEM = """\
Eres un experto coach de carrera técnica con 15 años de experiencia.
Tu tarea es evaluar si las habilidades SUGERIDAS por un agente de IA son
el puente real y específico entre el perfil actual del candidato y su objetivo profesional.

Un mentor de calidad NO sugiere temas genéricos solo para rellenar. Las sugerencias
deben ser el camino más corto y efectivo hacia el objetivo declarado.

FALLOS CRÍTICOS que llevan a puntuación 0.0:
  a) Sugerir una habilidad que el candidato ya tiene marcada como "avanzada" o "experta".
  b) Sugerir temas tan genéricos que valen para cualquier perfil básico (ej: "Git",
     "Comunicación", "Trabajo en equipo" para alguien con 5 años de experiencia técnica).
  c) Las sugerencias no guardan relación lógica con el objetivo profesional.

ESCALA DE PUNTUACIÓN:
- 1.0 → Cada sugerencia es el puente exacto al objetivo. Priorizadas perfectamente.
- 0.8 → La mayoría son excelentes; quizás 1 sugerencia es mejorable o el "reason" es vago.
- 0.5 → Mezcla de sugerencias valiosas y genéricas. Alguna prioridad mal asignada.
- 0.2 → La mayoría son genéricas, redundantes o mal enfocadas.
- 0.0 → FALLO CRÍTICO: Sugiere habilidades que ya posee o que son irrelevantes.

Responde ÚNICAMENTE con este JSON:
{{"score": <número entre 0.0 y 1.0>, "reason": "<explicación en español justificando con ejemplos>"}}
"""


def evaluate_gap_pertinence(run: Run, example: Example) -> dict:
    """
    MÉTRICA 2 — Pertinencia del Gap (Mentor Value).

    ¿Las sugerencias son el puente real entre lo que el candidato sabe
    y su objetivo profesional? ¿O son genéricas y redundantes?

    Fallo crítico: Sugerir algo que el candidato ya domina o algo irrelevante.
    """
    professional_objective = (example.inputs or {}).get(
        "professional_objective", "No especificado"
    )
    current_skills = (run.outputs or {}).get("current_skills", [])
    suggested_skills = (run.outputs or {}).get("suggested_skills", [])
    seniority = (run.outputs or {}).get("seniority_level", "desconocido")

    if not suggested_skills:
        return {
            "key": "gap_pertinence",
            "score": 0.0,
            "comment": "FALLO CRÍTICO: El agente no generó ninguna sugerencia de habilidades.",
        }

    # Extraer habilidades actuales en nivel avanzado para detectar redundancias
    advanced_skills = [
        s.get("name", "")
        for s in current_skills
        if s.get("level") in ("advanced", "expert")
    ]

    input_text = f"""
FECHA DE EVALUACIÓN: {datetime.now().strftime("%B %Y")}.

OBJETIVO PROFESIONAL DEL CANDIDATO: {professional_objective}
SENIORITY DETECTADO: {seniority}

HABILIDADES ACTUALES DEL CANDIDATO:
{json.dumps(current_skills, indent=2, ensure_ascii=False)}

HABILIDADES YA DOMINADAS (avanzado/experto):
{json.dumps(advanced_skills, ensure_ascii=False)}

SUGERENCIAS DEL AGENTE (lo que evaluarás):
{json.dumps(suggested_skills, indent=2, ensure_ascii=False)}

Evalúa si cada sugerencia del agente es el puente real al objetivo profesional.
Penaliza duramente si alguna sugerida ya está en la lista de habilidades dominadas.
"""

    try:
        chain = _build_judge_chain(_GAP_PERTINENCE_SYSTEM)
        result = chain.invoke({"input": input_text})
        score, reason = _extract_score_and_reason(result)
    except Exception as e:
        score, reason = 0.0, f"Error al ejecutar el juez de gap: {e}"

    return {"key": "gap_pertinence", "score": score, "comment": reason}


# ─────────────────────────────────────────────────────────────────────────────
# MÉTRICA 3 — CONSISTENCIA DE SENIORITY
# ─────────────────────────────────────────────────────────────────────────────

_SENIORITY_SYSTEM = """\
Eres un director de ingeniería con 20 años de experiencia evaluando perfiles técnicos.
Tu tarea es verificar si el nivel de seniority asignado por un agente de IA
es COHERENTE y CONSISTENTE con tres fuentes de evidencia del CV:

  1. AÑOS DE EXPERIENCIA: ¿Cuántos años reales acredita? Usa la "FECHA DE EVALUACIÓN" como hoy.
  2. COMPLEJIDAD DE SKILLS: ¿Los niveles reflejan madurez técnica real (principiante/medio/avanzado)?
  3. RESPONSABILIDADES: ¿Lideró equipos? ¿Tomó decisiones de arquitectura?

ESCALA DE SENIORITY de referencia:
- junior:    0-2 años técnicos. Estudiantes o perfiles sin autonomía.
- mid:       2-5 años. Resuelve problemas de forma autónoma.
- senior:    AL MENOS UNO DE: a) 5+ años técnicos, b) 3+ años con Liderazgo Técnico, c) Maestría/Doc + 3+ años.
- lead:      8+ años con gestión de equipos o responsabilidad de producto.
- principal: 10+ años, decisiones estratégicas en la organización.

REGLAS DE EXCEPCIÓN (No penalizar al agente aquí):
1. TRANSICIONES DE CARRERA: Si el candidato tiene 10 años en "Ventas" pero busca su primer rol como "AI Engineer", su seniority técnico es 'junior'. Esto es CORRECTO (Score 1.0).

FALLOS CRÍTICOS (Score 0.0):
  a) Etiquetar "senior" a alguien con habilidades todas en nivel principiante.
  b) Etiquetar "junior" a alguien con 8+ años de liderazgo técnico real.

Responde ÚNICAMENTE con este JSON:
{{"score": <número>, "reason": "<explicación justificando con las reglas de seniority>"}}
"""


def evaluate_seniority_consistency(run: Run, example: Example) -> dict:
    """
    MÉTRICA 3 — Consistencia de Seniority.

    ¿El nivel asignado (junior/mid/senior/lead/principal) es coherente
    con los años de experiencia y la complejidad de las habilidades extraídas?

    Fallo crítico: Senior con habilidades beginner, o junior con 10 años liderando equipos.
    """
    cv_text = (example.inputs or {}).get("cv_text", "")
    current_skills = (run.outputs or {}).get("current_skills", [])
    seniority = (run.outputs or {}).get("seniority_level", "unknown")
    years_experience = (run.outputs or {}).get("years_total_experience", "desconocido")
    profile_summary = (run.outputs or {}).get("profile_summary", "")

    if seniority == "unknown" or not current_skills:
        return {
            "key": "seniority_consistency",
            "score": 0.0,
            "comment": "FALLO CRÍTICO: El agente no pudo determinar el seniority o no extrajo skills.",
        }

    # Construir un resumen de distribución de niveles para el juez
    level_distribution: dict[str, int] = {}
    for skill in current_skills:
        level = skill.get("level", "unknown")
        level_distribution[level] = level_distribution.get(level, 0) + 1

    input_text = f"""
FECHA DE EVALUACIÓN: {datetime.now().strftime("%B %Y")}. Úsala estrictamente al calcular los años de experiencia de empleos hasta la actualidad.

CV ORIGINAL (para contexto de responsabilidades):
---
{cv_text[:10000]}
---

EVIDENCIA IDEAL (Ground Truth):
{_fmt_ground_truth(example.outputs or {})}

SENIORITY ASIGNADO POR EL AGENTE: {seniority}
AÑOS DE EXPERIENCIA DETECTADOS: {years_experience}
RESUMEN DEL PERFIL: {profile_summary}

DISTRIBUCIÓN DE NIVELES DE HABILIDADES EXTRAÍDAS:
{json.dumps(level_distribution, ensure_ascii=False)}

HABILIDADES COMPLETAS (para verificar coherencia):
{json.dumps(current_skills, indent=2, ensure_ascii=False)}

¿El seniority "{seniority}" es coherente con esta evidencia y el ideal esperado?
"""

    try:
        chain = _build_judge_chain(_SENIORITY_SYSTEM)
        result = chain.invoke({"input": input_text})
        score, reason = _extract_score_and_reason(result)
    except Exception as e:
        score, reason = 0.0, f"Error al ejecutar el juez de seniority: {e}"

    return {"key": "seniority_consistency", "score": score, "comment": reason}


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRO FINAL
# ─────────────────────────────────────────────────────────────────────────────

ALL_EVALUATORS = [
    evaluate_technical_fidelity,    # ← Más importante: sin alucinaciones
    evaluate_gap_pertinence,        # ← El "cerebro" del mentor
    evaluate_seniority_consistency, # ← El error más común en agentes de RRHH
]
