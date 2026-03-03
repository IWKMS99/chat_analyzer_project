# Getting Started (English)

## Option A: Run with prebuilt images (recommended)

```bash
docker compose -f docker-compose.prod.yml up -d
```

Open:

- Web UI: `http://localhost:8080`
- API docs: `http://localhost:8080/docs`

## Option B: Containerized local build (no hot reload)

```bash
docker compose up --build
```

This mode builds images locally from source code, but does not provide hot reload.

## Option C: Native developer mode (hot reload)

```bash
uv sync
corepack pnpm install
scripts/dev/run_api.sh
```

Run frontend in another terminal:

```bash
scripts/dev/run_web.sh
```

## First analysis in 3 steps

1. Export Telegram chat as JSON (see [user-guide.en.md](user-guide.en.md)).
2. Upload file in the Web UI.
3. Wait until analysis status is `done` and open dashboard.

## Next docs

- Full user flow: [user-guide.en.md](user-guide.en.md)
- Runtime tuning: [configuration.en.md](configuration.en.md)
- Operational notes: [operations.en.md](operations.en.md)
