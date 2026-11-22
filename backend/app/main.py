from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import CORS_ORIGINS
from app.bootstrap import bootstrap
from app.modules.auth.router import router as auth
from app.modules.facilities.router import router as facilities
from app.modules.cattle.router import router as cattle
from app.modules.movement.router import router as movement
from app.modules.alerts.router import router as alerts
from app.modules.health.router import router as health
from app.modules.transfers.router import router as transfers
from app.modules.reports.router import router as reports
from app.modules.users.router import router as users
from app.modules.audit.router import router as audit

@asynccontextmanager
async def lifespan(app):
    bootstrap()
    yield

app=FastAPI(title="VinaBeef Livestock Management API",version="2.0.0",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=CORS_ORIGINS,allow_methods=["*"],allow_headers=["*"])

for router in [auth,facilities,cattle,movement,alerts,health,transfers,reports,users,audit]:
    app.include_router(router,prefix="/api")

@app.get("/healthz",tags=["Operations"])
def healthz():return {"status":"ok","service":"vinabeef-fastapi"}

# Native HTML/CSS/JS, served directly. No frontend build, npm or React runtime.
web_root = Path(__file__).resolve().parents[2] / "web"
app.mount("/static", StaticFiles(directory=web_root), name="static")

@app.get("/", include_in_schema=False)
@app.get("/field", include_in_schema=False)
def index():
    return FileResponse(web_root / "index.html")
