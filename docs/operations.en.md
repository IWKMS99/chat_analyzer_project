# Operations Guide (English)

## Deployment modes

- `docker-compose.yml`: development stack with local image build.
- `docker-compose.prod.yml`: production stack with prebuilt GHCR images.

## Run production stack

```bash
docker compose -f docker-compose.prod.yml up -d
```

Default image names:

- `ghcr.io/<owner>/chat-analyzer-api:latest`
- `ghcr.io/<owner>/chat-analyzer-web:latest`

Override tags in `.env`:

- `API_IMAGE=ghcr.io/<owner>/chat-analyzer-api:vX.Y.Z`
- `WEB_IMAGE=ghcr.io/<owner>/chat-analyzer-web:vX.Y.Z`

Web runtime variables:

- `VITE_API_BASE_URL` is applied at container startup to runtime config.
- `NGINX_CLIENT_MAX_BODY_SIZE` controls nginx upload limit in front of API.

## Data persistence

`backend_data` volume stores:

- SQLite DB,
- uploaded files,
- generated analysis payloads.

## Upgrade procedure

1. Update image tags in `.env` (or use new `latest`).
2. Pull and restart services:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

## Common issues

### API startup fails with `PermissionError: /app`

Cause: local run picked Docker-style paths from `.env`.

Fix:

- use `scripts/dev/run_api.sh`, or
- set local-safe values:

```bash
export SQLITE_PATH=backend_data/analyses.db
export STORAGE_BASE_DIR=backend_data
```

### Upload rejected with HTTP 413

Set both limits and restart services:

- API limit: `MAX_UPLOAD_BYTES`
- nginx front-proxy limit: `NGINX_CLIENT_MAX_BODY_SIZE`

The effective upload limit is the lower of these two values.

### API unreachable from web

Check:

- `VITE_API_BASE_URL`
- reverse-proxy path (`/api`)
- API health endpoint: `http://localhost:8080/api/healthz`

### Slow analysis

Tune:

- `TASK_WORKERS`
- `CHAT_ANALYZER_NLP_WORKERS`

### GHCR pull denied

- verify package visibility or authenticate to GHCR,
- verify `API_IMAGE` / `WEB_IMAGE` values.

## Releases and versioning

Single monorepo SemVer is used.

- `MAJOR`: breaking API/schema/runtime compatibility.
- `MINOR`: backward-compatible features.
- `PATCH`: backward-compatible fixes and docs updates.

Each published GitHub Release produces:

- git tag `vX.Y.Z`,
- `ghcr.io/<owner>/chat-analyzer-api:vX.Y.Z` and `latest`,
- `ghcr.io/<owner>/chat-analyzer-web:vX.Y.Z` and `latest`.

Release flow:

1. CI passes.
2. `CHANGELOG.md` updated.
3. Tag `vX.Y.Z` pushed.
4. GitHub Release published.
5. `Release Images` workflow verified.

For stabilization, use pre-release tags (for example `v0.1.0-rc.1`) and mark release as pre-release.
