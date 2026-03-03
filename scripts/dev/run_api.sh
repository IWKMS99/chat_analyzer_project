#!/usr/bin/env bash
set -euo pipefail

uv run uvicorn chat_analyzer_api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --app-dir apps/api/src
