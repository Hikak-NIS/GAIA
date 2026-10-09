$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$env:PYTHONPATH = "apps/api"
& ".venv\Scripts\python.exe" -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Native command failed (exit $LASTEXITCODE)" }
& ".venv\Scripts\python.exe" -m ruff check apps/api database tests
if ($LASTEXITCODE -ne 0) { throw "Native command failed (exit $LASTEXITCODE)" }
& ".venv\Scripts\python.exe" -m alembic check
if ($LASTEXITCODE -ne 0) { throw "Native command failed (exit $LASTEXITCODE)" }
Push-Location "apps\web"
npm run lint
if ($LASTEXITCODE -ne 0) { throw "Native command failed (exit $LASTEXITCODE)" }
npm run typecheck
if ($LASTEXITCODE -ne 0) { throw "Native command failed (exit $LASTEXITCODE)" }
npm run build
if ($LASTEXITCODE -ne 0) { throw "Native command failed (exit $LASTEXITCODE)" }
Pop-Location
