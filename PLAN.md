# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

actor-gauge-metrics

## Roadmap

### project-skeleton — Project skeleton with FastAPI backend and React frontend

Status: done

Acceptance:
- FastAPI app runs with health endpoint
- React + TypeScript + Vite frontend builds
- Dockerfiles for backend and frontend
- docker-compose with Keycloak and persistent volumes
- SQLite persistent storage with SQLAlchemy
- Basic project structure meeting contract requirements

Implementation: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/models/__init__.py`, `backend/app/api/__init__.py`, `backend/app/services/__init__.py`, `backend/requirements.txt`, `backend/Dockerfile`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/Dockerfile`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `compose.yaml`, `.env.example`, `.gitignore`, `README.md`, `LICENSE`, `CHANGELOG.md`, `pyproject.toml`, `portfolio.json`

Tests: `backend/tests/test_health.py`, `frontend/tests/App.test.tsx`

### actor-state-machine — Actor state machine domain engine

Status: done

Acceptance:
- Actor model with RUNNING/PAUSED/SUSPENDED/CRASHED states
- State transitions with validation
- Snapshot configuration (full/data)
- Actor lifecycle API endpoints
- Persistence with SQLite

Implementation: `backend/app/models/actor.py`, `backend/app/services/actor_service.py`, `backend/app/api/actors.py`, `backend/tests/test_actor_state_machine.py`

Tests: `backend/tests/test_actor_state_machine.py`, `backend/tests/test_actor_api.py`

### telemetry-relay — OTel telemetry relay for actor attribution

Status: planned

Acceptance:
- OTLP receiver endpoint at 169.254.17.1:4317
- Actor identity attribution (actor_uid, actor_name, etc.)
- Cardinality-bounded metric forwarding
- Delta temporality enforcement

Implementation: `backend/app/services/telemetry_relay.py`, `backend/app/api/telemetry.py`, `backend/tests/test_telemetry_relay.py`

Tests: `backend/tests/test_telemetry_relay.py`

### actor-gauge-metrics — Actor gauge metrics (ate.actors)

Status: done

Acceptance:
- UpDownCounter for actor counts by status and template
- Incremented on state transitions
- No per-collection full scan

Implementation: `backend/app/services/actor_metrics.py`, `backend/tests/test_actor_metrics.py`, `backend/app/services/actor_service.py`

Tests: `backend/tests/test_actor_metrics.py`

### oidc-auth — OIDC authentication with Keycloak

Status: planned

Acceptance:
- Authorization code flow with PKCE
- HttpOnly SameSite cookies with CSRF protection
- Role-based access control (viewer/operator/admin)
- Login/logout endpoints

Implementation: `backend/app/core/auth.py`, `backend/app/api/auth.py`, `backend/tests/test_auth.py`, `frontend/src/components/auth/`

Tests: `backend/tests/test_auth.py`, `frontend/tests/auth.test.tsx`

### frontend-dashboard — React dashboard with actor management

Status: planned

Acceptance:
- Actor list with pagination/filtering
- Actor detail view with state transitions
- Create/import/search/export workflows
- Loading/error/empty states
- Typed API client from backend routes

Implementation: `frontend/src/components/actors/`, `frontend/src/api/client.ts`, `frontend/src/pages/`, `frontend/tests/dashboard.test.tsx`

Tests: `frontend/tests/dashboard.test.tsx`

### ci-pipeline — CI pipeline with backend/frontend tests and Docker builds

Status: planned

Acceptance:
- GitHub Actions workflow with pytest, npm ci/build/test
- Dockerfile builds for backend and frontend
- At least 12 backend tests, 3 frontend tests

Implementation: `.github/workflows/ci.yml`

Tests: `backend/tests/`, `frontend/tests/`

