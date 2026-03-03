# Contributing

Thanks for contributing to Chat Analyzer.

## Before you start

- Read architecture notes: [docs/architecture.en.md](docs/architecture.en.md)
- Read operational/release notes: [docs/operations.en.md](docs/operations.en.md)
- Check open issues and avoid duplicated work.

## Local setup

Prerequisites:

- Python 3.11+
- `uv` (or `.venv/bin/uv`)
- Node.js 20+
- `pnpm` via Corepack

Install dependencies:

```bash
uv sync
corepack pnpm install
```

## Development flow

1. Create a focused branch.
2. Implement changes with tests.
3. Run local checks.
4. Open PR with summary and risks.

## Local checks

```bash
scripts/ci/verify.sh
```

Manual equivalent:

```bash
.venv/bin/ruff check .
.venv/bin/pytest -q
corepack pnpm --filter @chat-analyzer/web build
```

## API contracts

If backend schema changed:

```bash
corepack pnpm --filter @chat-analyzer/api-contracts run generate
```

Commit generated files from `packages/api-contracts` in the same PR.

## Pull request expectations

- Keep PR scope tight.
- Include tests for behavior changes.
- Update docs for user/operator/developer flow changes.
- Ensure CI is green before requesting review.
- Update screenshots in `docs/assets/` if UI changed significantly.

## Security

Do not disclose vulnerabilities in public issues.
Use [SECURITY.md](SECURITY.md).
