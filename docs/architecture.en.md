# Architecture (Short)

## Components

- `apps/api`: FastAPI service for uploads, analysis lifecycle, and dashboard delivery.
- `apps/web`: React + Vite client for analysis management and dashboard rendering.
- `packages/analyzer-core`: shared Python analysis engine.
- `packages/api-contracts`: generated TypeScript client/types from backend OpenAPI.

## Data flow

1. User uploads Telegram JSON.
2. API creates analysis task and runs pipeline.
3. Analyzer engine parses and aggregates data.
4. API stores metadata in SQLite and result payloads on filesystem.
5. Web app fetches status and dashboard payload for rendering.

## Compatibility

- OpenAPI is the backend contract source.
- TS contracts are generated from that OpenAPI.
- Repository uses single SemVer release line (`vX.Y.Z`).
