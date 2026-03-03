# Contributing

Thanks for contributing to Chat Analyzer.

## Development Setup

### Prerequisites

- Python 3.11+
- `uv`
- Node.js 20+
- `pnpm` (via Corepack)
- Docker (optional, recommended for full stack)

### Install dependencies

```bash
uv sync
corepack pnpm install
```

### Run local checks

```bash
scripts/ci/verify.sh
```

Equivalent manual checks:

```bash
uv run ruff check .
uv run pytest -q
pnpm --filter @chat-analyzer/web build
pnpm --filter @chat-analyzer/web test:smoke
```

## API Contracts Workflow

When API schema changes:

```bash
corepack pnpm --filter @chat-analyzer/api-contracts run generate
```

Commit generated updates from `packages/api-contracts` in the same PR.

## Pull Request Rules

- Keep PRs focused and small enough for review.
- Add or update tests for behavioral changes.
- Update docs when changing setup, runtime, or user-facing behavior.
- Ensure CI is green before requesting review.

## Versioning And Releases

This repository uses one monorepo SemVer version.

- `MAJOR`: breaking changes (API behavior, compatibility, schema expectations).
- `MINOR`: backward-compatible features.
- `PATCH`: backward-compatible fixes and docs corrections.

On each published GitHub Release:

- tag `vX.Y.Z` is the source of truth,
- GHCR images are published with `vX.Y.Z` and `latest`.

## Architecture Notes

- `apps/api`: FastAPI backend and async analysis pipeline.
- `apps/web`: React + Vite UI.
- `packages/analyzer-core`: analysis engine and aggregators.
- `packages/api-contracts`: generated TypeScript contracts.
