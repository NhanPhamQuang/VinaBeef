from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import Transfer,Cattle,User,Barn,Presence,now
from app.core.schemas import TransferIn
from app.core.security import current_user,require_roles,ensure_barn_scope,audit
from app.core.serializers import record,records
router=APIRouter(prefix="/transfers",tags=["Cattle transfers"])

@router.get("")
def transfers(db:Session=Depends(get_db),user:User=Depends(current_user)):
    q=select(Transfer).join(Cattle,Transfer.cattle_id==Cattle.id).join(Barn,Cattle.barn_id==Barn.id).order_by(Transfer.created_at.desc())
    if user.role=="FARM_MANAGER" and user.farm_id:q=q.where(Barn.farm_id==user.farm_id)
    if user.role=="BARN_SUPERVISOR" and user.barn_id:q=q.where(Cattle.barn_id==user.barn_id)
    return records(db.scalars(q.limit(200)).all())

@router.post("",status_code=201)
def create_transfer(data:TransferIn,db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN","FARM_MANAGER","BARN_SUPERVISOR"))):
    animal=db.get(Cattle,data.cattle_id)
    if not animal or not db.get(Barn,data.target_barn_id):raise HTTPException(404,"Animal or target barn not found")
    ensure_barn_scope(db,user,animal.barn_id,True)
    if animal.barn_id==data.target_barn_id:raise HTTPException(400,"Same source/destination")
    x=Transfer(cattle_id=animal.id,source_barn_id=animal.barn_id,target_barn_id=data.target_barn_id,reason=data.reason,requested_by=user.id)
    db.add(x);db.flush();audit(db,user,"TRANSFER_REQUEST","transfer",x.id);db.commit();return record(x)

@router.patch("/{transfer_id}/{action}")
def transition_transfer(transfer_id:str,action:str,db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN","FARM_MANAGER"))):
    x=db.get(Transfer,transfer_id)
    if not x:raise HTTPException(404,"Transfer not found")
    if action not in {"approve","complete","cancel"}:raise HTTPException(400,"Unknown action")
    ensure_barn_scope(db,user,x.source_barn_id,True)
    animal=db.get(Cattle,x.cattle_id)
    if action=="approve" and x.status=="PENDING":x.status="APPROVED";x.approved_by=user.id
    elif action=="complete" and x.status=="APPROVED":
        if animal.barn_id!=x.source_barn_id:raise HTTPException(409,"Animal assignment changed")
        animal.barn_id=x.target_barn_id;x.status="COMPLETED";x.completed_at=now()
        state=db.get(Presence,animal.id)
        if state:state.state="UNKNOWN" # transfer does not fabricate a gate movement
    elif action=="cancel" and x.status in {"PENDING","APPROVED"}:x.status="CANCELLED"
    else:raise HTTPException(409,"Invalid transfer state transition")
    audit(db,user,"TRANSFER_"+action.upper(),"transfer",x.id);db.commit();return record(x)
