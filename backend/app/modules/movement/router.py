from fastapi import APIRouter,Depends,HTTPException,Header
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import User,Movement,Barn,Reader,Gate,GatewaySync,now
from app.core.schemas import ReadIn,SyncIn
from app.core.config import GATEWAY_API_KEY
from app.core.security import current_user,require_roles,ensure_barn_scope
from app.core.serializers import records,record
from app.modules.movement.service import process_read
import hmac
router=APIRouter(tags=["RFID movement and offline sync"])

@router.post("/movements/read")
def ingest_event(data:ReadIn,db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN","FARM_MANAGER","BARN_SUPERVISOR"))):
    reader=db.get(Reader,data.reader_id)
    if reader:
        gate=db.get(Gate,reader.gate_id)
        if gate:ensure_barn_scope(db,user,gate.barn_id,True)
    return process_read(db,data,user.id)

@router.get("/movements")
def movements(limit:int=100,barn_id:str|None=None,db:Session=Depends(get_db),user:User=Depends(current_user)):
    q=select(Movement).join(Barn,Movement.barn_id==Barn.id).order_by(Movement.occurred_at.desc())
    if barn_id:q=q.where(Movement.barn_id==barn_id)
    if user.role=="FARM_MANAGER" and user.farm_id:q=q.where(Barn.farm_id==user.farm_id)
    if user.role=="BARN_SUPERVISOR" and user.barn_id:q=q.where(Movement.barn_id==user.barn_id)
    return records(db.scalars(q.limit(min(max(limit,1),500))).all())

@router.post("/gateway/sync")
def sync(data:SyncIn,x_gateway_key:str|None=Header(None),db:Session=Depends(get_db)):
    if not x_gateway_key or not hmac.compare_digest(x_gateway_key,GATEWAY_API_KEY):raise HTTPException(401,"Invalid gateway key")
    results=[]
    for item in data.events:
        try:results.append(process_read(db,item,data.gateway_id))
        except Exception:
            db.rollback()
            raise
    status=db.get(GatewaySync,data.gateway_id)
    if status is None:status=GatewaySync(gateway_id=data.gateway_id);db.add(status)
    status.last_sync_at=now();status.accepted_count=(status.accepted_count or 0)+len([r for r in results if r["outcome"] in {"ACCEPTED","ACCEPTED_LATE"}]);db.commit()
    return {"gateway_id":data.gateway_id,"results":results,"server_time":now().isoformat()}

@router.get("/gateway/status")
def gateway_status(db:Session=Depends(get_db),user:User=Depends(current_user)):
    return records(db.scalars(select(GatewaySync).order_by(GatewaySync.last_sync_at.desc())).all())
