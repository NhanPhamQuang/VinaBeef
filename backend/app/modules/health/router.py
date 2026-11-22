from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import User,Cattle,Barn,HealthRecord,Tag
from app.core.schemas import HealthIn
from app.core.security import current_user,require_roles,ensure_barn_scope,audit
from app.core.serializers import record,records
router=APIRouter(prefix="/health",tags=["Health and vaccination"])

@router.get("")
def health(cattle_id:str|None=None,type:str|None=None,db:Session=Depends(get_db),user:User=Depends(current_user)):
    q=select(HealthRecord).join(Cattle,HealthRecord.cattle_id==Cattle.id).join(Barn,Cattle.barn_id==Barn.id).order_by(HealthRecord.event_at.desc())
    if cattle_id:q=q.where(HealthRecord.cattle_id==cattle_id)
    if type:q=q.where(HealthRecord.type==type)
    if user.role=="FARM_MANAGER" and user.farm_id:q=q.where(Barn.farm_id==user.farm_id)
    if user.role=="BARN_SUPERVISOR" and user.barn_id:q=q.where(Cattle.barn_id==user.barn_id)
    return records(db.scalars(q.limit(300)).all())

@router.get("/scan/{epc}")
def scan(epc:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    tag=db.scalar(select(Tag).where(Tag.epc==epc,Tag.active.is_(True)))
    if not tag:raise HTTPException(404,"Unknown RFID tag")
    animal=db.get(Cattle,tag.cattle_id)
    ensure_barn_scope(db,user,animal.barn_id)
    return record(animal)

@router.post("",status_code=201)
def create_health(data:HealthIn,db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN","FARM_MANAGER","BARN_SUPERVISOR"))):
    animal=db.get(Cattle,data.cattle_id)
    if not animal:raise HTTPException(404,"Cattle not found")
    ensure_barn_scope(db,user,animal.barn_id,True)
    if data.type=="VACCINATION" and not data.vaccine:raise HTTPException(422,"Vaccine name required")
    if data.source_id:
        existing=db.scalar(select(HealthRecord).where(HealthRecord.source_id==data.source_id))
        if existing:
            if existing.cattle_id!=data.cattle_id:raise HTTPException(409,"Idempotency key already used for a different animal")
            return record(existing)
    item=HealthRecord(**data.model_dump(exclude={"event_at"}),author_id=user.id,event_at=data.event_at if data.event_at else None) if data.event_at else HealthRecord(**data.model_dump(exclude={"event_at"}),author_id=user.id)
    db.add(item);db.flush()
    audit(db,user,"HEALTH_CREATE","health_record",item.id,{"type":data.type,"cattle_id":animal.id})
    db.commit();return record(item)
