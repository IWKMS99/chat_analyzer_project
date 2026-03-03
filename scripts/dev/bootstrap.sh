#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required: https://docs.astral.sh/uv/" >&2
  exit 1
fi

if ! command -v corepack >/dev/null 2>&1; then
  echo "corepack is required (Node.js >=16.13)" >&2
  exit 1
fi

uv sync
corepack pnpm install

echo "Bootstrap complete"
