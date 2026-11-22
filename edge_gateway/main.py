"""Offline-first farm gateway: durable SQLite queue and retryable central sync."""
import asyncio,os,sqlite3,uuid,json
from contextlib import asynccontextmanager
from datetime import datetime,timezone
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env",override=False)
import httpx
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from typing import Literal

DATA_FILE=os.getenv("EDGE_DB_PATH","./edge_events.sqlite")
CENTRAL=os.getenv("CENTRAL_API_URL","http://localhost:8000").rstrip("/")
GATEWAY_ID=os.getenv("GATEWAY_ID","farm-dak-lak-gateway")
GATEWAY_KEY=os.getenv("GATEWAY_API_KEY","vinabeef-local-gateway-demo-key")
SYNC_INTERVAL=int(os.getenv("SYNC_INTERVAL_SECONDS","10"))


def connection():
    Path(DATA_FILE).parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(DATA_FILE,timeout=20)
    db.row_factory=sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("CREATE TABLE IF NOT EXISTS events (event_id TEXT PRIMARY KEY, reader_id TEXT NOT NULL, tag_epc TEXT NOT NULL, direction TEXT NOT NULL, observed_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING', central_outcome TEXT, last_error TEXT, created_at TEXT NOT NULL)")
    return db

class EventIn(BaseModel):
    event_id:str|None=None
    reader_id:str=Field(min_length=3)
    tag_epc:str=Field(min_length=3)
    direction:Literal["IN","OUT"]
    observed_at:datetime|None=None

def utc_now():return datetime.now(timezone.utc).isoformat()

def accept(data:EventIn):
    event_id=data.event_id or str(uuid.uuid4())
    observed_at=(data.observed_at.isoformat() if data.observed_at else utc_now())
    with connection() as db:
        try:
            db.execute("INSERT INTO events(event_id,reader_id,tag_epc,direction,observed_at,status,created_at) VALUES (?,?,?,?,?,'PENDING',?)",(event_id,data.reader_id,data.tag_epc,data.direction,observed_at,utc_now()))
            db.commit()
            result="STORED_LOCALLY"
        except sqlite3.IntegrityError:
            result="ALREADY_STORED"
    return {"event_id":event_id,"outcome":result,"acknowledgment":"Durably stored at farm gateway; central processing is pending"}

def sync_once():
    with connection() as db:
        entries=db.execute("SELECT * FROM events WHERE status='PENDING' ORDER BY created_at LIMIT 100").fetchall()
        if not entries:return {"sent":0,"pending":0,"central_status":"NO_PENDING_EVENTS"}
        events=[{k:row[k] for k in ("event_id","reader_id","tag_epc","direction","observed_at")} for row in entries]
        try:
            with httpx.Client(timeout=10) as client:
                resp=client.post(f"{CENTRAL}/api/gateway/sync",headers={"X-Gateway-Key":GATEWAY_KEY},json={"gateway_id":GATEWAY_ID,"events":events})
                resp.raise_for_status();result=resp.json()
            outcomes={x["event_id"]:x for x in result["results"]}
            synced=0
            for e in entries:
                outcome=outcomes.get(e["event_id"])
                if not outcome:continue
                # REJECTED/UNKNOWN_TAG is a terminal central outcome with preserved evidence.
                db.execute("UPDATE events SET status='SYNCED',central_outcome=?,last_error=NULL WHERE event_id=?",(outcome["outcome"],e["event_id"]))
                synced+=1
            db.commit()
            return {"sent":synced,"pending":db.execute("SELECT COUNT(*) FROM events WHERE status='PENDING'").fetchone()[0],"central_status":"CONNECTED"}
        except (httpx.HTTPError,ValueError,KeyError) as exc:
            # Never remove unacknowledged local records.
            db.execute("UPDATE events SET last_error=? WHERE status='PENDING'",(str(exc)[:400],));db.commit()
            return {"sent":0,"pending":len(entries),"central_status":"OFFLINE_OR_ERROR","error":str(exc)[:200]}

async def sync_loop():
    while True:
        try:await asyncio.to_thread(sync_once)
        except Exception:pass
        await asyncio.sleep(max(SYNC_INTERVAL,2))

@asynccontextmanager
async def lifespan(app):
    with connection():pass
    task=asyncio.create_task(sync_loop())
    yield
    task.cancel()
    try:await task
    except asyncio.CancelledError:pass

app=FastAPI(title="VinaBeef Farm Edge Gateway",version="2.0.0",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:8000","http://127.0.0.1:8000"],allow_methods=["*"],allow_headers=["*"])

@app.get("/healthz")
def healthz():return {"status":"ok","gateway_id":GATEWAY_ID}

@app.post("/api/edge/events",status_code=202)
def submit_event(data:EventIn):return accept(data)

@app.get("/api/edge/status")
def status():
    with connection() as db:
        total=db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        pending=db.execute("SELECT COUNT(*) FROM events WHERE status='PENDING'").fetchone()[0]
        recent=db.execute("SELECT event_id,tag_epc,direction,status,central_outcome,last_error,created_at FROM events ORDER BY created_at DESC LIMIT 20").fetchall()
        return {"gateway_id":GATEWAY_ID,"stored":total,"pending":pending,"synced":total-pending,"central_api":CENTRAL,"recent":[dict(x) for x in recent]}

@app.post("/api/edge/sync-now")
def flush_queue():return sync_once()
