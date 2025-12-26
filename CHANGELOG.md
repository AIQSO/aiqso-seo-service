# Changelog

All notable changes to this repository are documented in this file.

## [1.1.0] - 2025-12-25

### Added
- **Developer Tooling**
  - `pyproject.toml` with ruff, mypy, and pytest configuration
  - `.pre-commit-config.yaml` with Python linting and formatting hooks
  - `requirements-dev.txt` with development dependencies
  - GitHub Actions CI workflow (`.github/workflows/ci.yml`)
    - Python lint, typecheck (non-blocking), and test jobs (Python 3.11/3.12)
    - Dashboard lint (non-blocking), typecheck (non-blocking), and build (non-blocking) jobs
    - Docker build verification
    - Note: Some checks are non-blocking due to pre-existing issues in the codebase
- **Dashboard Tooling**
  - Prettier configuration (`.prettierrc.json`)
  - Husky + lint-staged for pre-commit hooks
  - New npm scripts: `lint:fix`, `format`, `format:check`, `typecheck`

### Security
- **python-multipart** 0.0.6 → 0.0.21 (CVE-2024-53981, CVE-2024-24762)
- **aiohttp** 3.9.1 → 3.12.14 (CVE-2024-52304, CVE-2024-30251, CVE-2024-23334, request smuggling fix)
- **jinja2** 3.1.3 → 3.1.6 (CVE-2024-56326, CVE-2024-56201, CVE-2025-27516)
- Removed unused **python-jose** dependency (CVE-2024-33663, CVE-2024-33664)

### Fixed
- Bare `except` clauses replaced with `except Exception` in SEO auditors
- Missing `datetime` import in billing router
- Duplicate import removed from odoo_service.py
- Various code style issues fixed by ruff

## Unreleased

### Added
- Runtime configuration validation (`ENVIRONMENT`, `SECRET_KEY` checks) and logging configuration (`LOG_LEVEL`, `LOG_JSON`).
- Optional API key enforcement for most routes via `REQUIRE_API_KEY`.
- Minimal pytest coverage for settings validation and health endpoint.
- Documentation: `ARCHITECTURE.md`, `docs/CONFIGURATION.md`, `IMPLEMENTATION_NOTES.md`.

### Changed
- `/health/db` now uses SQLAlchemy `text()` and returns `503` when unhealthy.
- Reduced stdout `print()` usage in favor of structured logging.

### Fixed
- Added missing runtime dependencies used by the codebase (`PyYAML`, `click`) to `requirements.txt`.

