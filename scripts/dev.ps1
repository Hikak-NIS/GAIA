param([switch]$UseSqlite)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

# Never let a new frontend silently connect to a previous API process.
foreach ($port in @(8000, 5173)) {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        throw "Port $port is already occupied (PID $($listener[0].OwningProcess)). Stop the previous GAIA server before starting this script."
    }
}

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
$webLocationPushed = $false
try {
    $apiReady = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if ($apiProcess.HasExited) { throw "GAIA API exited during startup. Frontend was not started." }
        try {
            $schema = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/openapi.json' -TimeoutSec 2
            if (-not $schema.paths.'/api/v1/auth/verify-email') { throw "API version mismatch" }
            $apiReady = $true
            break
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if (-not $apiReady) { throw "GAIA API did not become ready with email verification support." }
    Push-Location "apps\web"
    $webLocationPushed = $true
    npm run dev
if ($LASTEXITCODE -ne 0) { throw "Native command failed (exit $LASTEXITCODE)" }
} finally {
    if ($webLocationPushed) { Pop-Location }
    # Windows venv python.exe launches a child interpreter. Killing only the
    # launcher leaves Uvicorn serving old code on port 8000.
    if (-not $apiProcess.HasExited) {
        & taskkill.exe /PID $apiProcess.Id /T /F | Out-Null
    }
}
