Write-Host "=========================================================="
Write-Host "SIMULADOR DE RENDIMIENTO REAL-WORLD (PDFs)"
Write-Host "=========================================================="
Write-Host "Este script medira la Calidad, Latencia y Costo en 2 fases:"
Write-Host "1. E2E-Baseline-Real (V1 Prompts, Sin Reranking)"
Write-Host "2. E2E-Final-Arch-Real (V3 Prompts, Con Reranking)"
Write-Host "=========================================================="

# Fase 1: Baseline
Write-Host ">> [1/2] Ejecutando E2E Baseline Real-World..."
$env:USE_RERANKING = "false"
$env:PROMPT_VERSION_LP = "V1"
python -m evaluations.real_world.run_real_world_eval --experiment "e2e-baseline-real"

# Fase 2: Final
Write-Host ">> [2/2] Ejecutando E2E Arquitectura Final Real-World..."
$env:USE_RERANKING = "true"
$env:PROMPT_VERSION_LP = "V3"
python -m evaluations.real_world.run_real_world_eval --experiment "e2e-final-arch-real"

Write-Host "=========================================================="
Write-Host "EVALUACION COMPARATIVA COMPLETADA"
Write-Host "=========================================================="
Write-Host "Ahora genera tu grafica comparativa con:"
Write-Host "python -m evaluations.reports.generate_e2e_report"
Write-Host "=========================================================="
