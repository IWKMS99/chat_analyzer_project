# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog,
and this project adheres to Semantic Versioning.

## [0.1.0] - 2026-03-04

### Added

- OSS baseline documentation (`LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`).
- User documentation in English and Russian (`docs/user-guide.*.md`).
- Environment configuration references in English and Russian (`docs/configuration.*.md`).
- Demo dataset for onboarding (`examples/example_chat.json`).
- Community templates for issues and pull requests.
- GHCR release workflow for API and Web images.
- Production compose file using prebuilt images (`infra/docker-compose.prod.yml`).

### Changed

- Unified monorepo version references around `0.1.0`.
- Expanded `README.md` for both users and contributors.

### Notes

- Release images are published as `vX.Y.Z` and `latest` when a GitHub Release is published.
