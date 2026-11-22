# VinaBeef M2 — FastAPI + Plain HTML/CSS/JavaScript (`.venv`, NO Docker)

This is the **local-first, framework-free UI edition** of the VinaBeef RFID Livestock Farm Management System. It reuses the original FastAPI modular-monolith backend, PostgreSQL/SQLAlchemy/Alembic domain model, JWT/RBAC, automated tests, and the Python/SQLite edge gateway. The prior React/TypeScript/Vite frontend and React Native/Expo project have been replaced with one responsive HTML/CSS/vanilla-JS web interface. **No npm, Node.js, Docker, Render, EC2, or CI/CD knowledge is needed to run it.**

It keeps the previous VinaFarm visual language: dark sidebar, blue buttons, white data panels and tables. It **does not** newly claim complete 31/31 use-case implementation; review `docs/use_case_coverage.csv` and `docs/M2_REQUIREMENTS_DELTA.md` for existing functional gaps.

## Requirements

- **Windows 10/11**, Python **3.11+**, `py` launcher, network access for the first `pip install`.
- **Database:** existing Aiven PostgreSQL (preferred if you already configured it), or SQLite *only as a local smoke-test fallback* when `DATABASE_URL` is absent.
- A browser. No JavaScript tooling is required.

## Quick start on Windows — EXPLICIT COMMANDS (PowerShell)

Open PowerShell **in the extracted project directory** (containing `requirements.txt`).

```powershell
# 1. Create one virtual environment for backend AND gateway
py -m venv .venv

# 2. Install dependencies (includes Pytest)
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. Create your local configuration (SKIP if .env already exists)
Copy-Item .env.example .env

# 4. Open .env in Notepad and set DATABASE_URL for YOUR Aiven DB
notepad .env
```

**Protect `.env`**: Never commit or share it. Aiven URI provided in chat earlier contained a password; rotate it. Use a **separate** database/schema for this FastAPI app instead of the old team's Spring Boot `defaultdb` schema. Aiven needs a working network connection and SSL (`sslmode=require`).

### Terminal A — migrate & start central application

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Keep this PowerShell window open. Check:

- Main website **http://127.0.0.1:8000**
- Swagger **http://127.0.0.1:8000/docs**
- Health **http://127.0.0.1:8000/healthz**
- Field Health mobile-friendly page **http://127.0.0.1:8000/field**

### Terminal B — start the local offline Farm Gateway

In a **new** PowerShell window, open the project root, then:

```powershell
cd edge_gateway
..\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

- Gateway API **http://127.0.0.1:8001/docs**
- Gateway health **http://127.0.0.1:8001/healthz**
- Gateway queue **http://127.0.0.1:8001/api/edge/status**

Both processes share the project-root `.env` automatically. The gateway SQLite file defaults to `edge_gateway/data/edge_events.sqlite` (a local file created on first run). To simulate a WAN outage, stop **only Terminal A** and submit a valid event to the gateway; restart A and check the queue via `GET /api/edge/status`. The gateway must see a valid central reader ID and EPC from the same central database.

### Terminal C — tests (optional)

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
```

The tests override `DATABASE_URL` with their own temporary SQLite database: they **do not** write to your Aiven database. Please use a separate PostgreSQL test DB for stronger integration validation.

### Simpler Windows launchers

- `setup.bat` = create `.venv`, `pip install`, create `.env.example` copy only when `.env` is missing.
- `run_backend.bat` = Alembic migration, then central FastAPI server.
- `run_gateway.bat` = SQLite Gateway server.
- `run_tests.bat` = Pytest.

These scripts **do not hide errors**: a failed process prints its traceback and pauses. Using the explicit terminal commands above is still best for debugging.

## Demo account (DEMO_MODE=1 ONLY)

| Role | Email | Password |
| --- | --- | --- |
| System Administrator | `admin@vinabeef.test` | `Demo@123456` |
| Farm Manager | `manager@vinabeef.test` | `Demo@123456` |
| Barn Supervisor | `supervisor@vinabeef.test` | `Demo@123456` |
| Executive | `executive@vinabeef.test` | `Demo@123456` |

Demo seed: three farms, 120 barns, 12 simulated readers, 240 cattle. Seed only initializes demo data when farms table is empty; if you point to an existing Aiven database, existing records remain. For any publicly accessible deployment set `APP_ENV=production`, `DEMO_MODE=0`, and proper unique secrets.

## New simpler project structure

```text
VinaBeef_M2_Vanilla_Venv/
├── .env.example            # copy to .env (secrets never included)
├── requirements.txt        # ONE Python environment for everything
├── setup.bat
├── run_backend.bat
├── run_gateway.bat
├── run_tests.bat
├── backend/
│   ├── app/core, db, modules   # existing FastAPI Modular Monolith
│   ├── alembic/               # PostgreSQL/SQLite migrations
│   └── tests/
├── web/
│   ├── index.html
│   └── assets/
│       ├── app.js             # vanilla DOM, fetch(), IndexedDB
│       ├── styles.css         # preserved VinaFarm look
│       └── ranch.png
├── edge_gateway/main.py      # Python + SQLite event queue / retry
├── docs/                     # M2 architecture and UC mapping
└── scripts/                  # seed and benchmark probe
```

## Interface scope / behavior

- Dashboard, Herd / RFID Tags, Facilities, Gate Readers, Movement, Alerts / missing-animal evaluation, Transfers, Field Health / Vaccination, Disease Surveillance, Reporting CSV, Audit, Users / RBAC, Farm Gateway status.
- No React, TypeScript, JSX, Vite, npm or Expo. The browser loads `web/index.html`, `styles.css`, and `app.js` **directly through FastAPI**, and calls the existing authenticated `/api/...` endpoints.
- The `/field` page is responsive and supports **typed EPC** or keyboard-wedge RFID readers which emit typed keystrokes. **Real RFID native SDK / Bluetooth protocol support is not implemented.**
- On the Field Health screen, a demonstration **IndexedDB outbox** can hold health records after an unsuccessful API submission *when explicitly confirmed by the operator*. Use `Sync Mobile Queue` to retry; records use `source_id` for central idempotency. **Browser offline storage is not encrypted, guaranteed, or medically certified**; do not use on shared production field devices. If no preloaded animal identity is available offline, EPC identification itself will fail. Do not mistake local queue acknowledgment for central persistence.
- The local gateway persists RFID events in SQLite with WAL and syncs them to the FastAPI API with `GATEWAY_API_KEY`. No physical RFID hardware connection is claimed.
- Disease-control integration remains an explicitly **SIMULATED** export because no actual national API contract was provided.

## Common errors

| Symptom | Check |
| --- | --- |
| `'py' is not recognized` | Install Python 3.11+ and Windows Python launcher; reopen PowerShell. |
| `'uvicorn' / 'alembic' is not recognized` | Use `.venv\Scripts\python.exe -m uvicorn` / `-m alembic`, not global commands. |
| `Connection refused` to Aiven | `DATABASE_URL`, hostname, port, TLS, Internet, Aiven service status / IP restrictions. |
| `alembic upgrade head` fails | Inspect migration traceback. Do not drop a shared `defaultdb`; use an isolated database. |
| `Address already in use` | Another process is on 8000/8001. `netstat -ano | findstr :8000` on Windows. |
| Gateway page says offline | Launch Terminal B; check `http://127.0.0.1:8001/healthz`; open website using `127.0.0.1`. |
| Browser on phone cannot connect | `127.0.0.1` refers to the phone itself. Bind the backend to a trusted LAN interface and use your PC's LAN IP; mobile HTTPS/secure-context limitations remain. |
| Empty data after login | Check `DEMO_MODE`, DB selection and whether the database already contains farm records. |

## Honest coverage statement

The frontend rewrite preserves the major workflows the prior React UI exposed, but it **does not fix all existing incomplete use cases**. The 31-case coverage table remains a *baseline assessment*, not a certificate of completion. Existing gaps include automatic missing-animal evaluation policy wiring, full reader lifecycle/heartbeat, advanced reports, real national disease API integration and native RFID reader support. Production-grade reliability, benchmarked <=2s response, mobile encryption, and hardware integration remain unverified.

**License / course note:** this is an educational implementation, not a production clinical data application.
