# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog,
and this project adheres to Semantic Versioning.

## [0.1.0] - 2026-03-04

Initial public release of Chat Analyzer.

Included in this release:

- FastAPI backend with upload, analysis lifecycle, and dashboard APIs.
- React/Vite web dashboard UI (charts, KPI cards, tabular views).
- Shared analyzer engine and generated API contracts in monorepo layout.
- Docker deployment options:
  - source-based development stack,
  - production stack with GHCR prebuilt images.
- OSS baseline files:
  - `LICENSE` (MIT),
  - `CONTRIBUTING.md`,
  - `SECURITY.md`,
  - `CODE_OF_CONDUCT.md`,
  - issue/PR templates.
- User/operator documentation and demo dataset (`examples/example_chat.json`).

Release image tags:

- `ghcr.io/<owner>/chat-analyzer-api:v0.1.0` and `latest`
- `ghcr.io/<owner>/chat-analyzer-web:v0.1.0` and `latest`
