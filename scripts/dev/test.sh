#!/usr/bin/env bash
set -euo pipefail

uv run ruff check .
uv run pytest -q
corepack pnpm --filter @chat-analyzer/web build

echo "All checks passed"
