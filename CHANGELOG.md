# Changelog

## 1.3.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-11-09

### Fixed
- **actor-gauge-metrics**: Fixed duplicate metrics increments in API endpoints
  - All actor lifecycle API endpoints (`create_actor`, `transition_actor`, `pause_actor`, `commit_actor`, `resume_actor`, `revert_actor`, `dump_actor`, `delete_actor`) were calling `actor_metrics` methods after the service layer already did so, causing double-counting
  - Metrics now correctly track actor counts by status and template with exactly one increment/decrement per state transition

### Added
- Integration test `test_metrics_integration_via_api` verifying metrics flow through full API stack

## [1.1.0] - 2026-11-06

### Added
- **actor-state-machine**: Actor state machine domain engine with RUNNING/PAUSED/SUSPENDED/CRASHED states
- **actor-gauge-metrics**: Actor gauge metrics (ate.actors) with UpDownCounter for actor counts by status and template
- **project-skeleton**: FastAPI backend with React + TypeScript + Vite frontend, Dockerfiles, docker-compose with Keycloak, SQLite persistent storage

### Tests
- 36 backend tests (health, actor state machine, actor API, actor metrics)
- 4 frontend tests (App component rendering)

## [1.0.0] - 2026-11-06

### Added
- Initial project structure and configuration
- MIT License
- Basic README with Alan Vo contact information

---

Alan Vo · [alanvo.net](https://alanvo.net) · [X: @alanvoasi](https://x.com/alanvoasi)
