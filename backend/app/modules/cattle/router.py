from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select,or_,func
from app.db.session import get_db
from app.db.models import User,Cattle,Tag,Barn,Presence,HealthRecord,Movement,Transfer
from app.core.schemas import CattleIn,CattlePatch,TagIn
from app.core.security import current_user,require_roles,ensure_barn_scope,audit
from app.core.serializers import record,records
router=APIRouter(prefix="/cattle",tags=["Cattle and RFID tags"])

def scoped(db,user,q):
    if user.role=="FARM_MANAGER" and user.farm_id:q=q.join(Barn,Cattle.barn_id==Barn.id).where(Barn.farm_id==user.farm_id)
    if user.role=="BARN_SUPERVISOR" and user.barn_id:q=q.where(Cattle.barn_id==user.barn_id)
    return q

@router.get("")
def list_cattle(q:str="",barn_id:str|None=None,skip:int=0,limit:int=100,db:Session=Depends(get_db),user:User=Depends(current_user)):
    statement=scoped(db,user,select(Cattle).order_by(Cattle.animal_code))
    if barn_id:statement=statement.where(Cattle.barn_id==barn_id)
    if q:
        pattern=f"%{q}%"
        statement=statement.outerjoin(Tag,Tag.cattle_id==Cattle.id).where(or_(Cattle.animal_code.ilike(pattern),Tag.epc.ilike(pattern))).distinct()
    items=db.scalars(statement.offset(max(skip,0)).limit(min(max(limit,1),500))).all()
    tags={t.cattle_id:t.epc for t in db.scalars(select(Tag).where(Tag.active.is_(True),Tag.cattle_id.in_([x.id for x in items]))).all()} if items else {}
    return [{**record(x),"epc":tags.get(x.id)} for x in items]

@router.get("/{cattle_id}")
def get_cattle(cattle_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    x=db.get(Cattle,cattle_id)
    if not x:raise HTTPException(404,"Cattle not found")
    ensure_barn_scope(db,user,x.barn_id)
    tags=records(db.scalars(select(Tag).where(Tag.cattle_id==x.id)).all())
    return {**record(x),"tags":tags,"presence":record(db.get(Presence,x.id))}

@router.post("",status_code=201)
def create_cattle(data:CattleIn,db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN","FARM_MANAGER","BARN_SUPERVISOR"))):
    ensure_barn_scope(db,user,data.barn_id,True)
    if db.scalar(select(Cattle).where(Cattle.animal_code==data.animal_code)):raise HTTPException(409,"Animal code already exists")
    if data.epc and db.scalar(select(Tag).where(Tag.epc==data.epc)):raise HTTPException(409,"RFID EPC already exists")
    x=Cattle(**data.model_dump(exclude={"epc"}));db.add(x);db.flush()
    if data.epc:db.add(Tag(cattle_id=x.id,epc=data.epc))
    db.add(Presence(cattle_id=x.id,barn_id=data.barn_id,state="INSIDE"))
    audit(db,user,"CATTLE_CREATE","cattle",x.id);db.commit();return record(x)

@router.patch("/{cattle_id}")
def update_cattle(cattle_id:str,data:CattlePatch,db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN","FARM_MANAGER","BARN_SUPERVISOR"))):
    x=db.get(Cattle,cattle_id)
    if not x:raise HTTPException(404,"Cattle not found")
    ensure_barn_scope(db,user,x.barn_id,True)
    changed=data.model_dump(exclude_unset=True)
    for key,value in changed.items():setattr(x,key,value)
    audit(db,user,"CATTLE_UPDATE","cattle",x.id,{"fields":list(changed)})
    db.commit();return record(x)

@router.post("/{cattle_id}/tags",status_code=201)
def add_tag(cattle_id:str,data:TagIn,db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN","FARM_MANAGER","BARN_SUPERVISOR"))):
    x=db.get(Cattle,cattle_id)
    if not x:raise HTTPException(404,"Cattle not found")
    ensure_barn_scope(db,user,x.barn_id,True)
    if db.scalar(select(Tag).where(Tag.epc==data.epc)):raise HTTPException(409,"RFID EPC already assigned")
    old=db.scalars(select(Tag).where(Tag.cattle_id==x.id,Tag.active.is_(True))).all()
    for t in old:t.active=False
    t=Tag(cattle_id=x.id,epc=data.epc);db.add(t);db.flush();audit(db,user,"TAG_ASSIGN","cattle",x.id,{"tag_id":t.id,"superseded_tags":len(old)});db.commit();return record(t)

@router.get("/{cattle_id}/history")
def history(cattle_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    x=db.get(Cattle,cattle_id)
    if not x:raise HTTPException(404,"Cattle not found")
    ensure_barn_scope(db,user,x.barn_id)
    return {"health":records(db.scalars(select(HealthRecord).where(HealthRecord.cattle_id==x.id).order_by(HealthRecord.event_at.desc())).all()),"movements":records(db.scalars(select(Movement).where(Movement.cattle_id==x.id).order_by(Movement.occurred_at.desc())).all()),"transfers":records(db.scalars(select(Transfer).where(Transfer.cattle_id==x.id).order_by(Transfer.created_at.desc())).all())}
