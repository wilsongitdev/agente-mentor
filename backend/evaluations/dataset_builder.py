"""
Constructor del Dataset de Evaluación (LangSmith Dataset Builder)

Este script automatiza la creación y actualización de un dataset de prueba robusto en LangSmith.
Incluye casos de prueba realistas ("Junior", "Senior en Transición", "Cambio de Carrera")
con ruido simulado (saltos de línea, caracteres especiales) para estresar el motor de
extracción de habilidades del agente.
"""

import os
from langsmith import Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure LangSmith
client = Client()
DATASET_NAME = "Skill Extraction Quality - Agente Mentor"

EXAMPLES = [
    # Case 1: The "Junior with Potential"
    {
        "inputs": {
            "cv_text": """
ANA GARCÍA | Estudiante de Ingeniería\n
----------------------------------------\r\n
Página 1 de 1\r\n\n
EXPERIENCIA:\n
* Pasante de TI en 'Tech Solution' (Junio 2023 - Diciembre 2023)\n
  - Apoyo en automatización con Pyth on\n
  - Consultas básicas SQL | Reportes Excel\n\n
CURSOS:\n
• Python for Data Science\r\n
• SQL Fundamental (Coursera)\n
            """,
            "professional_objective": "Data Analyst"
        },
        "outputs": {
            "candidate_name": "Ana García",
            "seniority_level": "junior",
            "years_total_experience": 1.0,
            "current_skills": [
                {
                    "name": "Python",
                    "category": "Programming Languages",
                    "level": "beginner",
                    "type": "explicita",
                    "justification": "Menciona apoyo en automatización con Python durante su pasantía."
                },
                {
                    "name": "SQL",
                    "category": "Databases",
                    "level": "beginner",
                    "type": "explicita",
                    "justification": "Realizó consultas básicas SQL en su experiencia laboral y tiene cursos certificados."
                },
                {
                    "name": "Excel",
                    "category": "Data Analysis",
                    "level": "beginner",
                    "type": "explicita",
                    "justification": "Menciona reportes en Excel."
                }
            ],
            "suggested_skills": [
                {
                    "name": "Pandas",
                    "reason": "Herramienta esencial en Python para cualquier analista de datos junior.",
                    "priority": "high"
                },
                {
                    "name": "Power BI",
                    "reason": "Frecuentemente solicitado para visualización de datos junto con SQL y Python.",
                    "priority": "medium"
                }
            ],
            "profile_summary": "Estudiante de ingeniería con bases en Python y SQL, con una primera experiencia en pasantía técnica."
        }
    },
    # Case 2: The "Senior in Transition"
    {
        "inputs": {
            "cv_text": """
CARLOS MENDOZA\r\n
SR. SOFTWARE ARCHITECT | JAVA EXPERT\r\n
\n
8+ Años de experiencia en desarrollo backend robusto.\n\n
PROYECTOS CLAVE:\n
| Empresa A | 2018 - Presente | Leads Backend Team\n
- Migración a Spring Boot & Kubernetes\r\n
- Diseño de microservicios con PostgreSQL\r\n
\n
Página 2 / 3\r\n
| Empresa B | 2016 - 2018 | Software Engineer\n
- Java EE, XML, WebSphere\n
            """,
            "professional_objective": "Machine Learning Engineer"
        },
        "outputs": {
            "candidate_name": "Carlos Mendoza",
            "seniority_level": "senior",
            "years_total_experience": 8.0,
            "current_skills": [
                {
                    "name": "Java",
                    "category": "Programming Languages",
                    "level": "advanced",
                    "type": "explicita",
                    "justification": "Ocho años de experiencia y rol de arquitecto experto."
                },
                {
                    "name": "Spring Boot",
                    "category": "Frameworks",
                    "level": "advanced",
                    "type": "explicita",
                    "justification": "Menciona migración y diseño de microservicios con esta tecnología."
                },
                {
                    "name": "PostgreSQL",
                    "category": "Databases",
                    "level": "advanced",
                    "type": "explicita",
                    "justification": "Diseño de base de datos relacional para microservicios."
                },
                {
                    "name": "Kubernetes",
                    "category": "Cloud & DevOps",
                    "level": "intermediate",
                    "type": "explicita",
                    "justification": "Experiencia en migración a K8s."
                }
            ],
            "suggested_skills": [
                {
                    "name": "PyTorch",
                    "reason": "Fundamento necesario para la transición hacia roles de deep learning e ingeniería de modelos.",
                    "priority": "high"
                },
                {
                    "name": "Scikit-learn",
                    "reason": "Indispensable para dominar el machine learning clásico antes de especializarse.",
                    "priority": "high"
                },
                {
                    "name": "MLOps",
                    "reason": "Excelente oportunidad para apalancar su experiencia en K8s y DevOps en el ciclo de vida de modelos IA.",
                    "priority": "medium"
                }
            ],
            "profile_summary": "Arquitecto backend senior con sólida base en Java y microservicios, buscando pivotar hacia IA."
        }
    },
    # Case 3: The "Career Reorientation"
    {
        "inputs": {
            "cv_text": """
ELENA TORRES\n
CHEF EJECUTIVO | ADMINISTRACIÓN GASTRONÓMICA\r\n
------------------------------------------------\n
Email: elena.chef@mail.com | Medellín, Colombia\r\n
EXPERIENCIA (5 Años):\n
* Restaurante 'Sol y Mar' (2019 - Presente)\r\n
  - Liderazgo de equipo de cocina (12 personas)\n
  - Control de costos, inventarios y compras\r\n
  - Optimización de procesos operativos\n
\n
Nota: Apasionada por la tecnología y la automatización de procesos.\n
            """,
            "professional_objective": "AI Engineer"
        },
        "outputs": {
            "candidate_name": "Elena Torres",
            "seniority_level": "junior",
            "years_total_experience": 0.0,
            "current_skills": [
                {
                    "name": "Liderazgo de Equipos",
                    "category": "Soft Skills",
                    "level": "advanced",
                    "type": "explicita",
                    "justification": "Cinco años como chef ejecutivo liderando equipos de 12 personas."
                },
                {
                    "name": "Optimización de Procesos",
                    "category": "General Skills",
                    "level": "intermediate",
                    "type": "explicita",
                    "justification": "Menciona explícitamente haber optimizado procesos operativos en el restaurante."
                }
            ],
            "suggested_skills": [
                {
                    "name": "Python",
                    "reason": "Lenguaje de programación fundamental para cualquier aspirante a Ingeniero de IA.",
                    "priority": "high"
                },
                {
                    "name": "Matemáticas para IA",
                    "reason": "Sólida base necesaria para entender algoritmos de ML desde cero.",
                    "priority": "medium"
                }
            ],
            "profile_summary": "Profesional con amplia experiencia en gestión operativa y liderazgo en el sector gastronómico, iniciando transición a IA."
        }
    },
    # Case 4: The AI Specialist (User Example)
    {
        "inputs": {
            "cv_text": """
ING. ROBERTO SALAZAR\n
Especialista en IA y Visión por Computadora\r\n
\n
EXPERIENCIA PROFESIONAL (4 Años):\n
1. Senior AI Developer @ DeepVision (2022-2024)\n
   - Generación de video con IA | Optimizacion de telecomunicaciones\r\n
2. Data Scientist @ Telecom Corp (2020-2022)\n
   - Análisis de datos masivos\r\n
\n
EDUCACIÓN:\n
- Maestría en Inteligencia Artificial\n
- Ingeniería Electrónica\n
            """,
            "professional_objective": "Senior AI Architect"
        },
        "outputs": {
            "candidate_name": "Roberto Salazar",
            "seniority_level": "mid",
            "years_total_experience": 4.0,
            "current_skills": [
                {
                    "name": "IA y Visión por Computadora",
                    "category": "Artificial Intelligence",
                    "level": "advanced",
                    "type": "explicita",
                    "justification": "Menciona posgrado en IA y años de experiencia como AI Developer Senior."
                },
                {
                    "name": "Visión Artificial",
                    "category": "Artificial Intelligence",
                    "level": "advanced",
                    "type": "explicita",
                    "justification": "Especialista en este dominio."
                }
            ],
            "suggested_skills": [
                {
                    "name": "AWS",
                    "priority": "high",
                    "reason": "Complementar su conocimiento de cloud con otra plataforma importante en el mercado"
                },
                {
                    "name": "Apache Spark",
                    "priority": "medium",
                    "reason": "Fortalecer sus capacidades de procesamiento de big data"
                },
                {
                    "name": "MLOps",
                    "priority": "high",
                    "reason": "Mejorar sus habilidades de despliegue y gestión de modelos de IA"
                }
            ],
            "profile_summary": "Ingeniero electrónico con maestría en Inteligencia Artificial, con experiencia en desarrollo de soluciones de IA, análisis de datos y visión por computadora. Ha trabajado en proyectos que van desde optimización de telecomunicaciones hasta generación de video con IA, mostrando versatilidad y capacidad de adaptación en diferentes dominios tecnológicos."
        }
    }
]

def build_dataset():
    """
    Crea o actualiza el dataset de evaluación en la plataforma LangSmith.
    
    Limpia los ejemplos existentes para asegurar que las métricas se calculen
    sobre la versión más reciente de la "Verdad Terrenal" (Ground Truth).
    """
    
    # Check if dataset already exists
    try:
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
        print(f"Dataset '{DATASET_NAME}' ya existe (id: {dataset.id}).")
        
        # --- NUEVO: Limpieza de ejemplos existentes para evitar duplicados ---
        print("   🧹 Limpiando ejemplos anteriores para evitar duplicados...")
        existing_examples = client.list_examples(dataset_id=dataset.id)
        for example in existing_examples:
            client.delete_example(example.id)
            
    except Exception:
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description="Dataset robusto para evaluación de extracción de habilidades con ruido."
        )
        print(f"Dataset '{DATASET_NAME}' creado exitosamente (id: {dataset.id}).")

    # Add examples
    print(f"   📤 Subiendo {len(EXAMPLES)} ejemplos frescos...")
    for example in EXAMPLES:
        client.create_example(
            inputs=example["inputs"],
            outputs=example["outputs"],
            dataset_id=dataset.id
        )
    
    print("\n   ¡Completado!")
    print(f"   👉 Dataset limpio en: https://smith.langchain.com/datasets/{dataset.id}")

if __name__ == "__main__":
    build_dataset()
