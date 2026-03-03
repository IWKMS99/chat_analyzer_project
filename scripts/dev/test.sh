#!/usr/bin/env bash
set -euo pipefail

uv run ruff check .
uv run alembic -c apps/api/alembic.ini upgrade head
uv run pytest -q
corepack pnpm --filter @chat-analyzer/api-contracts run check
corepack pnpm --filter @chat-analyzer/web build

echo "All checks passed"
