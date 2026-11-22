# Verification and known limits

## Automated backend verification

A set of 12 Pytest tests was executed against an isolated SQLite database for application and gateway behavior. Verified scenarios:

- login failure and authentication enforcement
- cattle registration, uniqueness, new RFID tag assignment
- accepted OUT/IN movement and presence projection
- repeat event ID does not generate an extra movement
- unknown tag and wrong-barn anomaly alert creation
- mobile RFID lookup, vaccination record and source-id idempotency
- requested → approved → completed transfer workflow
- role/scope denial and restricted audit access
- authenticated gateway synchronization and duplicate replay
- CSV report and clearly simulated external export
- gateway durable local storage, recovery and retained pending events on HTTP connection failures

## Current local Python / plain-JS verification boundary

- All **12 Python Pytest tests passed** in the authoring environment, including the new FastAPI static-web route test.
- `node --check web/assets/app.js` passed syntax validation using a one-off inspection tool; **Node.js is not required to run this project**.
- FastAPI TestClient successfully returned HTML from `/` and `/field`, CSS/JS/image files from `/static/...`, and `GET /healthz` with 200 responses. JWT login API also returned 200 in a dedicated local smoke test.
- A full interactive Chromium session could **not** be completed in the authoring environment because localhost navigation was blocked by the test runtime. UI interaction on the user's Windows browser remains to be checked.
- These checks used SQLite fixtures and **do not** prove Aiven/PostgreSQL migration compatibility or production readiness. Do not claim the 2-second performance NFR as verified.

## SOLID reflection evidence

- **SRP:** `movement/service.py` processes RFID acceptance; `alerts/router.py` manages alert lifecycle; `health/router.py` manages clinical writes.
- **OCP:** gateway reads are normalized into `ReadIn`; new reader adapters can translate their hardware payload into this format without altering accepted-movement rules.
- **LSP:** there is no comprehensive repository-interface replacement test in this demo; avoid claiming LSP is proven.
- **ISP:** exposed API routers are separated by role and concern. Internal repository protocol segregation can be improved in a future release.
- **DIP:** the architecture uses normalized DTO and module boundaries; for strict DIP proof introduce explicit repository protocols and tests that swap SQLAlchemy adapters for fakes. Do not claim that a full Clean Architecture layering has been verified.

The final M2 reflection should describe code evidence, limitations and specific refactoring steps instead of claiming all SOLID principles were automatically guaranteed by FastAPI.
