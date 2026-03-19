"""
Seed script – uploads the initial course catalog to Firebase
and rebuilds the vector index.

Usage:
    cd backend
    python db/seed_courses.py
"""

from __future__ import annotations

import sys
import os

# Make sure backend/ is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

COURSE_CATALOG = [
    # ── Python ────────────────────────────────────────────────────────────
    {
        "id": "py-001",
        "title": "Python para Principiantes – De Cero a Héroe",
        "provider": "Udemy",
        "url": "https://udemy.com/course/python-para-principiantes",
        "description": "Aprende Python desde cero. Variables, funciones, OOP, manejo de archivos y más.",
        "skills_covered": ["Python", "OOP", "Variables", "Funciones", "Archivos"],
        "level": "beginner",
        "duration_hours": 22.0,
        "category": "Programming Language",
        "language": "es",
        "rating": 4.7,
    },
    {
        "id": "py-002",
        "title": "Python Avanzado: Decoradores, Generators y Concurrencia",
        "provider": "Platzi",
        "url": "https://platzi.com/cursos/python-avanzado",
        "description": "Domina decorators, generators, context managers, asyncio y multiprocessing.",
        "skills_covered": ["Python", "asyncio", "Concurrencia", "Decoradores", "Generators"],
        "level": "advanced",
        "duration_hours": 14.0,
        "category": "Programming Language",
        "language": "es",
        "rating": 4.8,
    },
    # ── Machine Learning ──────────────────────────────────────────────────
    {
        "id": "ml-001",
        "title": "Machine Learning con Python y Scikit-learn",
        "provider": "Coursera",
        "url": "https://coursera.org/learn/machine-learning-python",
        "description": "Aprende regresión, clasificación, clustering y validación de modelos con scikit-learn.",
        "skills_covered": ["Machine Learning", "scikit-learn", "Python", "Estadística", "Pandas"],
        "level": "intermediate",
        "duration_hours": 40.0,
        "category": "Data Science / ML",
        "language": "es",
        "rating": 4.9,
    },
    {
        "id": "ml-002",
        "title": "Deep Learning con TensorFlow y Keras",
        "provider": "Udemy",
        "url": "https://udemy.com/course/deep-learning-tensorflow",
        "description": "Redes neuronales, CNNs, RNNs, Transfer Learning y despliegue de modelos.",
        "skills_covered": ["Deep Learning", "TensorFlow", "Keras", "CNNs", "RNNs", "Python"],
        "level": "advanced",
        "duration_hours": 35.0,
        "category": "Data Science / ML",
        "language": "es",
        "rating": 4.8,
    },
    {
        "id": "ml-003",
        "title": "MLOps: De Notebooks a Producción",
        "provider": "Platzi",
        "url": "https://platzi.com/cursos/mlops",
        "description": "CI/CD para ML, MLflow, DVC, Docker en pipelines de machine learning.",
        "skills_covered": ["MLOps", "MLflow", "DVC", "Docker", "CI/CD", "Python"],
        "level": "advanced",
        "duration_hours": 20.0,
        "category": "DevOps / Infrastructure",
        "language": "es",
        "rating": 4.7,
    },
    # ── Cloud / AWS ───────────────────────────────────────────────────────
    {
        "id": "aws-001",
        "title": "AWS Cloud Practitioner – Certificación Oficial",
        "provider": "Udemy",
        "url": "https://udemy.com/course/aws-certified-cloud-practitioner",
        "description": "Fundamentos de AWS: cómputo, almacenamiento, redes, seguridad y facturación.",
        "skills_covered": ["AWS", "Cloud", "S3", "EC2", "IAM", "VPC"],
        "level": "beginner",
        "duration_hours": 14.0,
        "category": "Cloud Platform",
        "language": "es",
        "rating": 4.8,
    },
    {
        "id": "aws-002",
        "title": "AWS Solutions Architect Associate",
        "provider": "A Cloud Guru",
        "url": "https://acloudguru.com/course/aws-certified-solutions-architect-associate",
        "description": "Diseña soluciones cloud escalables, seguras y rentables en AWS.",
        "skills_covered": ["AWS", "S3", "RDS", "Lambda", "CloudFormation", "ECS", "VPC"],
        "level": "intermediate",
        "duration_hours": 40.0,
        "category": "Cloud Platform",
        "language": "en",
        "rating": 4.9,
    },
    {
        "id": "aws-003",
        "title": "AWS Bedrock y Generative AI para Desarrolladores",
        "provider": "Udemy",
        "url": "https://udemy.com/course/aws-bedrock-generative-ai",
        "description": "Integra LLMs como Claude y Llama 2 en aplicaciones usando AWS Bedrock.",
        "skills_covered": ["AWS Bedrock", "LLMs", "Claude", "Generative AI", "Python", "boto3"],
        "level": "intermediate",
        "duration_hours": 12.0,
        "category": "Cloud Platform",
        "language": "es",
        "rating": 4.6,
    },
    # ── Data Engineering ──────────────────────────────────────────────────
    {
        "id": "de-001",
        "title": "Ingeniería de Datos con Apache Spark y PySpark",
        "provider": "Coursera",
        "url": "https://coursera.org/learn/data-engineering-spark",
        "description": "Procesamiento masivo de datos, Spark SQL, DataFrames y streaming.",
        "skills_covered": ["Apache Spark", "PySpark", "Big Data", "SQL", "Python"],
        "level": "intermediate",
        "duration_hours": 30.0,
        "category": "Data Science / ML",
        "language": "es",
        "rating": 4.7,
    },
    {
        "id": "de-002",
        "title": "Pipelines de Datos con Airflow y dbt",
        "provider": "Platzi",
        "url": "https://platzi.com/cursos/airflow-dbt",
        "description": "Orquesta pipelines de datos con Apache Airflow y transforma datos con dbt.",
        "skills_covered": ["Apache Airflow", "dbt", "ETL", "SQL", "Python", "Data Pipelines"],
        "level": "intermediate",
        "duration_hours": 18.0,
        "category": "Data Science / ML",
        "language": "es",
        "rating": 4.6,
    },
    # ── Backend / APIs ────────────────────────────────────────────────────
    {
        "id": "be-001",
        "title": "FastAPI Completo: APIs Modernas con Python",
        "provider": "Udemy",
        "url": "https://udemy.com/course/fastapi-completo",
        "description": "Construye APIs RESTful con FastAPI, Pydantic, autenticación JWT y despliegue.",
        "skills_covered": ["FastAPI", "Python", "REST APIs", "Pydantic", "JWT", "SQLAlchemy"],
        "level": "intermediate",
        "duration_hours": 20.0,
        "category": "Framework / Library",
        "language": "es",
        "rating": 4.9,
    },
    {
        "id": "be-002",
        "title": "Microservicios con Docker y Kubernetes",
        "provider": "Udemy",
        "url": "https://udemy.com/course/microservicios-docker-kubernetes",
        "description": "Diseña e implementa arquitecturas de microservicios usando Docker y K8s.",
        "skills_covered": ["Docker", "Kubernetes", "Microservicios", "DevOps", "CI/CD"],
        "level": "advanced",
        "duration_hours": 28.0,
        "category": "DevOps / Infrastructure",
        "language": "es",
        "rating": 4.8,
    },
    # ── LangChain / AI Agents ─────────────────────────────────────────────
    {
        "id": "ai-001",
        "title": "LangChain y LangGraph: Construye Agentes IA Avanzados",
        "provider": "Udemy",
        "url": "https://udemy.com/course/langchain-langgraph-agents",
        "description": "Crea sistemas multi-agente, RAG pipelines y flujos complejos con LangGraph.",
        "skills_covered": ["LangChain", "LangGraph", "LLMs", "RAG", "Python", "Agentes IA"],
        "level": "advanced",
        "duration_hours": 16.0,
        "category": "Framework / Library",
        "language": "es",
        "rating": 4.8,
    },
    {
        "id": "ai-002",
        "title": "Prompt Engineering: Domina los LLMs",
        "provider": "Platzi",
        "url": "https://platzi.com/cursos/prompt-engineering",
        "description": "Técnicas avanzadas de prompting: few-shot, chain-of-thought, structured output.",
        "skills_covered": ["Prompt Engineering", "LLMs", "GPT", "Claude", "OpenAI API"],
        "level": "intermediate",
        "duration_hours": 8.0,
        "category": "Data Science / ML",
        "language": "es",
        "rating": 4.7,
    },
    {
        "id": "ai-003",
        "title": "RAG Systems: Búsqueda Semántica y Vector Databases",
        "provider": "Udemy",
        "url": "https://udemy.com/course/rag-vector-databases",
        "description": "Implementa RAG con FAISS, Chroma, Pinecone y LangChain.",
        "skills_covered": ["RAG", "FAISS", "Chroma", "Embeddings", "LangChain", "Python"],
        "level": "intermediate",
        "duration_hours": 12.0,
        "category": "Framework / Library",
        "language": "es",
        "rating": 4.7,
    },
    # ── Frontend ──────────────────────────────────────────────────────────
    {
        "id": "fe-001",
        "title": "React con TypeScript – Curso Completo 2025",
        "provider": "Udemy",
        "url": "https://udemy.com/course/react-typescript-2025",
        "description": "React 18, hooks, context, React Query, Next.js y testing con Vitest.",
        "skills_covered": ["React", "TypeScript", "Next.js", "React Query", "Tailwind CSS"],
        "level": "intermediate",
        "duration_hours": 32.0,
        "category": "Framework / Library",
        "language": "es",
        "rating": 4.8,
    },
    # ── Databases ─────────────────────────────────────────────────────────
    {
        "id": "db-001",
        "title": "SQL y PostgreSQL: De Cero a Experto",
        "provider": "Platzi",
        "url": "https://platzi.com/cursos/postgresql",
        "description": "Diseño de bases de datos, queries avanzados, índices y optimización.",
        "skills_covered": ["SQL", "PostgreSQL", "Bases de Datos", "Indexación", "Query Optimization"],
        "level": "intermediate",
        "duration_hours": 16.0,
        "category": "Database",
        "language": "es",
        "rating": 4.7,
    },
    {
        "id": "db-002",
        "title": "NoSQL con MongoDB y Firebase",
        "provider": "Udemy",
        "url": "https://udemy.com/course/nosql-mongodb-firebase",
        "description": "Modelado de datos NoSQL, operaciones CRUD, aggregations y Firebase Realtime DB.",
        "skills_covered": ["MongoDB", "Firebase", "NoSQL", "CRUD", "Aggregation Pipeline"],
        "level": "beginner",
        "duration_hours": 12.0,
        "category": "Database",
        "language": "es",
        "rating": 4.6,
    },
    # ── DevOps ────────────────────────────────────────────────────────────
    {
        "id": "do-001",
        "title": "DevOps Completo: CI/CD, Terraform e IaC",
        "provider": "Coursera",
        "url": "https://coursera.org/learn/devops-cicd-terraform",
        "description": "Pipelines CI/CD con GitHub Actions, infraestructura como código con Terraform.",
        "skills_covered": ["DevOps", "CI/CD", "Terraform", "GitHub Actions", "IaC", "AWS"],
        "level": "intermediate",
        "duration_hours": 25.0,
        "category": "DevOps / Infrastructure",
        "language": "es",
        "rating": 4.8,
    },
    # ── Soft Skills / Architecture ────────────────────────────────────────
    {
        "id": "arch-001",
        "title": "Arquitectura de Software: Patrones y Principios",
        "provider": "Platzi",
        "url": "https://platzi.com/cursos/arquitectura-software",
        "description": "SOLID, Clean Architecture, DDD, microservicios, hexagonal y event-driven.",
        "skills_covered": ["Clean Architecture", "SOLID", "DDD", "Microservicios", "Event-Driven"],
        "level": "advanced",
        "duration_hours": 14.0,
        "category": "Architecture / Design",
        "language": "es",
        "rating": 4.9,
    },
]


def main() -> None:
    from services.firebase_service import upsert_course
    from services.vector_store_service import vector_store_service

    print(f"[Seed] Uploading {len(COURSE_CATALOG)} courses to Firebase…")
    for course in COURSE_CATALOG:
        upsert_course(course["id"], course)
        print(f"  ✓ {course['id']} – {course['title']}")

    print("\n[Seed] Building vector index…")
    vector_store_service.build_index(COURSE_CATALOG)
    print("[Seed] Done! Vector index built and courses seeded in Firebase.")


if __name__ == "__main__":
    main()
