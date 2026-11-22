from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import User,Barn,Farm
from app.core.schemas import UserIn,UserPatch
from app.core.security import current_user,require_roles,hash_password,audit
from app.core.serializers import record,records
router=APIRouter(prefix="/users",tags=["Users and RBAC"])
PUBLIC_FIELDS=["id","email","full_name","role","farm_id","barn_id","active"]

@router.get("")
def users(db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN","FARM_MANAGER"))):
    q=select(User).order_by(User.email)
    if user.role=="FARM_MANAGER":q=q.where(User.farm_id==user.farm_id)
    return records(db.scalars(q).all(),PUBLIC_FIELDS)

@router.post("",status_code=201)
def create_user(data:UserIn,db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN"))):
    if db.scalar(select(User).where(User.email==data.email.lower())):raise HTTPException(409,"Email exists")
    if data.farm_id and not db.get(Farm,data.farm_id):raise HTTPException(404,"Farm not found")
    if data.barn_id and not db.get(Barn,data.barn_id):raise HTTPException(404,"Barn not found")
    x=User(email=data.email.lower(),full_name=data.full_name,role=data.role,password_hash=hash_password(data.password),farm_id=data.farm_id,barn_id=data.barn_id)
    db.add(x);db.flush();audit(db,user,"USER_CREATE","user",x.id,{"role":x.role});db.commit();return record(x,PUBLIC_FIELDS)

@router.patch("/{user_id}")
def patch_user(user_id:str,data:UserPatch,db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN"))):
    x=db.get(User,user_id)
    if not x:raise HTTPException(404,"User not found")
    changes=data.model_dump(exclude_unset=True)
    if x.id==user.id and (changes.get("active") is False or ("role" in changes and changes["role"]!="SYSTEM_ADMIN")):raise HTTPException(409,"Cannot disable or demote current administrator")
    for key,value in changes.items():setattr(x,key,value)
    audit(db,user,"USER_UPDATE","user",x.id,{"fields":list(changes)});db.commit();return record(x,PUBLIC_FIELDS)
