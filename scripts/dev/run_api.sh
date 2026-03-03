#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="apps/api/src:packages/analyzer-core/src:${PYTHONPATH:-}"
# Local dev defaults. Values explicitly exported in shell still take priority.
export SQLITE_PATH="${SQLITE_PATH:-backend_data/analyses.db}"
export STORAGE_BASE_DIR="${STORAGE_BASE_DIR:-backend_data}"

UV_BIN="${UV_BIN:-uv}"
if ! command -v "$UV_BIN" >/dev/null 2>&1; then
  UV_BIN=".venv/bin/uv"
fi

"$UV_BIN" run alembic -c apps/api/alembic.ini upgrade head

"$UV_BIN" run uvicorn chat_analyzer_api.main:app \
  --host 0.0.0.0 \
  --port 8000
