"""
Orquestación de LangGraph.

Flujo:
  pdf_parser ──► skill_extractor ──► course_matcher ──► learning_path_generator ──► FIN

Cada nodo es un agente independiente que recibe el estado completo (AgentState)
y devuelve un diccionario de estado parcial con sus propias actualizaciones.
"""

from __future__ import annotations
from langgraph.graph import END, StateGraph

from agents.pdf_parser_agent import pdf_parser_node
from agents.skill_extraction_agent import skill_extraction_node
from agents.course_matching_agent import course_matching_node
from agents.learning_path_agent import learning_path_node
from core.state import AgentState
from utils.logger import logger


def _should_stop_on_error(state: AgentState) -> str:
    """Arista condicional: detiene el pipeline si ocurre un error crítico."""
    errors = state.get("errors", [])
    current_step = state.get("current_step", "")
    if errors and current_step in ("pdf_parser", "skill_extractor"):
        logger.warning("Error crítico detectado en {} – abortando el pipeline.", current_step)
        return "end"
    return "continue"


def build_graph() -> StateGraph:
    """Construye y compila el flujo de agentes."""
    graph = StateGraph(AgentState)

    # ── Registro de nodos ────────────────────────────────────────────────
    graph.add_node("pdf_parser", pdf_parser_node)
    graph.add_node("skill_extractor", skill_extraction_node)
    graph.add_node("course_matcher", course_matching_node)
    graph.add_node("learning_path_generator", learning_path_node)

    # ── Punto de entrada ─────────────────────────────────────────────────
    graph.set_entry_point("pdf_parser")

    # ── Conexiones (Aristas) ──────────────────────────────────────────────
    graph.add_conditional_edges(
        "pdf_parser",
        _should_stop_on_error,
        {"end": END, "continue": "skill_extractor"},
    )
    graph.add_conditional_edges(
        "skill_extractor",
        _should_stop_on_error,
        {"end": END, "continue": "course_matcher"},
    )
    graph.add_edge("course_matcher", "learning_path_generator")
    graph.add_edge("learning_path_generator", END)

    return graph.compile()


# Singleton del grafo compilado utilizado por la API
cv_analysis_graph = build_graph()
