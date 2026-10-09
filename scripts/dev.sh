#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r apps/api/requirements.lock
if [[ "${1:-}" == "--sqlite" ]]; then export DATABASE_URL="sqlite:///data/gaia.db"; fi
export PYTHONPATH="apps/api"
.venv/bin/python -m alembic upgrade head
if [[ ! -d apps/web/node_modules ]]; then (cd apps/web && npm ci); fi

.venv/bin/python -m uvicorn gaia.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 --workers 1 &
api_pid=$!
trap 'kill "$api_pid" 2>/dev/null || true' EXIT INT TERM
cd apps/web
npm run dev
