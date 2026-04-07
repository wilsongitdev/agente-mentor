import os
import re
from langsmith import Client
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()

def generate_e2e_report():
    client = Client()
    # En run_e2e_eval usabas el mismo dataset o a veces se crea uno nuevo.
    # Buscaremos todos los proyectos E2E
    print("Conectando con LangSmith para extraer métricas End-to-End (E2E)...")
    
    try:
        all_projects = list(client.list_projects())
        # Filtrar proyectos que contengan e2e y que coincidan con las versiones oficiales
        allowed_prefixes = ["e2e-baseline", "e2e-final-arch"]
        projects = [
            p for p in all_projects 
            if any(p.name.lower().startswith(prefix) for prefix in allowed_prefixes)
        ]
        
        if not projects:
            print("⚠️ No se encontró ningún proyecto de evaluación E2E oficial.")
            print(f"Buscados: {allowed_prefixes}")
            return
            
    except Exception as e:
        print(f"Error conectando a LangSmith: {e}")
        return
    
    data = []
    
    # Procesaremos máximo 4 para que la gráfica se vea bien
    projects = sorted(projects, key=lambda x: getattr(x, "start_time", getattr(x, "created_at", None)) or "", reverse=True)[:4]
    
    for p in reversed(projects):
        print(f"   [INFO] Procesando '{p.name}'...")
        feedbacks = list(client.list_feedback(project_name=p.name))
        runs = list(client.list_runs(project_name=p.name))
        
        if not feedbacks and not runs:
            print(f"      ⚠️ No se encontraron datos para este proyecto.")
            continue
            
        scores_by_key = {}
        for f in feedbacks:
            if f.score is not None:
                key = f.key
                if key not in scores_by_key:
                    scores_by_key[key] = []
                scores_by_key[key].append(f.score)
        
        # Calcular latencia (segundos) y costo aproximado
        total_latency = 0
        total_tokens = 0
        run_count = len(runs) if len(runs) > 0 else 1
        
        for r in runs:
            if getattr(r, 'start_time', None) and getattr(r, 'end_time', None):
                latency = (r.end_time - r.start_time).total_seconds()
                total_latency += latency
            
            # LangSmith acumula los tokens en r.total_tokens o extra fields
            if hasattr(r, 'total_tokens') and r.total_tokens:
                total_tokens += r.total_tokens
            elif r.extra and "total_tokens" in r.extra:
                total_tokens += r.extra["total_tokens"]

        avg_latency = total_latency / run_count
        avg_tokens = total_tokens / run_count
        # Costo aprox por sesión (asumiendo GPT-4o-mini o GPT-3.5: ~$0.5 / 1M tokens = $0.0005 por 1k)
        # Esto es referencial para la gráfica
        costo_promedio_centavos = (avg_tokens / 1000) * 0.05 
            
        mentor_quality = sum(scores_by_key.get("overall_mentor_quality", [0])) / len(scores_by_key.get("overall_mentor_quality", [1]))
        
        # Nombre limpio
        clean_name = re.sub(r"-[a-f0-9]{8}$", "", p.name)
        display_name = clean_name.replace("eval-e2e-", "E2E ").title()
        
        created_at = getattr(p, "created_at", getattr(p, "start_time", None))
        
        data.append({
            "Experimento": display_name,
            "Calidad Mentor": round(mentor_quality, 2),
            "Latencia (s)": round(avg_latency, 1),
            "Costo (c)": round(costo_promedio_centavos, 2),
            "Tokens": int(avg_tokens),
            "created_at": created_at
        })
            
    if not data:
        print("⚠️ No existen suficientes datos E2E.")
        return
        
    df = pd.DataFrame(data)
    # Ordenar cronológicamente y quedarse con la última versión de cada experimento
    df = df.sort_values("created_at").drop_duplicates(subset="Experimento", keep="last")
    
    print("\n=== RESUMEN SISTEMA COMPLETO (E2E) ===")
    print(df[["Experimento", "Calidad Mentor", "Latencia (s)", "Costo (c)"]].to_string(index=False))
    
    # --- DIBUJAR LA GRÁFICA (Eje dual con estilo moderno) ---
    fig, ax1 = plt.subplots(figsize=(12, 7))
    
    # Estilo oscuro
    fig.patch.set_facecolor('#1A1A2E')
    ax1.set_facecolor('#16213E')
    
    # Eje 1: Calidad (Barras)
    color_calidad = '#28B463'
    bars = ax1.bar(
        df["Experimento"], 
        df["Calidad Mentor"], 
        color=color_calidad,
        width=0.4,
        alpha=0.8,
        label='Calidad E2E (Score)'
    )
    
    ax1.set_ylabel("Calidad E2E (0.0 a 1.0)", color=color_calidad, fontsize=14, fontweight='bold')
    ax1.set_ylim(0, 1.15)
    ax1.tick_params(axis='y', labelcolor=color_calidad, labelsize=13)
    ax1.axhline(y=0.85, color=color_calidad, linestyle='--', alpha=0.4, label='Meta Calidad (0.85)')
    
    # Eje 2: Latencia (Línea)
    ax2 = ax1.twinx()
    color_latencia = '#E67E22'
    ax2.plot(
        df["Experimento"],
        df["Latencia (s)"],
        color=color_latencia,
        marker='o',
        linewidth=3,
        markersize=10,
        label='Latencia (Segundos)',
        markerfacecolor='white'
    )
    
    ax2.set_ylabel("Tiempo de Respuesta (Segundos)", color=color_latencia, fontsize=14, fontweight='bold')
    ax2.set_ylim(0, max(df["Latencia (s)"].max() * 1.4, 25))
    ax2.tick_params(axis='y', labelcolor=color_latencia, labelsize=13)
    
    # Título y etiquetas
    plt.title("Performance Integral del Agente Mentor AI\nComparativa Calidad vs. Latencia (E2E Real-World)", 
              fontsize=20, fontweight='bold', pad=30, color='white')
    ax1.set_xlabel("")
    ax1.tick_params(axis='x', rotation=0, colors='white', labelsize=14)
    
    # Unificar leyendas
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    legend = ax1.legend(lines1 + lines2, labels1 + labels2, 
                        loc='upper center', bbox_to_anchor=(0.5, -0.15),
                        ncol=3, fontsize=13, frameon=True, 
                        facecolor='#1A1A2E', edgecolor='#444')
    plt.setp(legend.get_texts(), color='white')
    
    # Estilizado
    for ax in [ax1, ax2]:
        ax.spines['top'].set_visible(False)
        ax.grid(axis='y', linestyle='--', alpha=0.1, color='white')
    
    # Anotar calidad (Dentro de la barra para evitar solapamientos con la latencia)
    ax1.bar_label(bars, fmt='%.2f', label_type='center', color='white', fontweight='bold', fontsize=18)
    
    # Anotar tokens en la base de las barras
    for idx, row in df.iterrows():
        token_str = f"{row['Tokens']/1000:.1f}k\ntokens"
        ax1.text(idx, 0.05, token_str, ha='center', va='bottom', 
                 color='white', fontsize=13, fontweight='bold', alpha=0.9)

    # Anotar latencia (burbujas elevadas para evitar solapamientos)
    for idx, val in enumerate(df["Latencia (s)"]):
        ax2.annotate(f"{val}s", 
                     xy=(idx, val), 
                     xytext=(0, 25), 
                     textcoords="offset points",
                     ha='center', va='bottom', 
                     color=color_latencia, 
                     fontweight='bold',
                     fontsize=15,
                     bbox=dict(boxstyle='round,pad=0.4', fc='#1A1A2E', ec=color_latencia, alpha=0.9))

    plt.tight_layout()
    
    out_file = "4_rendimiento_sistema_completo.png"
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), out_file)
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    print(f"\n[SUCCESS] Grafica combinada generada y guardada en:\n{out_path}")

if __name__ == "__main__":
    generate_e2e_report()
