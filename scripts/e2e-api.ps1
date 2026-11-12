$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$env:PYTHONPATH = "apps/api"
& ".venv\Scripts\python.exe" -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Native command failed (exit $LASTEXITCODE)" }
& ".venv\Scripts\python.exe" scripts/seed_global_e2e.py
if ($LASTEXITCODE -ne 0) { throw "E2E fixture failed (exit $LASTEXITCODE)" }
& ".venv\Scripts\python.exe" scripts/run_e2e_api.py
if ($LASTEXITCODE -ne 0) { throw "Native command failed (exit $LASTEXITCODE)" }
