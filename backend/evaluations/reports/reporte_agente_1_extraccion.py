import os
import re
from langsmith import Client
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()

def generate_skills_report():
    client = Client()
    dataset_name = "Skill Extraction Quality - Agente Mentor"
    
    print("Conectando con LangSmith para extraer métricas del Agente 1 (Extracción)...")
    
    try:
        all_projects = list(client.list_projects())
        # Filtramos los proyectos que evalúan el Agente 1 (Skill Extraction)
        # Buscar por palabras clave como "skill", "prompt-se", "se-", "se_v"
        projects = []
        for p in all_projects:
            name = p.name.lower()
            if any(key in name for key in ["skill", "prompt-se", "se-", "se_v"]):
                # Excluir explícitamente los del path (Agente 3)
                if "path" not in name and "iter-" not in name:
                    projects.append(p)
                    
        if not projects:
            # Fallback a los últimos 10 si no hay matches estrictos
            projects = all_projects[:10]
            print(f"⚠️ Procesando proyectos de fallback ({len(projects)} encontrados)...")
            
    except Exception as e:
        print(f"Error conectando a LangSmith: {e}")
        return
    
    data = []
    
    # Ordenar por fecha y tomar los últimos 4
    projects = sorted(projects, key=lambda x: getattr(x, "start_time", getattr(x, "created_at", None)) or "", reverse=True)[:4]
    
    for p in reversed(projects):
        print(f"   [INFO] Procesando '{p.name}'...")
        feedbacks = list(client.list_feedback(project_name=p.name))
        
        if not feedbacks:
            print(f"      ⚠️ Sin feedback.")
            continue
            
        scores_by_key = {}
        for f in feedbacks:
            if f.score is not None:
                key = f.key
                if key not in scores_by_key:
                    scores_by_key[key] = []
                scores_by_key[key].append(f.score)
        
        # Validar métricas mínimas para considerarlo del Agente 1
        if "technical_fidelity" not in scores_by_key and "gap_pertinence" not in scores_by_key:
            continue
            
        # Calcular promedios
        technical_fidelity = sum(scores_by_key.get("technical_fidelity", [0])) / len(scores_by_key.get("technical_fidelity", [1]))
        gap_pertinence = sum(scores_by_key.get("gap_pertinence", [0])) / len(scores_by_key.get("gap_pertinence", [1]))
        seniority_consistency = sum(scores_by_key.get("seniority_consistency", [0])) / len(scores_by_key.get("seniority_consistency", [1]))
        
        # Limpieza de nombre para la leyenda
        clean_name = re.sub(r"-[a-f0-9]{8}$", "", p.name)
        display_name = clean_name.replace("skill-extraction-eval-", "Iter ").replace("se-v", "V").replace("se_v", "V").replace("prompt-se-", "P-SE ").title()
        
        created_at = getattr(p, "created_at", getattr(p, "start_time", None))
        
        data.append({
            "Experimento": display_name,
            "Fidelidad": round(technical_fidelity, 2),
            "Brechas": round(gap_pertinence, 2),
            "Seniority": round(seniority_consistency, 2),
            "created_at": created_at
        })
            
    if not data:
        print("⚠️ No existen proyectos con métricas compatibles de Skill Extraction.")
        return
        
    df = pd.DataFrame(data)
    df = df.sort_values("created_at")
    
    print("\n=== RESUMEN EXTRACCIÓN (AGENTE 1) ===")
    print(df[["Experimento", "Fidelidad", "Brechas", "Seniority"]].to_string(index=False))
    
    # --- ESTILO MODERNO (DARK THEME) ---
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor('#1A1A2E')
    ax.set_facecolor('#16213E')
    
    # Dibujar Barras
    df.plot(
        x="Experimento", 
        y=["Fidelidad", "Brechas", "Seniority"], 
        kind="bar", 
        ax=ax,
        color=['#E74C3C', '#3498DB', '#9B59B6'], # Rojo, Azul, Púrpura
        width=0.8,
        alpha=0.85,
        edgecolor='white',
        linewidth=0.5
    )
    
    # Título y Etiquetas
    plt.title("Performance del Agente de Extracción de Habilidades\nCalidad Técnica y Consistencia de Seniority", 
              fontsize=16, fontweight='bold', pad=25, color='white')
    plt.ylabel("Score Promedio (0.0 a 1.0)", fontsize=13, color='white', fontweight='bold')
    plt.xlabel("")
    plt.ylim(0, 1.15)
    
    # Meta
    plt.axhline(y=0.85, color='#F1C40F', linestyle='--', label='Meta Calidad (0.85)', linewidth=2, alpha=0.8)
    
    # Configurar Ticks
    plt.xticks(rotation=0, fontsize=12, color='white', fontweight='bold')
    plt.yticks(fontsize=11, color='white')
    
    # Configurar Rejilla
    ax.grid(axis='y', linestyle='--', alpha=0.2, color='white')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#444')
    ax.spines['left'].set_color('#444')
    
    # Leyenda Optimizada
    legend = plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12),
                        ncol=4, fontsize=11, frameon=True, 
                        facecolor='#1A1A2E', edgecolor='#444')
    plt.setp(legend.get_texts(), color='white')
    
    # Anotar valores en barras
    for container in ax.containers:
        ax.bar_label(container, fmt='%.2f', padding=3, color='white', fontsize=14, fontweight='bold')

    plt.tight_layout()
    
    out_file = "1_rendimiento_extraccion_habilidades.png"
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), out_file)
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    print(f"\n[OK] Grafica guardada en:\n{out_path}")

if __name__ == "__main__":
    generate_skills_report()
