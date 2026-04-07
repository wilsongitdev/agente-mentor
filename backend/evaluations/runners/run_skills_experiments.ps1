# Script para ejecutar experimentos de Extracción de Skills (V1, V2, V3)
# Este script ejecuta la evaluación contra LangSmith para cada versión del prompt.

Write-Host "🚀 Iniciando experimentos de Skill Extraction..." -ForegroundColor Cyan

# --- VERSIÓN 1: Baseline ---
Write-Host "`n[1/3] Ejecutando V1: Baseline..." -ForegroundColor Yellow
$env:PROMPT_VERSION = "V1"
python -m evaluations.runners.run_skills_eval --experiment "Skills-V1-Baseline"

# --- VERSIÓN 2: Contextual ---
Write-Host "`n[2/3] Ejecutando V2: Contextual..." -ForegroundColor Yellow
$env:PROMPT_VERSION = "V2"
python -m evaluations.runners.run_skills_eval --experiment "Skills-V2-Contextual"

# --- VERSIÓN 3: Premium ---
Write-Host "`n[3/3] Ejecutando V3: Premium (Producción)..." -ForegroundColor Yellow
$env:PROMPT_VERSION = "V3"
python -m evaluations.runners.run_skills_eval --experiment "Skills-V3-Premium"

Write-Host "`n✅ ¡Experimentos completados!" -ForegroundColor Green
Write-Host "👉 Revisa los resultados y compáralos en: https://smith.langchain.com/" -ForegroundColor Cyan
