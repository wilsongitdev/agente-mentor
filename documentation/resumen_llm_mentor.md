# Resumen Técnico Completo — Proyecto Agente Mentor
> Documento generado para dar contexto a un LLM. Cubre arquitectura, decisiones de diseño, implementación y resultados experimentales cuantitativos.

---

## 1. Visión General del Proyecto

**Agente Mentor** es un sistema de Inteligencia Artificial multi-agente diseñado para automatizar la generación de **rutas de aprendizaje personalizadas** a partir de CVs profesionales en formato PDF.

El flujo de valor es el siguiente:
1. El usuario sube su CV (PDF) y declara un **objetivo profesional** (ej. "AI Engineer", "Data Analyst").
2. El sistema analiza el perfil y detecta sus habilidades actuales, nivel de seniority y **brechas de conocimiento** (*skill gaps*) respecto al objetivo.
3. El sistema recupera cursos relevantes de un catálogo indexado semánticamente.
4. El sistema sintetiza una **ruta pedagógica ordenada** con justificaciones y tiempos estimados.

**Contexto académico:** Trabajo Final de un programa de AI Engineering. Validado con 21 experimentos en LangSmith sobre 7 CVs reales de LinkedIn. La evolución de la arquitectura demostró una mejora del **+52% en calidad E2E** entre el Baseline y la Arquitectura Final.

---

## 2. Stack Tecnológico

| Capa | Tecnología | Propósito |
|---|---|---|
| **Orquestación** | LangGraph 0.1.x (StateGraph) | Flujo determinístico de agentes |
| **LLM Principal** | AWS Bedrock (Claude 3.5 Haiku) *o* OpenAI GPT-4o-mini | Extracción de habilidades + generación de rutas |
| **LLM Juez** | Configurable (modelo superior al agente) | Evaluación automatizada LLM-as-Judge |
| **Embeddings** | OpenAI `text-embedding-3-small` | Vectorización del catálogo de cursos |
| **Vector Store** | FAISS (configurable a Chroma) | Búsqueda semántica de cursos |
| **Base de Datos** | Firebase Realtime Database | Persistencia de sesiones y rutas generadas |
| **PDF Parsing** | E2B Code Interpreter (Sandbox en la nube) + pdfplumber | Extracción segura de texto de PDFs |
| **API Backend** | FastAPI + Uvicorn (Python 3.11) | REST API asíncrona |
| **Frontend** | React 18 + Vite + Tailwind CSS | Interfaz de usuario |
| **Evaluación/Trazabilidad** | LangSmith | Logging de runs + métricas experimentales |
| **Entorno** | Miniconda + Python 3.11 (conda env: `cv-analyzer`) | Gestión de dependencias |

---

## 3. Arquitectura del Sistema — 4 Agentes en Pipeline

El sistema implementa un **StateGraph de LangGraph** con flujo lineal determinístico. Todos los agentes comparten un estado mutable común (`AgentState` TypedDict):

```
PDF Upload → [FastAPI] → BackgroundTask → [LangGraph Pipeline] → Firebase → Frontend
```

### 3.1 Estado Compartido (`AgentState`)

```python
class AgentState(TypedDict, total=False):
    # Sesión
    session_id: str
    pdf_path: str
    professional_objective: str

    # Output Agente 1
    cv_text: str

    # Output Agente 2
    candidate_name: Optional[str]
    seniority_level: str                       # "junior" | "mid" | "senior" | "lead" | "principal"
    years_total_experience: Optional[float]
    current_skills: List[Dict]                 # [{name, level, reason}]
    suggested_skills: List[Dict]               # [{name, priority, reason}]
    profile_summary: str

    # Output Agente 3
    matched_courses: List[Dict]                # Top 8 cursos del catálogo

    # Output Agente 4
    learning_path: Dict                        # Objeto LearningPath completo

    # Control
    errors: List[str]
    current_step: str
```

### 3.2 Grafo de Flujo

```
pdf_parser ──[conditional]──► skill_extractor ──[conditional]──► course_matcher ──► learning_path_generator ──► END
```

- Aristas condicionales: si hay error en `pdf_parser` o `skill_extractor`, el pipeline **aborta** sin seguir procesando.
- `course_matcher` → `learning_path_generator`: arista directa (no condicional).

---

## 4. Descripción Detallada de Cada Agente

### Agente 1 — PDF Parser ("The Reader")
- **Tecnología clave:** E2B Sandbox (ejecución de código en contenedor cloud aislado) + pdfplumber.
- **Motivación del Sandbox:** Seguridad. Los PDFs pueden contener código malicioso embebido. Al ejecutar la extracción dentro de E2B, se evita cualquier riesgo en el servidor local.
- **Entrada:** Ruta del archivo PDF en el servidor.
- **Salida:** `cv_text` — texto plano limpio extraído.
- **Sin LLM:** No usa IA generativa para garantizar fidelidad absoluta del texto.

### Agente 2 — Skill Extraction Agent ("The Profiler")
- **Tecnología clave:** LLM (Claude 3.5 Haiku o GPT-4o-mini) con prompt estructurado.
- **Entrada:** `cv_text` + `professional_objective`.
- **Salida:** Perfil estructurado en JSON:
  - `current_skills`: Lista de habilidades actuales con nivel (beginner/intermediate/advanced/expert).
  - `suggested_skills`: Brechas respecto al objetivo, con prioridad (high/medium/low) y justificación.
  - `seniority_level`: junior → principal.
  - `years_total_experience`: Años de experiencia total detectados.
  - `profile_summary`: Resumen narrativo del perfil.
- **Gestión de prompts:** El sistema permite seleccionar entre 3 versiones de prompt (V1 Baseline, V2 Elaborado, V3 Premium) mediante variable de entorno `PROMPT_VERSION`. En producción se usa V3.

### Agente 3 — Course Matching Agent ("The Searcher — RAG + Reranking")
> **Este agente es la contribución arquitectónica más importante del proyecto.**

- **Tecnología clave:** FAISS (búsqueda vectorial) + Algoritmo de Reranking Heurístico propio.
- **Sin costo adicional de LLM:** Todo el matching se hace sin llamadas a modelos generativos.
- **Entrada:** `current_skills`, `suggested_skills`, `seniority_level`, `professional_objective`.

#### Proceso Multi-Etapa:

**Paso 1 — Construcción de Queries Diversificadas:**
El agente genera hasta 12 queries de búsqueda semántica priorizadas por relevancia:
- Alta prioridad: queries para brechas críticas (`priority: "high"`) con contexto del rol.
- Media prioridad: queries para brechas secundarias.
- Habilidades actuales no dominadas (nivel no `advanced`/`expert`): queries de profundización.
- Queries genéricas de trayectoria basadas en seniority y objetivo.

**Paso 2 — Búsqueda Vectorial (FAISS):**
- Ejecuta `multi_query_search` con `k=5` por query.
- Obtiene hasta 30 cursos candidatos en bruto.
- **Filtrado previo:** Elimina cursos de habilidades ya dominadas (nivel advanced/expert).

**Paso 3 — Reranking Heurístico (núcleo del Agente 3):**
Sistema de scoring con pesos explícitos:
```python
# REGLA 1: Exact Match de Brechas → +15 puntos (alta prioridad en título/skills)
# REGLA 1b: Match en descripción → +5 puntos

# REGLA 2: Nivel del curso vs. Seniority del candidato
# - Nivel exacto match → +10
# - Junior + curso avanzado no integral → -15
# - Senior + curso básico ofimático → -25 (penalización fuerte)
# - Senior + curso principiante técnico → -12

# REGLA 3: Fundamentos de dominio real (pandas, numpy, SQL, estadística) → +8
```
- Lista de `generic_basics` penalizados para seniors: excel, word, outlook, powerpoint, "conceptos de PC".
- Lista de `domain_fundamentals` bonificados: pandas, numpy, SQL, matplotlib, estadística.

**Salida:** Top 8 cursos (`MAX_RERANKED_COURSES = 8`) ordenados por score heurístico.

**Feature flag:** `USE_RERANKING=true/false` en `.env` para comparar con/sin reranking.

### Agente 4 — Learning Path Generator ("The Architect")
- **Tecnología clave:** LLM con prompt instruccional.
- **Entrada:** Perfil completo del candidato + cursos seleccionados.
- **Proceso:** El LLM organiza los cursos en fases secuenciales (hitos/milestones), calcula tiempos estimados de compleción y redacta un resumen ejecutivo con justificación pedagógica de la ruta.
- **Salida:** Objeto `LearningPath` con:
  - `steps[]`: Ordenados con `step_no`, `phase`, `course`, `rationale`.
  - `total_duration_hours`.
  - `candidate_name`, `seniority_level`.
  - JSON estructurado persistido en Firebase.

---

## 5. API REST (FastAPI)

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/upload-cv` | POST | Sube PDF (multipart). Responde inmediatamente con `session_id`. El procesamiento corre en `BackgroundTasks`. |
| `/api/v1/job-status/{session_id}` | GET | Polling de estado: `processing` → `completed` / `failed`. Incluye `learning_path` cuando completa. |
| `/api/v1/learning-path/{session_id}` | GET | Devuelve la ruta persistida en Firebase. |
| `/api/v1/index-courses` | POST | Re-indexa catálogo de Firebase → FAISS en background. |

---

## 6. Framework de Evaluación

El proyecto implementa un **sistema de evaluación completo** con 3 capas:

### 6.1 Evaluación del Agente 2 (Skill Extraction) — 3 métricas vía LLM-as-Judge

**Métrica 1 — `technical_fidelity` (Fidelidad Técnica / Zero Hallucination):**
- **Qué mide:** ¿Todo lo extraído tiene respaldo real en el CV? ¿Se ignoró el stack principal?
- **Fallo crítico (0.0):** Inventar herramientas o ignorar tecnologías centrales.
- **Definición de "inferida válida":** Skill que no aparece nombrada pero es obvia e indispensable para el rol descrito (ej: Data Engineer con ETL en PySpark → Python se puede inferir).
- **Scoring:** 1.0 (cero alucinaciones) → 0.0 (fallo crítico).

**Métrica 2 — `gap_pertinence` (Pertinencia del Gap / Mentor Value):**
- **Qué mide:** ¿Las sugerencias son el puente real y específico al objetivo profesional?
- **Fallo crítico (0.0):** Sugerir skills que el candidato ya domina (advanced/expert), o sugerencias genéricas irrelevantes.
- **Context al juez:** Se pasan las skills dominadas (advanced/expert) para detectar redundancias.

**Métrica 3 — `seniority_consistency` (Consistencia de Seniority):**
- **Qué mide:** ¿El nivel asignado es coherente con años de experiencia + complejidad de skills + responsabilidades?
- **Regla de excepción crítica:** Candidatos en **transición de carrera** (ej. 5 años como chef que quiere ser AI Engineer) deben recibir `junior` aunque tengan muchos años totales. Este edge case está explícitamente codificado en el prompt del juez.
- **Escala de referencia:** junior (0-2 años técnicos) → mid (2-5) → senior (5+ técnicos o 3+ con liderazgo técnico o Maestría+3 años) → lead (8+ con gestión) → principal (10+ estratégico).

### 6.2 Evaluación del Sistema E2E — 1 métrica vía LLM-as-Judge

**Métrica — `overall_mentor_quality` (Calidad E2E del Sistema):**
- **Qué mide:** 3 dimensiones simultáneas:
  1. **Alignment (Alineación):** ¿La ruta responde al objetivo profesional declarado?
  2. **Logic (Coherencia):** ¿El orden es pedagógicamente correcto (bases antes que avanzado)?
  3. **Feasibility (Viabilidad):** ¿Los tiempos son realistas y el nivel es adecuado al seniority?
- **Fallo crítico (0.0-0.3):** Cursos sin relación, nivel completamente errado, orden ilógico.
- **Scoring:** 1.0 (excepcional) → 0.0 (fallo crítico).

### 6.3 Métricas de Rendimiento Operativo (de LangSmith)

El script `reporte_sistema_e2e.py` extrae automáticamente de LangSmith:
- **Latencia:** Tiempo E2E real (solo runs raíz, excluyendo sub-runs) en segundos.
- **Tokens del agente:** Total de tokens del pipeline, **excluyendo** los tokens del LLM-Judge (identificados por `run_type == "evaluator"` o keywords como `ChatPromptTemplate`, `JsonOutputParser`, `RunnableSequence`).
- **Costo operativo:** Calculado usando tarifas de AWS Bedrock Claude 3.5 Haiku:
  - Input: $0.25 / 1M tokens
  - Output: $1.25 / 1M tokens
  - Promedio conservador usado: $0.50 / 1M tokens ($0.0005 por 1k tokens)

---

## 7. Diseño Experimental y Evolución Arquitectónica

### 7.1 Experimentos de Agente 2 — Ingeniería de Prompts (Skill Extraction)

Se evaluaron **3 versiones de prompt** (A/B testing) con el mismo dataset de 7 CVs:
- **V1:** Prompt baseline mínimo.
- **V2:** Prompt elaborado con más instrucciones.
- **V3:** Prompt "premium" — versión en producción.

*Nota: Los resultados numéricos exactos por versión de prompt están en LangSmith / imagen 1.*

### 7.2 Experimentos de Agente 4 — Evolución del Learning Path

Se compararon **3 configuraciones arquitectónicas** midiendo `path_effectiveness` y `logical_order`:

| Fase | Configuración | Orden Lógico | Efectividad de Ruta |
|---|---|:---:|:---:|
| 1 | **Baseline V1** (Prompt V1 + sin Reranking) | 0.67 | 0.80 |
| 2 | **Solo Prompting V3** (Prompt V3 + sin Reranking) | 0.73 | 0.79 |
| 3 | **Arquitectura Final** (Prompt V3 + Reranking heurístico) | **0.74** | **0.90** |

**Insight clave:** El prompting aislado (Fase 2) mejoró el orden lógico pero no la efectividad de ruta. El salto en `path_effectiveness` de 0.79 → 0.90 se consiguió exclusivamente con el **Reranking Heurístico** del Agente 3, que entrega cursos más relevantes al Agente 4.

### 7.3 Evaluación E2E (Sistema Completo) — Real-World LinkedIn CVs

**Dataset:** 7 CVs reales de LinkedIn de distintos perfiles.
**Total de experimentos:** 21 corridas registradas en LangSmith.
**Comparadas:** Baseline v/s Arquitectura Final (con Reranking).

| Arquitectura | Calidad E2E (`overall_mentor_quality`) | Latencia E2E | Tokens Promedio (solo agente) |
|---|:---:|:---:|:---:|
| **Baseline** | 0.53 | 16.6 s | ~3,800 |
| **Arquitectura Final** | **0.81** | 18.8 s | ~4,600 |
| **Δ mejora** | **+52.8%** | +2.2 s (+13.3%) | +~800 tokens |

**Análisis costo-beneficio:** La mejora del +52% en calidad tiene un costo adicional de solo +2.2 segundos de latencia y ~800 tokens extra por sesión. El costo operativo de la Arquitectura Final por sesión sigue siendo inferior a **$0.01 USD**.

---

## 8. Estructura del Repositorio

```
agente-mentor/
├── backend/
│   ├── agents/
│   │   ├── pdf_parser_agent.py          # Agente 1: PDF → texto (E2B Sandbox)
│   │   ├── skill_extraction_agent.py    # Agente 2: texto → skills+gaps (LLM)
│   │   ├── course_matching_agent.py     # Agente 3: skills → cursos (FAISS + Reranking)
│   │   └── learning_path_agent.py       # Agente 4: cursos → ruta pedagógica (LLM)
│   ├── api/
│   │   ├── main.py                      # FastAPI app
│   │   └── routes/
│   │       ├── cv.py                    # POST /upload-cv
│   │       └── learning_path.py         # GET /learning-path/:id
│   ├── core/
│   │   ├── graph.py                     # StateGraph de LangGraph (pipeline completo)
│   │   └── state.py                     # AgentState (TypedDict compartido)
│   ├── config/settings.py               # Pydantic-settings (config + env vars)
│   ├── db/seed_courses.py               # Populate Firebase + construir índice FAISS
│   ├── prompts/
│   │   ├── skill_extraction.py          # Selector dinámico V1/V2/V3
│   │   ├── prompt_library.py            # Todas las versiones de prompt
│   │   └── learning_path.py             # Prompts del Agente 4
│   ├── evaluations/
│   │   ├── dataset_builder.py           # Construye dataset en LangSmith
│   │   ├── evaluators/
│   │   │   ├── skill_extraction_evaluator.py    # Jueces LLM: 3 métricas Agente 2
│   │   │   ├── learning_path_evaluator.py       # Jueces LLM: Agente 4
│   │   │   └── system_quality_evaluator.py      # Juez LLM: E2E (overall_mentor_quality)
│   │   ├── runners/
│   │   │   ├── run_skills_eval.py               # Runner: Agente 2
│   │   │   ├── run_skills_experiments.ps1        # Script: 3 versiones de prompt
│   │   │   ├── run_e2e_eval.py                   # Runner: E2E completo
│   │   │   └── run_e2e_experiments.ps1           # Script: Baseline vs Final
│   │   ├── reports/
│   │   │   ├── reporte_agente_1_extraccion.py    # → imagen 1_rendimiento_extraccion_habilidades.png
│   │   │   ├── reporte_agente_3_evolucion_lp.py  # → imagen 2_evolucion_arquitectura_pedagogica.png
│   │   │   ├── reporte_detallado_real_world.py   # → imagen 3_evaluacion_detallada_cvs_reales.png
│   │   │   ├── reporte_sistema_e2e.py            # → imagen 4_rendimiento_sistema_completo.png
│   │   │   └── reporte_costos_negocio.py         # → imagen 5_analisis_costos_operativos.png
│   │   └── real_world/
│   │       ├── cvs_to_test/                      # 7 CVs reales de LinkedIn (PDF)
│   │       └── bulk_evaluate_cvs.py              # Evaluación masiva por lotes
│   └── services/
│       ├── llm_service.py               # Abstracción LLM (OpenAI / AWS Bedrock)
│       ├── vector_store_service.py      # FAISS: index + multi_query_search
│       ├── pdf_service.py               # Extracción PDF (local fallback)
│       └── firebase_service.py          # CRUD Firebase Realtime DB
├── frontend/                            # React 18 + Vite + Tailwind CSS
├── documentation/architecture.md
├── environment.yml                      # Conda environment (cv-analyzer)
└── README.md
```

---

## 9. Variables de Entorno Clave

```env
# Proveedor LLM
LLM_PROVIDER=bedrock                          # "openai" | "bedrock"

# OpenAI (si LLM_PROVIDER=openai)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# AWS Bedrock (si LLM_PROVIDER=bedrock)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0

# Firebase
FIREBASE_CREDENTIALS_PATH=./config/firebase_credentials.json
FIREBASE_DATABASE_URL=https://<proyecto>.firebaseio.com

# LangSmith (trazabilidad + evaluaciones)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=agente-mentor

# E2B Sandbox (extracción PDF segura)
E2B_API_KEY=e2b_...

# Feature Flag — Reranking (default: true)
USE_RERANKING=true

# Versión de Prompt (Agente 2) — default: V3
PROMPT_VERSION=V3
```

---

## 10. Conceptos Teóricos Implementados

| Concepto | Implementación en el proyecto |
|---|---|
| **Multi-Agent System** | 4 agentes especializados orquestados por LangGraph StateGraph |
| **RAG (Retrieval-Augmented Generation)** | Agente 3: FAISS multi-query → contexto de cursos inyectado al Agente 4 |
| **LLM-as-Judge** | Evaluación automatizada con LLM superior como árbitro de calidad |
| **Prompt Engineering (A/B Testing)** | 3 versiones de prompt medidas experimentalmente en LangSmith |
| **Heuristic Re-ranking** | Scoring propio sin costo de LLM, mejora selection de cursos +11 pts path_effectiveness |
| **Observabilidad / Tracing** | LangSmith: todas las corridas trazadas con métricas, inputs y outputs |
| **Async Processing** | FastAPI BackgroundTasks + polling para no bloquear al usuario |
| **Secure Sandboxing** | E2B Cloud Sandbox para ejecución aislada de código de extracción PDF |
| **Feature Flags** | `USE_RERANKING` y `PROMPT_VERSION` permiten A/B testing sin cambios de código |

---

## 11. Resultados Cuantitativos Consolidados

### Agente 2 — Evolución por Versión de Prompt
*(Las métricas exactas por versión se consultan en LangSmith bajo experimentos `skills-v1`, `skills-v2`, `skills-v3`)*
- Las 3 métricas evaluadas: `technical_fidelity`, `gap_pertinence`, `seniority_consistency`.
- Cada métrica puntúa entre 0.0 y 1.0, evaluada por un LLM-Juez.

### Agente 4 — Evolución Arquitectónica (Learning Path)
| Fase | Config | `logical_order` | `path_effectiveness` |
|---|---|:---:|:---:|
| 1 | Baseline (V1, sin Reranking) | 0.67 | 0.80 |
| 2 | Solo Prompt V3 (sin Reranking) | 0.73 | 0.79 |
| 3 | **V3 + Reranking Heurístico** | **0.74** | **0.90** |

### Sistema Completo — E2E (7 CVs reales)
| Arquitectura | `overall_mentor_quality` | Latencia | Tokens (solo agente) | Costo/sesión |
|---|:---:|:---:|:---:|:---:|
| Baseline | 0.53 | 16.6 s | ~3,800 | < $0.01 USD |
| **Arquitectura Final** | **0.81** | 18.8 s | ~4,600 | < $0.01 USD |
| **Δ** | **+52.8%** | +2.2s | +~800 | mínimo |

---

## 12. Limitaciones Conocidas y Mejoras Propuestas

| Área | Limitación Actual | Mejora Propuesta |
|---|---|---|
| Autenticación | Sin auth, sistema single-tenant | JWT multi-tenant |
| Escalabilidad | BackgroundTasks de FastAPI (no distribuido) | Celery / AWS SQS |
| Caché | Sin caché | Redis para jobs + respuestas LLM |
| Catálogo | Cursos estáticos en Firebase | Integración con APIs de Coursera/Udemy |
| Multiidioma | CVs en español/inglés, prompts en español | Detección automática de idioma |
| Streaming | Respuesta completa o nada | SSE (Server-Sent Events) para stream parcial |
| Tests | Sin tests unitarios automatizados | Pytest + mocked LLM |
| Contenedores | Instalación manual | Docker + docker-compose |

---

*Este documento fue generado el 2026-04-09 a partir del análisis completo del código fuente, README y resultados experimentales del proyecto.*
