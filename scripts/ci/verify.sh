#!/usr/bin/env bash
set -euo pipefail

uv sync --frozen --dev
uv run ruff check .
uv run pytest -q
corepack pnpm install --frozen-lockfile
corepack pnpm --filter @chat-analyzer/web build
