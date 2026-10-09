param([switch]$UseSqlite)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Native command failed (exit $LASTEXITCODE)" }
}
& ".venv\Scripts\python.exe" -m pip install -r "apps\api\requirements.lock"
if ($LASTEXITCODE -ne 0) { throw "Native command failed (exit $LASTEXITCODE)" }
if ($UseSqlite) {
    $env:DATABASE_URL = "sqlite:///data/gaia.db"
}
$env:PYTHONPATH = "apps/api"
& ".venv\Scripts\python.exe" -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Native command failed (exit $LASTEXITCODE)" }

if (-not (Test-Path "apps\web\node_modules")) {
    Push-Location "apps\web"
    npm ci
if ($LASTEXITCODE -ne 0) { throw "Native command failed (exit $LASTEXITCODE)" }
    Pop-Location
}

$apiProcess = Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "gaia.main:app", "--app-dir", "apps/api", "--host", "127.0.0.1", "--port", "8000", "--workers", "1" -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden
try {
    Push-Location "apps\web"
    npm run dev
if ($LASTEXITCODE -ne 0) { throw "Native command failed (exit $LASTEXITCODE)" }
} finally {
    Pop-Location
    if (-not $apiProcess.HasExited) { Stop-Process -Id $apiProcess.Id }
}
