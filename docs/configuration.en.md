# Configuration Reference (English)

This document describes runtime environment variables for API, analyzer engine, and web app.

| Variable | Default | Used in | Effect | Tuning guidance |
| --- | --- | --- | --- | --- |
| `TASK_WORKERS` | `1` | API worker queue | Number of concurrent analysis workers (validated to `1..4`). | Increase on multi-core machines when running several analyses. |
| `MAX_UPLOAD_BYTES` | `104857600` (100 MB) | API upload endpoint | Maximum accepted upload size. | Raise for large exports, lower for stricter resource control. |
| `CHAT_ANALYZER_NLP_WORKERS` | `1` | analyzer-core NLP processor | Worker count for NLP stage. | Keep low on weak CPUs; increase carefully on servers. |
| `CHAT_ANALYZER_FALLBACK_JSON_MAX_BYTES` | `52428800` (50 MB) | analyzer-core data loader | Max JSON size for in-memory fallback parser. | Raise only if fallback parsing is required for bigger files. |
| `TASK_TTL_SECONDS` | `604800` | API cleanup logic | Retention time for task artifacts. | Lower to reduce storage growth. |
| `CLEANUP_INTERVAL_SECONDS` | `600` | API cleanup scheduler | How often cleanup runs. | Lower interval for aggressive cleanup; higher to reduce DB churn. |
| `RATE_LIMIT_REQUESTS` | `120` | API rate limiter | Allowed requests per window. | Tighten for public deployments. |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | API rate limiter | Window length in seconds. | Tune together with `RATE_LIMIT_REQUESTS`. |
| `CORS_ORIGINS` | `http://localhost:8080` | API CORS middleware | Comma-separated allowed browser origins. | Use exact production origins only. |
| `VITE_API_BASE_URL` | `/api` (Docker build arg) | Web app runtime bootstrap | Base URL/prefix for API calls. | Keep `/api` when proxied by nginx; use full URL for split deployments. |
| `SQLITE_PATH` | `/app/backend_data/analyses.db` (Docker) | API + Alembic | Path to SQLite database file. | Keep on persistent volume in production. |
| `STORAGE_BASE_DIR` | `/app/backend_data` (Docker) | API file storage | Directory for uploaded files and result JSON. | Use fast disk and persistent volume. |

## Notes

- Copy `.env.example` to `.env` and adjust values per environment.
- After changing env variables, restart services:

```bash
docker compose down
docker compose up -d
```
