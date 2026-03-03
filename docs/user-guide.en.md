# User Guide (English)

## Product workflow

1. Export Telegram chat in JSON format.
2. Upload the JSON file in Chat Analyzer.
3. Wait for analysis completion.
4. Explore dashboard widgets and datasets.

## How to export Telegram data (`result.json`)

1. Open **Telegram Desktop**.
2. Open the target chat you want to analyze.
3. Click the three-dot menu in the top-right corner.
4. Select **Export chat history**.
5. Choose **JSON** format and include message history.
6. Disable media to reduce export size.
7. Start export, wait for completion, and locate the JSON file (often `result.json`).

## Upload and analyze

1. Open Web UI (`http://localhost:8080`).
2. Upload exported Telegram JSON.
3. Track status until it is `done`.
4. Open dashboard and inspect metrics/charts/tables.

## Data handling notes

- This is self-hosted software: your data stays in your environment.
- Uploaded files and generated dashboard payloads are stored in backend storage.

## Related docs

- Fast setup: [getting-started.en.md](getting-started.en.md)
- Configuration: [configuration.en.md](configuration.en.md)
- Operations and troubleshooting: [operations.en.md](operations.en.md)
