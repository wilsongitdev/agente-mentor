Write-Host '============================================='
Write-Host 'SIMULADOR DE RENDIMIENTO E2E (LANGSMITH)'
Write-Host '============================================='
Write-Host 'Este script medira la Calidad, Latencia y Costo en 2 fases:'
Write-Host '1. E2E-Baseline (V1 Prompts, Sin Heurísticas)'
Write-Host '2. E2E-Arquitectura-Final (V3 Prompts, Con Heurísticas)'
Write-Host '============================================='

# Fase 1: Baseline
Write-Host '>> [1/2] Ejecutando E2E Baseline (Modelo de menor costo)...'
$env:USE_RERANKING = 'false'
$env:PROMPT_VERSION_LP = 'V1'
python -m evaluations.runners.run_e2e_eval --experiment 'e2e-baseline'

# Fase 2: Final
Write-Host '>> [2/2] Ejecutando E2E Arquitectura Final (V3 + Heurísticas)...'
$env:USE_RERANKING = 'true'
$env:PROMPT_VERSION_LP = 'V3'
python -m evaluations.runners.run_e2e_eval --experiment 'e2e-final-arch'

Write-Host '============================================='
Write-Host 'EVALUACIÓN E2E COMPLETADA'
Write-Host '============================================='
Write-Host 'Ahora genera tu grafica de Latencia y Costo con:'
Write-Host 'python -m evaluations.reports.generate_e2e_report'
