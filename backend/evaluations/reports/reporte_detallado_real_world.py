"""
Generador de Gráfica y Conclusiones para la Evaluación Real-World.

Lee el experimento más reciente del dataset 'Real-World-CVs-LinkedIn'
en LangSmith y genera:
  1. Gráfica de barras agrupadas con las 6 métricas por CV
  2. Tabla resumen en consola
  3. Bloque de Conclusiones automáticas para tu presentación

Uso:
    cd backend
    python -m evaluations.reports.generate_real_world_report
"""
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from dotenv import load_dotenv
from langsmith import Client

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
DATASET_NAME = "Real-World-CVs-LinkedIn"

METRICS = [
    "technical_fidelity",
    "gap_pertinence",
    "seniority_consistency",
    "path_effectiveness",
    "logical_order",
    "overall_mentor_quality",
]

METRIC_LABELS = {
    "technical_fidelity":     "Fidelidad\nTécnica",
    "gap_pertinence":         "Pertinencia\nBrechas",
    "seniority_consistency":  "Consistencia\nSeniority",
    "path_effectiveness":     "Eficacia\nRuta",
    "logical_order":          "Orden\nLógico",
    "overall_mentor_quality": "Calidad\nMentor E2E",
}

METRIC_COLORS = {
    "technical_fidelity":     "#4A90D9",
    "gap_pertinence":         "#7B61FF",
    "seniority_consistency":  "#00C4B6",
    "path_effectiveness":     "#FF7B61",
    "logical_order":          "#FFB800",
    "overall_mentor_quality": "#28B463",
}
# ─────────────────────────────────────────────────────────────────────────────


def _get_latest_experiment(client: Client) -> str | None:
    """Devuelve el nombre del experimento más reciente del dataset."""
    all_projects = list(client.list_projects())
    rw_projects = [
        p for p in all_projects
        if "real-world-linkedin" in p.name.lower()
    ]
    if not rw_projects:
        return None
    latest = sorted(
        rw_projects,
        key=lambda p: getattr(p, "start_time", getattr(p, "created_at", None)) or "",
        reverse=True,
    )[0]
    return latest.name


def _collect_scores(client: Client, project_name: str) -> dict[str, dict[str, float]]:
    """
    Devuelve {run_id: {metric: score}} para todos los runs del experimento.
    """
    feedbacks = list(client.list_feedback(project_name=project_name))
    runs = {r.id: r for r in client.list_runs(project_name=project_name)}

    scores_per_run: dict[str, dict[str, float]] = defaultdict(dict)
    for fb in feedbacks:
        if fb.score is not None and fb.key in METRICS:
            scores_per_run[str(fb.run_id)][fb.key] = float(fb.score)

    return scores_per_run


def _get_run_label(client: Client, run_id: str, project_name: str) -> str:
    """Obtiene una etiqueta legible para el run (nombre del candidato o archivo)."""
    try:
        run = client.read_run(run_id)
        outputs = run.outputs or {}
        # Preferir el nombre del candidato detectado por el agente
        name = outputs.get("candidate_name") or ""
        if name and name != "N/A":
            return name.split()[0]  # Solo el primer nombre para brevedad
        # Fallback: usar el filename del input
        inputs = run.inputs or {}
        filename = inputs.get("filename", f"CV_{run_id[:6]}")
        return Path(filename).stem.split("_")[0]
    except Exception:
        return f"CV_{run_id[:6]}"


def generate_real_world_report():
    client = Client()

    print("\nConectando con LangSmith...")

    # 1. Encontrar experimento
    project_name = _get_latest_experiment(client)
    if not project_name:
        print("⚠️  No se encontraron experimentos del dataset 'Real-World-CVs-LinkedIn'.")
        print("     Ejecuta primero: python -m evaluations.real_world.run_real_world_eval")
        return

    print(f"   [INFO] Experimento encontrado: '{project_name}'")

    # 2. Recopilar scores
    scores_per_run = _collect_scores(client, project_name)
    if not scores_per_run:
        print("[WARNING] No se encontraron metricas de feedback. Verifica que la evaluacion se completo.")
        return

    # 3. Obtener etiquetas de CV
    run_labels = {}
    for run_id in scores_per_run:
        run_labels[run_id] = _get_run_label(client, run_id, project_name)

    # 4. Construir matriz de datos
    run_ids = list(scores_per_run.keys())
    labels = [run_labels.get(rid, rid[:6]) for rid in run_ids]

    # ── TABLA RESUMEN EN CONSOLA ──────────────────────────────────────────────
    print(f"\n{'='*75}")
    print("  RESUMEN DE EVALUACIÓN: CVs REALES DE LINKEDIN")
    print(f"{'='*75}")
    header = f"{'CV':<22}" + "".join(f"{METRIC_LABELS[m].replace(chr(10), ' '):<22}" for m in METRICS)
    print(header)
    print("-" * 75)

    all_scores: dict[str, list[float]] = defaultdict(list)
    for run_id, label in zip(run_ids, labels):
        row = f"{label:<22}"
        for m in METRICS:
            s = scores_per_run[run_id].get(m, None)
            if s is not None:
                row += f"{s:<22.2f}"
                all_scores[m].append(s)
            else:
                row += f"{'N/A':<22}"
        print(row)

    print("-" * 75)
    avg_row = f"{'PROMEDIO SISTEMA':<22}"
    system_averages = {}
    for m in METRICS:
        if all_scores[m]:
            avg = sum(all_scores[m]) / len(all_scores[m])
            system_averages[m] = avg
            avg_row += f"{avg:<22.2f}"
        else:
            avg_row += f"{'N/A':<22}"
    print(avg_row)
    print(f"{'='*75}\n")

    # ── GRÁFICA (Estilo Moderno High-Legibility) ──────────────────────────────
    n_cvs = len(run_ids)
    n_metrics = len(METRICS)
    x = np.arange(n_cvs)
    bar_width = 0.12
    offsets = np.linspace(-(n_metrics - 1) / 2, (n_metrics - 1) / 2, n_metrics) * bar_width

    fig, ax = plt.subplots(figsize=(max(14, n_cvs * 2.5), 8))
    fig.patch.set_facecolor("#1A1A2E")
    ax.set_facecolor("#16213E")

    for i, (metric, offset) in enumerate(zip(METRICS, offsets)):
        values = [scores_per_run[rid].get(metric, 0) for rid in run_ids]
        bars = ax.bar(
            x + offset, values, bar_width,
            label=METRIC_LABELS[metric].replace("\n", " "),
            color=METRIC_COLORS[metric],
            alpha=0.9,
            edgecolor="white",
            linewidth=0.3,
        )
        # Etiquetas encima de cada barra con fuente legible
        for bar in bars:
            h = bar.get_height()
            if h >= 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    h + 0.015,
                    f"{h:.1f}",
                    ha="center", va="bottom",
                    color="white", fontsize=12, fontweight="bold"
                )

    # Línea de meta destacada
    ax.axhline(y=0.85, color="#F1C40F", linestyle="--", alpha=0.8, linewidth=2.5, label="Meta Calidad (0.85)")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, color="white", fontsize=15, fontweight='bold')
    ax.set_ylim(0, 1.18)
    ax.set_ylabel("Score del Juez LLM (0.0 – 1.0)", color="white", fontsize=15, fontweight='bold')
    ax.tick_params(axis='y', colors="white", labelsize=13)
    
    # Estilizado de bordes
    ax.spines["bottom"].set_color("#444")
    ax.spines["left"].set_color("#444")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.15, color="white")

    plt.title(
        "Métricas Detalladas por Candidato (LinkedIn Real-World)\nDesempeño End-to-End del Agente Mentor",
        color="white", fontsize=22, fontweight="bold", pad=30
    )
    
    # Leyenda clara en la parte inferior
    legend = ax.legend(
        loc="upper center", bbox_to_anchor=(0.5, -0.15),
        ncol=4, frameon=True, 
        facecolor="#1A1A2E", edgecolor="#444",
        fontsize=12
    )
    plt.setp(legend.get_texts(), color='white')

    plt.tight_layout()

    out_path = Path(__file__).parent.parent.parent / "3_evaluacion_detallada_cvs_reales.png"
    plt.savefig(str(out_path), dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"[OK] Grafica guardada en:\n   {out_path}\n")

    # ── CONCLUSIONES AUTOMÁTICAS ──────────────────────────────────────────────
    if system_averages:
        best_metric = max(system_averages, key=system_averages.get)
        worst_metric = min(system_averages, key=system_averages.get)
        global_avg = sum(system_averages.values()) / len(system_averages)

        verdict = "APROBADO [OK]" if global_avg >= 0.75 else "REQUIERE MEJORA [!!]"

        print(f"{'='*65}")
        print("  CONCLUSIONES AUTOMÁTICAS — PARA TU PRESENTACIÓN")
        print(f"{'='*65}")
        print(f"  Score Global del Sistema:   {global_avg:.2f}/1.00  →  {verdict}")
        print(f"  Métrica más fuerte:         {METRIC_LABELS[best_metric].replace(chr(10), ' ')} ({system_averages[best_metric]:.2f})")
        print(f"  Métrica más débil:          {METRIC_LABELS[worst_metric].replace(chr(10), ' ')} ({system_averages[worst_metric]:.2f})")
        print(f"  CVs evaluados:              {n_cvs}")
        print(f"  Experimento LangSmith:      {project_name}")
        print(f"{'='*65}\n")


if __name__ == "__main__":
    generate_real_world_report()
