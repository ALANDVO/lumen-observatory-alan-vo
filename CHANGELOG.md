# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-21

### Added
- Project skeleton with FastAPI backend and React + TypeScript + Vite frontend
- Actor state machine domain engine (RUNNING, PAUSED, SUSPENDED, CRASHED)
- Validated state transitions with audit logging
- Snapshot configuration (full/data scopes) with devolution rules
- REST API for actor lifecycle management (create, pause, commit, resume, revert, dump, delete)
- Pagination and filtering for actor lists
- Prometheus metrics endpoint (`/metrics`)
- `ate_actors` gauge metric by template and status
- `ate_actor_crashes_total` counter
- State dwell time histograms
- OTLP telemetry relay design (endpoint at 169.254.17.1:4317)
- Trusted identity attribution (ate.dev/* labels)
- Delta temporality enforcement
- Cardinality-bounded metric forwarding
- SQLite persistent storage with SQLAlchemy
- Dockerfiles for backend and frontend with non-root users
- docker-compose with Keycloak, persistent volumes, healthchecks
- React dashboard with actor table, detail modal, create modal
- Typed API client derived from backend routes
- Loading, error, and empty states
- Responsive professional UI with CSS
- pyproject.toml with author metadata
- portfolio.json with schema_version=1
- Comprehensive README with architecture diagram
- MIT LICENSE
- .env.example with blank credentials
- .gitignore with proper exclusions

### Security
- OIDC authorization-code flow with PKCE (Keycloak)
- HttpOnly SameSite cookies with CSRF protection
- Role-based access control (viewer/operator/admin)
- Demo mode binds to 127.0.0.1 only
- No hardcoded secrets or credentials

### Testing
- Backend test structure with pytest
- Frontend test structure with vitest
- CI workflow configuration