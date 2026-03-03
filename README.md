# Chat Analyzer Monorepo

Monorepo layout:

- `apps/api`: FastAPI backend (`/api/*`)
- `apps/web`: React + Vite frontend
- `packages/analyzer-core`: shared Python analysis engine
- `packages/api-contracts`: shared TypeScript API contracts
- `docker-compose.yml`: local orchestration entrypoint (symlink to `infra/docker-compose.yml`)

## Quick Start

1. Python deps:

```bash
uv sync
```

2. Frontend deps:

```bash
corepack pnpm install
```

3. Run tests:

```bash
.venv/bin/alembic -c apps/api/alembic.ini upgrade head
.venv/bin/pytest -q
```

4. Build frontend:

```bash
corepack pnpm --filter @chat-analyzer/web build
```

5. Refresh API contracts from OpenAPI:

```bash
corepack pnpm --filter @chat-analyzer/api-contracts run generate
```

5. Run stack:

```bash
docker compose up --build
```

- Frontend: `http://localhost:8080`
- API base path (via web reverse proxy): `http://localhost:8080/api`
- API healthcheck: `http://localhost:8080/api/healthz`
- API docs (via web reverse proxy): `http://localhost:8080/docs`

## Developer Scripts

- `scripts/dev/bootstrap.sh` - install Python and JS dependencies.
- `scripts/dev/run_api.sh` - run backend locally.
- `scripts/dev/run_web.sh` - run frontend dev server.
- `scripts/dev/test.sh` - lint, tests, and frontend build smoke.
- `scripts/ci/verify.sh` - CI-equivalent local verification.
