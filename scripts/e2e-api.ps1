$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$env:PYTHONPATH = "apps/api"
& ".venv\Scripts\python.exe" -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Native command failed (exit $LASTEXITCODE)" }
& ".venv\Scripts\python.exe" -m uvicorn gaia.main:app --app-dir apps/api --host 127.0.0.1 --port 8001 --workers 1
if ($LASTEXITCODE -ne 0) { throw "Native command failed (exit $LASTEXITCODE)" }
