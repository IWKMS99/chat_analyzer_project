# User Guide (English)

## What This Tool Does

Chat Analyzer reads Telegram Desktop JSON exports and generates an interactive dashboard with:

- message and activity metrics,
- temporal and participant statistics,
- chart and table widgets for exploration.

## Quick Run (Docker, prebuilt images)

```bash
docker compose -f docker-compose.prod.yml up -d
```

Open:

- Web UI: `http://localhost:8080`
- API docs: `http://localhost:8080/docs`

## How To Export Telegram Data (`result.json`)

1. Open **Telegram Desktop**.
2. Go to **Settings -> Advanced -> Export Telegram data**.
3. Select **JSON** as export format.
4. Include messages from the target chat(s).
5. Keep media disabled for first test runs to reduce file size.
6. Start export and wait until Telegram creates the output folder.
7. Open the output folder and locate the exported JSON file (commonly named `result.json`).

## Upload And Analyze

1. Open Chat Analyzer Web UI.
2. Go to analyses screen and use file upload.
3. Upload Telegram JSON (`result.json` or equivalent export file).
4. Wait until analysis status becomes `done`.
5. Open dashboard view.

## Troubleshooting

### Upload is rejected (HTTP 413)

- Increase `MAX_UPLOAD_BYTES` in `.env`.
- Restart stack after changing env values.

### Analysis is slow

- Increase `TASK_WORKERS` (up to 4 in current backend validation).
- Adjust `CHAT_ANALYZER_NLP_WORKERS` if CPU capacity allows.

### Parsing fallback warnings or memory pressure

- Tune `CHAT_ANALYZER_FALLBACK_JSON_MAX_BYTES`.
- Start with smaller chats to verify pipeline health.

### UI cannot reach API

- Verify `VITE_API_BASE_URL` and reverse-proxy path.
- Check API health endpoint: `http://localhost:8080/api/healthz`.

### Wrong locale/text display issues

- Ensure JSON is exported by Telegram Desktop without manual re-encoding.
- Avoid editing export files in tools that change encoding.
