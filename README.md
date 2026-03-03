# Chat Analyzer

Chat Analyzer is a self-hosted web tool for analyzing Telegram chat exports and turning them into interactive dashboards.
It is designed for users who need quick insights from `result.json` files and for contributors who want a clean monorepo architecture.

## Features

- Upload Telegram JSON exports and run asynchronous analysis.
- FastAPI backend with structured API and OpenAPI docs.
- React + Vite dashboard with charts, KPI cards, and tabular widgets.
- Configurable runtime limits (upload size, workers, retention, rate limits).
- Dockerized local dev stack and production stack with prebuilt images.

## Screenshots

![Dashboard overview](docs/assets/dashboard-overview.png)
![Charts view](docs/assets/charts.png)
![Tables view](docs/assets/tables.png)

## For Users

- English guide: [docs/user-guide.en.md](docs/user-guide.en.md)
- Русский гайд: [docs/user-guide.ru.md](docs/user-guide.ru.md)
- Environment configuration: [docs/configuration.en.md](docs/configuration.en.md) / [docs/configuration.ru.md](docs/configuration.ru.md)
- Demo dataset: [examples/example_chat.json](examples/example_chat.json)

### Production Run With Prebuilt Images

Use the production compose file that pulls images from GHCR:

```bash
docker compose -f docker-compose.prod.yml up -d
```

By default, the stack expects:

- `ghcr.io/<owner>/chat-analyzer-api:latest`
- `ghcr.io/<owner>/chat-analyzer-web:latest`

You can override image tags through environment variables in `.env`.

## For Contributors

- Contribution guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- Security policy: [SECURITY.md](SECURITY.md)
- Code of Conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Changelog: [CHANGELOG.md](CHANGELOG.md)

## Monorepo Layout

- `apps/api`: FastAPI backend (`/api/*`)
- `apps/web`: React + Vite frontend
- `packages/analyzer-core`: shared Python analysis engine
- `packages/api-contracts`: shared TypeScript API contracts
- `docker-compose.yml`: development orchestration entrypoint (symlink to `infra/docker-compose.yml`)
- `docker-compose.prod.yml`: production orchestration entrypoint (symlink to `infra/docker-compose.prod.yml`)

## Developer Quick Start

1. Python dependencies:

```bash
uv sync
```

2. Frontend dependencies:

```bash
corepack pnpm install
```

3. Run DB migrations and tests:

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

6. Run development stack (build from source):

```bash
docker compose up --build
```

- Frontend: `http://localhost:8080`
- API base path (via web reverse proxy): `http://localhost:8080/api`
- API healthcheck: `http://localhost:8080/api/healthz`
- API docs (via web reverse proxy): `http://localhost:8080/docs`

## Release And Versioning Policy

This repository uses a single monorepo SemVer version.

- `MAJOR`: breaking API behavior or incompatible schema/runtime changes.
- `MINOR`: backward-compatible feature additions.
- `PATCH`: backward-compatible bug fixes and documentation-only corrections.

Release artifacts include:

- Git tag `vX.Y.Z`
- GHCR images `:vX.Y.Z`
- GHCR images `:latest` (updated on each published release)

## Docker Data Refresh

`docker compose` uses a persistent volume (`backend_data`) for uploaded files and generated dashboard JSON.
If you update analyzer or dashboard rendering logic, old analyses will keep old JSON payloads until recomputed.

```bash
docker compose down -v
docker compose up --build
```

Then upload chats again to regenerate `results/*.json` with the current code.

## Developer Scripts

- `scripts/dev/bootstrap.sh` - install Python and JS dependencies.
- `scripts/dev/run_api.sh` - run backend locally.
- `scripts/dev/run_web.sh` - run frontend dev server.
- `scripts/dev/test.sh` - lint, tests, and frontend build smoke.
- `scripts/ci/verify.sh` - CI-equivalent local verification.
