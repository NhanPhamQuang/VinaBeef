from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import Farm,Barn,Gate,Reader,User
from app.core.security import current_user,require_roles,ensure_barn_scope,audit
from app.core.schemas import FarmIn,BarnIn,GateIn,ReaderIn
from app.core.serializers import record,records
router=APIRouter(tags=["Facilities and readers"])

@router.get("/farms")
def farms(db:Session=Depends(get_db),user:User=Depends(current_user)):
    q=select(Farm).order_by(Farm.name)
    if user.role=="FARM_MANAGER" and user.farm_id:q=q.where(Farm.id==user.farm_id)
    if user.role=="BARN_SUPERVISOR" and user.barn_id:
        barn=db.get(Barn,user.barn_id);q=q.where(Farm.id==barn.farm_id if barn else "")
    return records(db.scalars(q).all())

@router.post("/farms",status_code=201)
def create_farm(data:FarmIn,db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN"))):
    if db.scalar(select(Farm).where(Farm.name==data.name)):raise HTTPException(409,"Farm name exists")
    item=Farm(**data.model_dump());db.add(item);db.flush();audit(db,user,"FARM_CREATE","farm",item.id);db.commit();return record(item)

@router.get("/barns")
def barns(farm_id:str|None=None,db:Session=Depends(get_db),user:User=Depends(current_user)):
    q=select(Barn).order_by(Barn.code)
    if farm_id:q=q.where(Barn.farm_id==farm_id)
    if user.role=="FARM_MANAGER" and user.farm_id:q=q.where(Barn.farm_id==user.farm_id)
    if user.role=="BARN_SUPERVISOR" and user.barn_id:q=q.where(Barn.id==user.barn_id)
    return records(db.scalars(q).all())

@router.post("/barns",status_code=201)
def create_barn(data:BarnIn,db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN","FARM_MANAGER"))):
    if not db.get(Farm,data.farm_id):raise HTTPException(404,"Farm not found")
    if user.role=="FARM_MANAGER" and user.farm_id!=data.farm_id:raise HTTPException(403,"Outside farm scope")
    if db.scalar(select(Barn).where(Barn.farm_id==data.farm_id,Barn.code==data.code)):raise HTTPException(409,"Barn code exists")
    item=Barn(**data.model_dump());db.add(item);db.flush();audit(db,user,"BARN_CREATE","barn",item.id);db.commit();return record(item)

@router.get("/gates")
def gates(barn_id:str|None=None,db:Session=Depends(get_db),user:User=Depends(current_user)):
    q=select(Gate).join(Barn,Gate.barn_id==Barn.id)
    if barn_id:q=q.where(Gate.barn_id==barn_id)
    if user.role=="FARM_MANAGER" and user.farm_id:q=q.where(Barn.farm_id==user.farm_id)
    if user.role=="BARN_SUPERVISOR" and user.barn_id:q=q.where(Gate.barn_id==user.barn_id)
    return records(db.scalars(q).all())

@router.post("/gates",status_code=201)
def create_gate(data:GateIn,db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN","FARM_MANAGER"))):
    ensure_barn_scope(db,user,data.barn_id,True)
    item=Gate(**data.model_dump());db.add(item);db.flush();audit(db,user,"GATE_CREATE","gate",item.id);db.commit();return record(item)

@router.get("/readers")
def readers(db:Session=Depends(get_db),user:User=Depends(current_user)):
    q=select(Reader).join(Gate,Reader.gate_id==Gate.id).join(Barn,Gate.barn_id==Barn.id).order_by(Reader.code)
    if user.role=="FARM_MANAGER" and user.farm_id:q=q.where(Barn.farm_id==user.farm_id)
    if user.role=="BARN_SUPERVISOR" and user.barn_id:q=q.where(Barn.id==user.barn_id)
    return records(db.scalars(q).all())

@router.post("/readers",status_code=201)
def create_reader(data:ReaderIn,db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN","FARM_MANAGER"))):
    gate=db.get(Gate,data.gate_id)
    if not gate:raise HTTPException(404,"Gate not found")
    ensure_barn_scope(db,user,gate.barn_id,True)
    if db.scalar(select(Reader).where(Reader.code==data.code)):raise HTTPException(409,"Reader code exists")
    item=Reader(**data.model_dump());db.add(item);db.flush();audit(db,user,"READER_CREATE","reader",item.id);db.commit();return record(item)
