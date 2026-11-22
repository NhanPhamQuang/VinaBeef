from datetime import datetime,timedelta,timezone
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select,func
from app.db.session import get_db
from app.db.models import User,Barn,Alert,Cattle,Presence,MissingPolicy,Farm,GatewaySync,now
from app.core.security import current_user,require_roles,ensure_barn_scope,audit
from app.core.serializers import record,records
router=APIRouter(prefix="/alerts",tags=["Alerts and abnormality detection"])

@router.get("")
def alerts(status:str|None=None,db:Session=Depends(get_db),user:User=Depends(current_user)):
    q=select(Alert).outerjoin(Barn,Alert.barn_id==Barn.id).order_by(Alert.created_at.desc())
    if status:q=q.where(Alert.status==status)
    if user.role=="FARM_MANAGER" and user.farm_id:q=q.where(Barn.farm_id==user.farm_id)
    if user.role=="BARN_SUPERVISOR" and user.barn_id:q=q.where(Alert.barn_id==user.barn_id)
    return records(db.scalars(q.limit(300)).all())

@router.patch("/{alert_id}/{action}")
def update_alert(alert_id:str,action:str,db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN","FARM_MANAGER","BARN_SUPERVISOR"))):
    if action not in {"acknowledge","resolve"}:raise HTTPException(400,"Use acknowledge or resolve")
    x=db.get(Alert,alert_id)
    if not x:raise HTTPException(404,"Alert not found")
    if x.barn_id:ensure_barn_scope(db,user,x.barn_id,True)
    x.status="ACKNOWLEDGED" if action=="acknowledge" else "RESOLVED"
    if action=="resolve":x.resolved_at=now()
    audit(db,user,"ALERT_"+action.upper(),"alert",x.id);db.commit();return record(x)

@router.get("/policies")
def list_policies(db:Session=Depends(get_db),user:User=Depends(current_user)):
    q=select(MissingPolicy)
    if user.role=="FARM_MANAGER" and user.farm_id:q=q.where(MissingPolicy.farm_id==user.farm_id)
    if user.role=="BARN_SUPERVISOR":
        barn=db.get(Barn,user.barn_id) if user.barn_id else None
        if not barn:return []
        q=q.where(MissingPolicy.farm_id==barn.farm_id)
    return records(db.scalars(q).all())

@router.put("/policies/{farm_id}")
def configure_policy(farm_id:str,grace_minutes:int=60,enabled:bool=True,db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN","FARM_MANAGER"))):
    if not db.get(Farm,farm_id):raise HTTPException(404,"Farm not found")
    if user.role=="FARM_MANAGER" and user.farm_id!=farm_id:raise HTTPException(403,"Outside assigned farm")
    if grace_minutes<1 or grace_minutes>1440:raise HTTPException(400,"Grace must be between 1 and 1440 minutes")
    item=db.get(MissingPolicy,farm_id)
    if not item:item=MissingPolicy(farm_id=farm_id);db.add(item)
    item.grace_minutes=grace_minutes;item.enabled=enabled;item.updated_at=now()
    audit(db,user,"MISSING_POLICY_CONFIG","farm",farm_id,{"grace_minutes":grace_minutes,"enabled":enabled})
    db.commit();return record(item)

@router.post("/evaluate-missing")
def evaluate_missing(grace_minutes:int=60,db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN","FARM_MANAGER","BARN_SUPERVISOR"))):
    if grace_minutes<1 or grace_minutes>1440:raise HTTPException(400,"grace_minutes must be 1..1440")
    threshold=now()-timedelta(minutes=grace_minutes)
    q=select(Presence,Cattle).join(Cattle,Presence.cattle_id==Cattle.id).where(Presence.state=="OUTSIDE",Presence.last_event_at< threshold)
    if user.role=="BARN_SUPERVISOR" and user.barn_id:q=q.where(Cattle.barn_id==user.barn_id)
    if user.role=="FARM_MANAGER" and user.farm_id:q=q.join(Barn,Cattle.barn_id==Barn.id).where(Barn.farm_id==user.farm_id)
    added=[]
    for state,animal in db.execute(q):
        exists=db.scalar(select(Alert).where(Alert.cattle_id==animal.id,Alert.type=="MISSING",Alert.status!="RESOLVED"))
        if exists:continue
        alert=Alert(cattle_id=animal.id,barn_id=animal.barn_id,type="MISSING",message=f"{animal.animal_code} has not returned within {grace_minutes} minutes (proposed demo policy)")
        db.add(alert);db.flush();added.append(record(alert))
    audit(db,user,"MISSING_EVALUATION","policy","grace-minutes",{"minutes":grace_minutes,"raised":len(added)})
    db.commit();return {"new_alerts":added,"policy":"Demonstration grace window, not confirmed farm policy"}
