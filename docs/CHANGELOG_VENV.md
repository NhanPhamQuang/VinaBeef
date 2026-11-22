# VinaBeef M2 — local `.venv` refactor

## Removed

- Docker/Docker Compose, Render manifest and container startup files from this distribution.
- React, TypeScript, Vite / npm frontend and the React Native / Expo mobile project.

## Added

- `web/index.html`, `web/assets/styles.css`, `web/assets/app.js`: direct browser frontend with no packages or build system, retaining the former VinaFarm palette and sidebar layout.
- `/field`: responsive Field Health workflow; typed RFID EPC, keyboard-wedge compatibility and an IndexedDB demonstration outbox (not hardened offline clinical storage).
- `backend/app/main.py`: FastAPI serves static HTML/CSS/JS as its own web UI. `/api`, `/docs`, `/healthz` remain.
- `.env` support from the root folder shared by `backend/app/core/config.py` and `edge_gateway/main.py`.
- Root `requirements.txt` and Windows launchers for `.venv`, migration, backend, gateway and test runs.
- `backend/tests/test_plain_web.py` to check static frontend delivery.

## Unchanged

- FastAPI Modular Monolith, endpoints and SQLAlchemy models/Alembic migrations.
- JWT/RBAC, PostgreSQL/Aiven connection option and gateway SQLite retry logic.
- Original project UC-01..UC-31 baseline coverage assessment and acknowledged unimplemented gaps.

## Explicit limitations

This change prioritizes fast local execution and a reduced JS toolchain. It is **not** a new full-coverage implementation of all 31 use cases. The browser Field Health screen is not equivalent to a vendor-integrated React Native mobile scanner and the browser's IndexedDB is not an assured storage system for regulated clinical records.
