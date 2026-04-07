# Script de arranque del servidor backend – usa el entorno cv-analyzer
# Desactiva la generación de .pyc para evitar conflictos de caché
# Uso: .\start_server.ps1

Write-Host "Iniciando Agente Mentor Backend (entorno: cv-analyzer)..." -ForegroundColor Green

# Desactiva escritura de bytecode compilado (.pyc)
$env:PYTHONDONTWRITEBYTECODE = "1"

# Carga el .env si existe
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.+)$") {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"')
            [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
    Write-Host ".env cargado." -ForegroundColor DarkGray
}

& "C:\Users\WILSON\anaconda3\envs\cv-analyzer\python.exe" -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --no-access-log
