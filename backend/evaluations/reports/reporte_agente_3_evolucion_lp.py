import os
from langsmith import Client
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()

def generate_report():
    client = Client()
    # Nombre de tu dataset maestro
    dataset_name = "Skill Extraction Quality - Agente Mentor"
    
    print("Conectando con LangSmith para extraer métricas...")
    
    try:
        all_projects = list(client.list_projects())
        # Filtrar manualmente por dataset o por prefijo para ser más robustos
        projects = [p for p in all_projects if p.name.startswith("iter-")]
        
        if not projects:
            print("Proyectos totales encontrados en tu cuenta:", [p.name for p in all_projects[:10]])
    except Exception as e:
        print(f"Error conectando a LangSmith: {e}")
        return
    
    data = []
    for p in projects:
        print(f"   [INFO] Procesando '{p.name}'...")
        
        # En lugar de stats pre-calculados (que tardan), calculamos promedios manualmente
        feedbacks = list(client.list_feedback(project_name=p.name))
        
        if not feedbacks:
            print(f"      ⚠️ No se encontró feedback para '{p.name}'.")
            continue
            
        # Agrupar y promediar por llave (key)
        scores_by_key = {}
        for f in feedbacks:
            if f.score is not None:
                key = f.key
                if key not in scores_by_key:
                    scores_by_key[key] = []
                scores_by_key[key].append(f.score)
        
        # Calcular promedios
        logical_order = sum(scores_by_key.get("logical_order", [0])) / len(scores_by_key.get("logical_order", [1]))
        path_effectiveness = sum(scores_by_key.get("path_effectiveness", [0])) / len(scores_by_key.get("path_effectiveness", [1]))
        
        # Nombre limpio para la gráfica
        import re
        # Limpiar el hash de id del nombre (ej: -ab731fc7)
        clean_name = re.sub(r"-[a-f0-9]{8}$", "", p.name)
        display_name = clean_name.replace("iter-", "").replace("-", " ").title()
        
        # Fecha de creación (compatibilidad entre versiones del SDK)
        created_at = getattr(p, "created_at", getattr(p, "start_time", None))
        
        data.append({
            "Iteración": display_name,
            "Orden Lógico": round(logical_order, 2),
            "Efectividad de Ruta": round(path_effectiveness, 2),
            "created_at": created_at
        })
            
    if not data:
        print("⚠️ No se encontraron experimentos que empiecen con 'iter-'.")
        print("Por favor, ejecuta '.\\run_lp_experiments.ps1' primero.")
        return
        
    df = pd.DataFrame(data)
    # Ordenar cronológicamente y quedarse con la última versión de cada iteración
    df = df.sort_values("created_at").drop_duplicates(subset="Iteración", keep="last")
    
    # Asegurar el orden lógico (1, 2, 3) si es que el nombre empieza por número
    df = df.sort_values("Iteración")
    
    print("\n=== RESUMEN DE EVOLUCIÓN (TABLA MAESTRA) ===")
    print(df[["Iteración", "Orden Lógico", "Efectividad de Ruta"]].to_string(index=False))
    
    # --- DIBUJAR LA GRÁFICA ---
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Estilo moderno (oscuro como el real-world report)
    fig.patch.set_facecolor('#1A1A2E')
    ax.set_facecolor('#16213E')
    
    df.plot(
        x="Iteración", 
        y=["Orden Lógico", "Efectividad de Ruta"], 
        kind="bar", 
        ax=ax,
        color=['#7B61FF', '#00C4B6'],
        width=0.6,
        alpha=0.9,
        edgecolor='#1A1A2E'
    )
    
    # Título y etiquetas
    plt.title("Evolución del Agente Mentor (Mejoras Arquitectónicas)\nComparativa de Calidad en el Generador de Rutas", 
              fontsize=20, fontweight='bold', pad=30, color='white')
    plt.ylabel("Score del Juez LLM (0.0 a 1.0)", fontsize=15, color='white', fontweight='bold')
    plt.xlabel("")
    plt.ylim(0, 1.22)
    
    # Línea de meta destacada
    plt.axhline(y=0.85, color='#F1C40F', linestyle='--', linewidth=2.5, label='Meta de Aceptación (0.85)', alpha=0.8)
    
    # Estilizado de ejes
    plt.xticks(rotation=0, fontsize=15, color='white', fontweight='bold')
    plt.yticks(fontsize=13, color='white')
    ax.tick_params(colors='white')
    ax.spines['bottom'].set_color('#444')
    ax.spines['left'].set_color('#444')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.grid(axis='y', linestyle='--', alpha=0.15, color='white')
    
    # Leyenda clara en la parte inferior
    legend = plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15),
                        ncol=3, fontsize=13, frameon=True, 
                        facecolor='#1A1A2E', edgecolor='#444')
    plt.setp(legend.get_texts(), color='white')
    
    # Anotar valores en las barras con mayor visibilidad
    for container in ax.containers:
        # Solo anotar las barras
        if hasattr(container, 'patches'):
            ax.bar_label(container, fmt='%.2f', padding=5, color='white', fontweight='bold', fontsize=15)

    plt.tight_layout()
    
    # Guardar imagen
    out_file = "2_evolucion_arquitectura_pedagogica.png"
    plt.savefig(out_file, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f"\n[SUCCESS] Grafica optimizada generada y guardada en:\n{os.path.abspath(out_file)}")

if __name__ == "__main__":
    generate_report()
