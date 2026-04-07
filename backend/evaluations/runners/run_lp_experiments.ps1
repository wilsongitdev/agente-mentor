Write-Host "============================================="
Write-Host "SISTEMA DE SIMULACION DE HISTORIAL (LANGSMITH)"
Write-Host "============================================="
Write-Host "Este script recreara las 3 fases clave de tu proyecto:"
Write-Host "1. V1 Baseline (Sin Filtros)"
Write-Host "2. V3 Optimizado (Sin Filtros)"
Write-Host "3. Arquitectura Final (V3 + Heurística)"
Write-Host "=============================================`n"

# Forzar el uso del dataset de LinkedIn Real-World
$env:DATASET_NAME_OVERRIDE = "Real-World-CVs-LinkedIn"

# Iteracion 1: Baseline V1, sin Filtro Heuristico
Write-Host ">> [Iteracion 1/3] Ejecutando V1 Baseline..."
$env:USE_RERANKING="false"
$env:PROMPT_VERSION_LP="V1"
python -m evaluations.runners.run_path_eval --experiment "iter-1-baseline-v1"
Write-Host ">> Iteracion 1 Completada!`n"

# Iteracion 2: V3, sin Filtro Heuristico
Write-Host ">> [Iteracion 2/3] Ejecutando V3 (Solo Prompting)..."
$env:USE_RERANKING="false"
$env:PROMPT_VERSION_LP="V3"
python -m evaluations.runners.run_path_eval --experiment "iter-2-prompt-v3"
Write-Host ">> Iteracion 1 Completada!`n"

# Iteracion 3: V3, con Filtro Heuristico Score-Based
Write-Host ">> [Iteracion 3/3] Ejecutando V3 + Arquitectura Heuristica..."
$env:USE_RERANKING="true"
$env:PROMPT_VERSION_LP="V3"
python -m evaluations.runners.run_path_eval --experiment "iter-3-heuristic-arch"
Write-Host ">> Iteracion 3 Completada!`n"

Write-Host "============================================="
Write-Host "HISTORIAL RECREADO EXITOSAMENTE"
Write-Host "============================================="
Write-Host "Ahora puedes ejecutar: python -m evaluations.generate_metrics_report"
