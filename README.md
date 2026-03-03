# Chat Analyzer V2 (Utility-First)

Web-only self-hosted utility for Telegram `result.json` analysis.

## What Changed in V2

- Removed Telegram Mini App and bot flow
- Removed MinIO/Caddy/ngrok from default stack
- Hard break to new API: `/api/v2/*`
- Async analysis is preserved (`POST` + status polling)
- Frontend is fully declarative: backend returns dashboard schema (`tabs/widgets/datasets`)

## Quick Start

1. Copy env:

```bash
cp .env.example .env
```

2. Start:

```bash
docker compose up --build
```

3. Open app:

- Frontend: `http://localhost:8080`
- API docs: `http://localhost:8000/docs`

Upload Telegram Desktop export `result.json` and wait until analysis status becomes `done`.

## API V2

- `POST /api/v2/analyses` - create analysis from uploaded file
- `GET /api/v2/analyses` - list recent analyses
- `GET /api/v2/analyses/{analysis_id}/status` - get status/progress
- `GET /api/v2/analyses/{analysis_id}/dashboard` - get declarative dashboard payload
- `DELETE /api/v2/analyses/{analysis_id}` - delete analysis and stored files
- `GET /api/v2/healthz` - service health

## Storage and Retention

- Uploads/results are stored on local filesystem under `backend_data/`
- SQLite metadata database path is controlled by `SQLITE_PATH`
- Expired analyses are cleaned automatically using `TASK_TTL_SECONDS`

## Contributor Workflow

To add new metrics/charts, update Python analysis + dashboard builder.
No React module-specific chart code is required.

## Security Operations

### Secret Scanning

- CI runs `gitleaks` on every push and pull request via `.github/workflows/security-secret-scan.yml`
- Local pre-commit scanning is configured in `.pre-commit-config.yaml`

Setup:

```bash
pip install pre-commit
pre-commit install
```

### Secret Rotation and Git History Purge Checklist

If any secret appears in repository history or generated artifacts:

1. Revoke and rotate exposed credentials first (bot tokens, ngrok, MinIO keys, API keys).
2. Remove leaked files/content from the current branch.
3. Rewrite history with `git filter-repo` (or BFG) to purge leaked blobs.
4. Force-push rewritten branches and notify collaborators to re-clone.
5. Confirm with `gitleaks git --redact` that no secrets remain in history.
